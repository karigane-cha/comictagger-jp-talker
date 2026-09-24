"""Explicit-use, read-only MADB source. The Talker never instantiates this source."""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path

import requests
from comictalker.comiccacher import ComicCacher
from comictalker.comiccacher import Series as CachedSeries
from comictalker.vendor.pyrate_limiter import Limiter, RequestRate
from urllib3.exceptions import ReadTimeoutError

from comictagger_jp_talker import __version__
from comictagger_jp_talker.sources.madb_models import MADBError, MADBRecordBundle, MADBSearchPage
from comictagger_jp_talker.sources.madb_parser import (
    MAX_RESPONSE_BYTES,
    parse_resource,
    parse_search,
    terms,
)
from comictagger_jp_talker.sources.madb_queries import (
    DCTERMS_NS,
    DEFAULT_CANDIDATES,
    DEFAULT_TRIPLES,
    ENDPOINT,
    MAX_CANDIDATES,
    MAX_TRIPLES,
    SCHEMA_NS,
    ResourceKind,
    bounded_limit,
    isbn_query,
    resource_query,
    resource_uri,
)

logger = logging.getLogger(__name__)
QUERY_CACHE = "madb:query:v1"
RESOURCE_CACHE = "madb:resource:v1"
RELATION_CACHE = "madb:relation:v1"
_LOCK = threading.RLock()
_LIMITER = Limiter(RequestRate(1, 3))  # Local conservative policy, not an official MADB quota.
MAX_RELATIONS = 12
TIMEOUT = (5, 30)


class MADBSource:
    def __init__(
        self,
        cache_folder: Path,
        *,
        maximum_candidates: int = DEFAULT_CANDIDATES,
        maximum_triples: int = DEFAULT_TRIPLES,
    ) -> None:
        self.maximum_candidates = bounded_limit(maximum_candidates, MAX_CANDIDATES)
        self.maximum_triples = bounded_limit(maximum_triples, MAX_TRIPLES)
        self.cache_folder = cache_folder / "jpbooks-madb-v1"
        self.cache_folder.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            self.cache = ComicCacher(self.cache_folder, "jpbooks-madb-v1")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"comictagger-jp-talker/{__version__} (MADB read-only source)",
                "Accept": "application/sparql-results+json",
            }
        )
        self._closed = False

    def close(self) -> None:
        with _LOCK:
            if not self._closed:
                try:
                    self.session.close()
                finally:
                    self.cache.close()
                    self._closed = True

    def __enter__(self) -> MADBSource:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _request(self, query: str) -> bytes:
        # No automatic retry: avoid amplifying slow queries; expose Retry-After to callers.
        try:
            with _LIMITER.ratelimit("madb", delay=True):
                with self.session.post(
                    ENDPOINT,
                    data={"query": query},
                    timeout=TIMEOUT,
                    stream=True,
                    allow_redirects=False,
                ) as response:
                    status = response.status_code
                    if status != 200:
                        kind = "rate_limited" if status == 429 else "query" if status == 400 else "http"
                        raise MADBError(
                            kind,
                            f"MADB HTTP {status}",
                            status=status,
                            retry_after=response.headers.get("Retry-After"),
                        )
                    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                    if media_type not in ("application/sparql-results+json", "application/json"):
                        raise MADBError("protocol", "Expected SPARQL JSON Content-Type")
                    chunks, size = [], 0
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise MADBError("truncated", "MADB response exceeds byte cap")
                        chunks.append(chunk)
                    return b"".join(chunks)
        except requests.Timeout as exc:
            raise MADBError("timeout", "MADB request timed out") from exc
        except requests.ConnectionError as exc:
            # requests wraps its existing urllib3 transport's streaming read timeout.
            if exc.args and isinstance(exc.args[0], ReadTimeoutError):
                raise MADBError("timeout", "MADB response read timed out") from exc
            raise MADBError("network", "MADB connection failed") from exc
        except requests.RequestException as exc:
            raise MADBError("network", f"MADB transport failure ({type(exc).__name__})") from exc

    def _load(self, namespace: str, query: str, parser, *, refresh: bool, context: str = ""):
        # Endpoint + template text/limits + parser version namespace + relation scope.
        key = hashlib.sha256(f"{ENDPOINT}\n{namespace}\n{context}\n{query}".encode()).hexdigest()
        with _LOCK:  # One request at a time across source instances, including body streaming.
            if self._closed:
                raise RuntimeError("MADBSource is closed")
            cached = [] if refresh else self.cache.get_search_results(namespace, key)
            if cached:
                try:
                    result = parser(cached[0].data.data)
                    if not cached[0].complete or not self._complete(result):
                        raise MADBError("truncated", "Incomplete cached response")
                    return result
                except MADBError:
                    logger.warning("Invalid cached MADB response; refreshing %s:%s", namespace, key)
            content = self._request(query)
            result = parser(content)
            if self._complete(result):
                # Host search-cache expiration (currently seven days) for all scopes.
                # An envelope row also represents a valid zero-result search.
                self.cache.add_search_results(namespace, key, [CachedSeries(key, content)], True)
            return result

    @staticmethod
    def _complete(result) -> bool:
        if isinstance(result, MADBSearchPage):
            return not result.truncated
        return result.completeness == "complete"

    def search_by_isbn(self, isbn: str, *, refresh: bool = False) -> MADBSearchPage:
        query = isbn_query(isbn, self.maximum_candidates)
        return self._load(
            QUERY_CACHE,
            query,
            lambda data: parse_search(data, isbn, self.maximum_candidates),
            refresh=refresh,
        )

    def _resource(self, uri: str, kind: ResourceKind, *, refresh: bool, parent: str = "", relation: str = ""):
        query = resource_query(uri, kind, self.maximum_triples)
        return self._load(
            RELATION_CACHE if parent else RESOURCE_CACHE,
            query,
            lambda data: parse_resource(data, uri, kind, self.maximum_triples, book_uri=parent),
            refresh=refresh,
            context=f"{parent}|{relation}|{kind}",
        )

    def get(self, book_id: str, *, refresh: bool = False) -> MADBRecordBundle:
        uri = resource_uri(book_id, "book")
        book = self._resource(uri, "book", refresh=refresh)
        series, agents, holdings, warnings = [], [], [], []
        if book.completeness != "complete":
            warnings.append("Book direct triple limit reached")
        seen: set[tuple[str, str]] = set()
        attempted = 0

        def related(record, predicate: str, kind: ResourceKind, target: list) -> None:
            nonlocal attempted
            for term in terms(record.statements, predicate):
                try:
                    if term.kind != "uri":
                        raise ValueError
                    target_uri = resource_uri(term.value, kind)
                except ValueError:
                    # Retain raw evidence, including bnodes; never interpolate it in a query.
                    warnings.append(f"Unresolved {kind} reference on {record.uri}")
                    continue
                if (kind, target_uri) in seen:
                    continue
                seen.add((kind, target_uri))
                if attempted >= MAX_RELATIONS:
                    warnings.append("Related resource budget reached")
                    continue
                attempted += 1
                try:
                    result = self._resource(
                        target_uri, kind, refresh=refresh, parent=record.uri, relation=predicate
                    )
                except MADBError as exc:
                    warnings.append(f"{kind} {target_uri}: {exc.kind} ({exc.desc})")
                else:
                    target.append(result)
                    if result.completeness != "complete":
                        warnings.append(f"{kind} {target_uri}: direct triple limit reached")

        related(book, SCHEMA_NS + "isPartOf", "series", series)
        for record in (book, *series):
            related(record, DCTERMS_NS + "creator", "agent", agents)
            # P... literals remain raw; only genuine URI references are Agent lookups.
            if any(t.kind == "uri" for t in record.publisher_references):
                related(record, DCTERMS_NS + "publisher", "agent", agents)
        related(book, SCHEMA_NS + "provider", "holding", holdings)
        # No Work lookup: current Phase 2A evidence has not established that capability.
        completeness = "partial" if warnings else "complete"
        if book.completeness == "truncated":
            completeness = "truncated"
        return MADBRecordBundle(
            book, tuple(series), tuple(agents), tuple(holdings), tuple(dict.fromkeys(warnings)), completeness
        )

    def check_status(self) -> None:
        """Source-only bounded SELECT; never used by JapaneseBooksTalker.check_status."""
        self.search_by_isbn("9784832241190", refresh=True)
