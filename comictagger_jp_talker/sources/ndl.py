"""NDL Search SRU 1.2 / DC-NDL RDF v3; also parse v2 digitization dates."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urldefrag, urlsplit

import requests
from comictalker.comiccacher import ComicCacher
from comictalker.comiccacher import Series as CachedSeries
from comictalker.comictalker import RLCallBack, TalkerDataError, TalkerNetworkError
from comictalker.vendor.pyrate_limiter import Limiter, RequestRate

from comictagger_jp_talker import __version__
from comictagger_jp_talker.isbn import isbn13, normalize_isbn
from comictagger_jp_talker.models import BookRecord, ContentDates, SearchPage, SearchQuery
from comictagger_jp_talker.sources.ndl_summary import DETAIL_ENDPOINT, parse_summary

ENDPOINT = "https://ndlsearch.ndl.go.jp/api/sru"
RECORD_SCHEMA = "dcndl_v3"
SEARCH_CACHE = "jpbooks.ndl.search.dcndl_v3"
RECORD_CACHE = "jpbooks.ndl.record.dcndl_v3"
NS = {
    "sru": "http://www.loc.gov/zing/srw/",
    "diag": "http://www.loc.gov/zing/srw/diagnostic/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcndl": "http://ndl.go.jp/dcndl/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
}
RDF_ABOUT = "{" + NS["rdf"] + "}about"
RDF_RESOURCE = "{" + NS["rdf"] + "}resource"
RDF_DATATYPE = "{" + NS["rdf"] + "}datatype"
RDFS_LABEL = "{" + NS["rdfs"] + "}label"
_LOCK = threading.RLock()
_LIMITER = Limiter(RequestRate(1, 2))  # Local policy, not an NDL-published quota.
logger = logging.getLogger(__name__)


def cql_quote(value: str) -> str:
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise TalkerDataError("NDL Search", 2, "検索値に制御文字または孤立サロゲートがあります。")
    # CQL string delimiters and masking operators. URL encoding belongs to requests.
    return '"' + re.sub(r'([\\"*?^])', r"\\\1", value) + '"'


def build_cql(query: SearchQuery) -> str:
    fields: list[tuple[str, str]] = []
    if query.itemno:
        fields.append(("itemno", query.itemno))
    elif query.isbn:
        isbn = normalize_isbn(query.isbn)
        if not isbn:
            raise TalkerDataError("NDL Search", 2, "不正な ISBN です。")
        fields.append(("isbn", isbn))
    else:
        fields.extend(
            (key, val)
            for key, val in (
                ("title", query.title),
                ("title", query.issue),
                ("creator", query.creator),
                ("publisher", query.publisher),
            )
            if val
        )
    if not fields:
        raise TalkerDataError("NDL Search", 3, "ISBN または検索語を指定してください。")
    fields.extend(
        (key, val)
        for key, val in (
            ("mediatype", query.mediatype),
            ("from", query.from_date),
            ("until", query.until_date),
        )
        if val
    )
    cql = " AND ".join(f"{key} = {cql_quote(val)}" for key, val in fields)
    if query.title and not query.isbn and not query.itemno:
        # NDL accepts sortBy as an AND-connected field (verified live). Standard
        # CQL's trailing 'sortBy issued_date/...' is misparsed as part of mediatype.
        orders = {
            "title": "",  # NDL's existing default order.
            "oldest": "issued_date/sort.ascending",
            "newest": "issued_date/sort.descending",
        }
        if query.sort_order not in orders:
            raise TalkerDataError("NDL Search", 2, "不正な検索順です。")
        if order := orders[query.sort_order]:
            cql += f" AND sortBy={order}"  # Fixed allowlist; never interpolate user-supplied CQL.
    return cql


def _value(node: ET.Element) -> str:
    for path in ("rdf:Description/rdf:value", "foaf:Agent/foaf:name"):
        value = node.findtext(path, namespaces=NS)
        if value:
            return value.strip()
    return (node.text or "").strip()


def _values(node: ET.Element, path: str) -> list[str]:
    return list(dict.fromkeys(v for el in node.findall(path, NS) if (v := _value(el))))


def ndl_record_url(value: str) -> tuple[str, str] | None:
    """Use only the returned NDL books URL; never manufacture an ID from an ISBN."""
    url, _ = urldefrag(value)
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "ndlsearch.ndl.go.jp" or parts.query:
        return None
    match = re.fullmatch(r"/books/([A-Za-z0-9_-]+)", parts.path)
    return (match[1], url) if match else None


def parse_record(rdf: ET.Element) -> BookRecord:
    if rdf.tag != "{" + NS["rdf"] + "}RDF":
        raise TalkerDataError("NDL Search", 1, "Unsupported metadata: DC-NDL RDF がありません。")
    # BibResource may repeat for holdings links. Only the node with a title is the book.
    books = [n for n in rdf.findall("dcndl:BibResource", NS) if _values(n, "dcterms:title")]
    if len(books) != 1:
        raise TalkerDataError("NDL Search", 2, "Malformed record: 書誌タイトルが欠落または曖昧です。")
    bib = books[0]
    identity = ndl_record_url(bib.get(RDF_ABOUT, ""))
    if not identity:
        raise TalkerDataError("NDL Search", 1, "Unsupported metadata: NDL 書誌 URL がありません。")
    record_id, url = identity
    record = BookRecord(id=record_id, title=_values(bib, "dcterms:title")[0], url=url)
    for attribute, path in (
        ("series_titles", "dcndl:seriesTitle"),
        ("volumes", "dcndl:volume"),
        ("creators", "dcterms:creator"),
        ("responsibilities", "dc:creator"),
        ("contributors", "dcterms:contributor"),
        ("publishers", "dcterms:publisher"),
        ("issued", "dcterms:issued"),
        ("dates", "dcterms:date"),
        ("digitized_dates", "dcndl:dateDigitized"),
        ("available_dates", "dcterms:available"),
        ("formats", "dcterms:format"),
        ("languages", "dcterms:language"),
        ("editions", "dcndl:edition"),
    ):
        setattr(record, attribute, _values(bib, path))
    for language in bib.findall("dcterms:language", NS):
        if language.get(RDF_RESOURCE):
            record.languages.append(language.attrib[RDF_RESOURCE])
    for creator in bib.findall("dcterms:creator", NS):
        name = creator.findtext("foaf:Agent/foaf:name", namespaces=NS)
        if name:
            record.creator_roles.extend(
                (name.strip(), role) for role in _values(creator, "foaf:Agent/dcndl:role")
            )
    record.isbns = [
        _value(n)
        for n in bib.findall("dcterms:identifier", NS)
        if n.get(RDF_DATATYPE) == NS["dcndl"] + "ISBN" and _value(n)
    ]
    record.abstracts = _values(bib, "dcterms:abstract")
    record.descriptions = _values(bib, "dcterms:description")
    for node in bib.findall("dcterms:subject", NS) + bib.findall("dc:subject", NS):
        value = _value(node)
        resource = node.get(RDF_RESOURCE, "")
        datatype = node.get(RDF_DATATYPE, "")
        if re.match(r"https?://id\.ndl\.go\.jp/class/ndc[0-9]*/", resource):
            record.ndc.append(resource)
        elif datatype.startswith(NS["dcndl"] + "NDC"):
            record.ndc.append(datatype + ": " + value)
        elif re.match(r"https?://id\.ndl\.go\.jp/class/", resource) or datatype:
            record.classifications.append(resource or datatype + ": " + value)
        elif value or resource:
            record.subjects.append(value or resource)
    for node in bib.findall("dcndl:materialType", NS):
        # Preserve label AND URI; don't infer electronic/paper from publication date.
        record.material_types.append(" ".join(v for v in (node.get(RDFS_LABEL), node.get(RDF_RESOURCE)) if v))
    # v2 can repeat BibResource for links; v3 puts them on the titled node.
    linked_items = {
        link.get(RDF_RESOURCE)
        for node in rdf.findall("dcndl:BibResource", NS)
        if node.get(RDF_ABOUT) == bib.get(RDF_ABOUT)
        for link in node.findall("dcndl:record", NS)
    }
    for item in rdf.findall("dcndl:Item", NS):
        uri = item.get(RDF_ABOUT, "")
        if not uri or uri not in linked_items:
            continue  # Unrelated nodes stay in raw_xml, never supply dates for this book.
        record.content_dates.append(
            ContentDates(
                uri=uri,
                issued=_values(item, "dcterms:issued"),
                dates=_values(item, "dcterms:date"),
                digitized=_values(item, "dcndl:dateDigitized"),
                available=_values(item, "dcterms:available"),
                material_types=[
                    " ".join(v for v in (n.get(RDFS_LABEL), n.get(RDF_RESOURCE)) if v)
                    for n in item.findall("dcndl:materialType", NS)
                ],
                formats=_values(item, "dcterms:format"),
                descriptions=_values(item, "dcterms:description"),
            )
        )
    for admin in rdf.findall("dcndl:BibAdminResource", NS):
        if ndl_record_url(admin.get(RDF_ABOUT, "")) == identity:
            record.providers.extend(_values(admin, "dcndl:bibRecordCategory"))
    for node in bib.findall("dcterms:rights", NS):
        record.rights.append(_value(node) or node.get(RDF_RESOURCE, ""))
    record.raw_xml = ET.tostring(rdf, encoding="unicode")
    return record


def parse_sru(content: bytes) -> SearchPage:
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError) as exc:
        raise TalkerDataError("NDL Search", 2, f"Invalid XML: {exc}") from exc
    if root.tag != "{" + NS["sru"] + "}searchRetrieveResponse":
        raise TalkerDataError("NDL Search", 1, "Unsupported metadata: SRU 応答ではありません。")
    diagnostics = root.findall(".//diag:diagnostic", NS)
    if diagnostics:
        messages = [
            " | ".join(_values(d, "diag:uri") + _values(d, "diag:message") + _values(d, "diag:details"))
            for d in diagnostics
        ]
        # NDL uses a general-error URI for no matches (observed with both ISBN
        # forms). Match the message as well: URI 1/1 alone also covers real errors.
        # Never hide conflicting counts, records, or additional diagnostics.
        if (
            all(
                d.findtext("diag:uri", namespaces=NS) == "info:srw/diagnostic/1/1"
                and d.findtext("diag:message", namespaces=NS)
                in ("Record does not exist", "Record does not exit")
                for d in diagnostics
            )
            and root.findtext("sru:numberOfRecords", namespaces=NS) in (None, "0")
            and not root.findall("sru:records/sru:record", NS)
        ):
            logger.info("NDL Search: no records; SRU diagnostics: %s", "; ".join(messages))
            return SearchPage([], 0)
        raise TalkerDataError("NDL Search", 1, "SRU diagnostics: " + "; ".join(messages))
    try:
        total = int(root.findtext("sru:numberOfRecords", namespaces=NS) or "")
        if total < 0:
            raise ValueError("negative count")
    except ValueError as exc:
        raise TalkerDataError("NDL Search", 2, "Malformed response: numberOfRecords が不正です。") from exc
    if total == 0:
        return SearchPage([], 0)
    records: list[BookRecord] = []
    warnings: list[str] = []
    errors: list[TalkerDataError] = []
    for node in root.findall("sru:records/sru:record", NS):
        try:
            data = node.find("sru:recordData", NS)
            if data is None:
                raise TalkerDataError("NDL Search", 2, "Malformed record: recordData がありません。")
            rdf = data.find("rdf:RDF", NS)
            if rdf is None:
                raise TalkerDataError("NDL Search", 1, "Unsupported metadata: DC-NDL RDF がありません。")
            # Real NDL responses label recordSchema as dc-v1.1 even for DC-NDL RDF.
            # Validate the payload namespace instead of trusting that label.
            records.append(parse_record(rdf))
        except TalkerDataError as exc:
            warnings.append(str(exc))
            errors.append(exc)
    if not records:
        if errors:
            raise errors[0]
        raise TalkerDataError("NDL Search", 3, "Malformed response: 件数に対応する書誌がありません。")
    return SearchPage(records, total, warnings, total > len(records) + len(errors))


def rank_records(records: list[BookRecord], isbn: str = "") -> list[BookRecord]:
    """No ISBN-based merging: retain editions and providers as selectable candidates.

    Exact ISBN first, NDL catalog records next, then useful-field completeness,
    and returned record ID as a deterministic tie breaker. Drop only duplicate IDs.
    """
    wanted = isbn13(isbn)

    def key(record: BookRecord) -> tuple:
        exact = bool(wanted and wanted in {isbn13(v) for v in record.isbns})
        national = "R100000002" in record.providers
        complete = sum(
            bool(v)
            for v in (
                record.creators or record.responsibilities,
                record.publishers,
                record.isbns,
                record.issued or record.dates,
                record.languages,
                record.abstracts,
                record.volumes,
            )
        )
        return -int(exact), -int(national), -complete, record.id

    result: dict[str, BookRecord] = {}
    for record in sorted(records, key=key):
        result.setdefault(record.id, record)
    return list(result.values())


class NDLSource:
    def __init__(self, cache_folder: Path, *, maximum_records: int = 20) -> None:
        self.maximum_records = maximum_records
        self._refresh_summaries: set[str] = set()
        self.cache_folder = cache_folder / "jpbooks-ndl-v1"
        self.cache_folder.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"comictagger-jp-talker/{__version__} (NDL Search SRU)"
        with _LOCK:
            self.cache = ComicCacher(self.cache_folder, "jpbooks-ndl-v1")

    def _request(self, query: str, on_rate_limit: RLCallBack | None) -> bytes:
        params = {
            "operation": "searchRetrieve",
            "version": "1.2",
            "recordSchema": RECORD_SCHEMA,
            "recordPacking": "xml",
            "maximumRecords": self.maximum_records,
            "startRecord": 1,
            "query": query,
        }
        return self._get(ENDPOINT, params, on_rate_limit)

    def _get(self, endpoint: str, params: dict, on_rate_limit: RLCallBack | None) -> bytes:
        try:
            with _LIMITER.ratelimit("ndlsearch", delay=True, on_rate_limit=on_rate_limit):
                response = self.session.get(endpoint, params=params, timeout=(5, 30))
            response.raise_for_status()
            return response.content  # XML bytes determine encoding; never requests' guessed .text.
        except requests.Timeout as exc:
            raise TalkerNetworkError("NDL Search", 4) from exc
        except requests.ConnectionError as exc:
            raise TalkerNetworkError(
                "NDL Search", 1, "Connection error: NDL Search に接続できません。"
            ) from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            raise TalkerNetworkError(
                "NDL Search", 3 if status == 429 else 0, f"HTTP error: {status}"
            ) from exc
        except requests.RequestException as exc:
            raise TalkerNetworkError("NDL Search", 0, f"Request error: {type(exc).__name__}") from exc

    def _with_summary(self, record: BookRecord, on_rate_limit: RLCallBack | None) -> BookRecord:
        if record.abstracts:
            return record
        # Only enrich the selected record. Shared limiter and ComicCacher also
        # cover this API, with the normal seven-day search-cache lifetime.
        cache_source = "jpbooks.ndl.summary.v1"
        cached = (
            []
            if record.id in self._refresh_summaries
            else self.cache.get_search_results(cache_source, record.id)
        )
        content = (
            cached[0].data.data
            if cached
            else self._get(DETAIL_ENDPOINT, {"cs": "bib", "f-token": record.id}, on_rate_limit)
        )
        try:
            data = json.loads(content)
        except (ValueError, UnicodeDecodeError) as exc:
            raise TalkerDataError("NDL Search", 2, "Invalid JSON: 要約の応答を解析できません。") from exc
        summary = parse_summary(data, record.id)
        if not cached:
            # Cache valid 'no summary' responses too; never cache malformed data.
            self.cache.add_search_results(cache_source, record.id, [CachedSeries(record.id, content)], True)
        if summary:
            record.abstracts = summary.texts
            record.summary_provider = summary.provider
            record.summary_medium = summary.medium
            record.summary_item_id = summary.item_id
        self._refresh_summaries.discard(record.id)
        return record

    def search(
        self, query: SearchQuery, *, refresh: bool = False, on_rate_limit: RLCallBack | None = None
    ) -> SearchPage:
        cql = build_cql(query)
        cache_key = hashlib.sha256(f"{self.maximum_records}:{cql}".encode()).hexdigest()
        with _LOCK:  # Serialize requests across Talker instances and protect SQLite connection handover.
            cached = [] if refresh else self.cache.get_search_results(SEARCH_CACHE, cache_key)
            if cached:
                try:
                    page = parse_sru(cached[0].data.data)
                except TalkerDataError:
                    logger.warning("Invalid cached NDL search response; refreshing %s", cache_key)
                    cached = []
            if not cached:
                content = self._request(cql, on_rate_limit)
                page = parse_sru(content)
                # Store even zero-result pages; ComicCacher otherwise has no negative-cache marker.
                self.cache.add_search_results(
                    SEARCH_CACHE, cache_key, [CachedSeries(cache_key, content)], True
                )
                for record in page.records:
                    self.cache.add_series_info(
                        RECORD_CACHE, CachedSeries(record.id, record.raw_xml.encode("utf-8")), True
                    )
            page.records = rank_records(page.records, query.isbn)
            if refresh:
                self._refresh_summaries = {record.id for record in page.records}
            return page

    def get(self, record_id: str, *, on_rate_limit: RLCallBack | None = None) -> BookRecord:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", record_id):
            raise TalkerDataError("NDL Search", 2, "不正な NDL 書誌 ID です。")
        with _LOCK:
            cached = self.cache.get_series_info(record_id, RECORD_CACHE)
            if cached:
                try:
                    record = parse_record(ET.fromstring(cached.data.data))
                except (ET.ParseError, TalkerDataError):
                    logger.warning("Invalid cached NDL record; refreshing %s", record_id)
                else:
                    return self._with_summary(record, on_rate_limit)
            page = self.search(
                SearchQuery(itemno=record_id, mediatype=""), refresh=True, on_rate_limit=on_rate_limit
            )
            matches = [record for record in page.records if record.id == record_id]
            if len(matches) != 1:
                raise TalkerDataError("NDL Search", 3, "指定した NDL 書誌が見つかりません。")
            return self._with_summary(matches[0], on_rate_limit)

    def check_status(self, *, on_rate_limit: RLCallBack | None = None) -> None:
        with _LOCK:
            parse_sru(self._request(build_cql(SearchQuery(isbn="488594287X", mediatype="")), on_rate_limit))
