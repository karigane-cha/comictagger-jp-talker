"""Conservative Japanese bibliographic mappings to real ComicTagger types."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, replace

import isocodes
from comicapi.genericmetadata import ComicSeries, Credit, GenericMetadata, MetadataOrigin
from comicapi.utils import parse_url

from comictagger_jp_talker.isbn import isbn13
from comictagger_jp_talker.models import BookRecord, ContentDates

_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_VOLUME = re.compile(
    r"^(?P<series>.+?)(?:[.．]\s*|\s+|\s*第)(?P<num>[0-9０-９]{1,3})(?:巻)?"
    r"(?:\s*(?:\([^()（）]+\)|（[^()（）]+）))?$"
)


def infer_volume(title: str) -> tuple[str, str | None]:
    """A delimited terminal 1–3 digit number, optionally followed by one subtitle.

    This is a fallback, not proof of a volume. Original title is always retained.
    Subtitle parentheses must match and cannot be nested or repeated.
    Years, decimals, ranges and undelimited digits are left alone.
    """
    match = _VOLUME.fullmatch(title)
    if match and not re.search(r"[0-9０-９][.．]$", match["series"]):
        series = match["series"].rstrip()
        if series and not series[-1:].isdigit():
            return series, str(int(match["num"].translate(_DIGITS)))
    return title, None


def issue_number(value: str) -> str:
    match = re.fullmatch(r"\s*(?:第)?([0-9０-９]+)(?:巻)?\s*", value)
    return str(int(match[1].translate(_DIGITS))) if match else value


_EXPLICIT_VOLUME = re.compile(
    r"\s*(?:第)?(?P<num>[0-9０-９]{1,3})(?:巻)?"
    r"(?:\s*(?:\([^()（）]+\)|（[^()（）]+）))?\s*"
)


def explicit_volume_number(value: str) -> str | None:
    """Extract an integer from NDL volume text without changing its source value.

    Accept only 1–3 digits and one matching, non-nested subtitle block.
    Unknown labels, ranges, decimals and year-like values are not integers.
    """
    match = _EXPLICIT_VOLUME.fullmatch(value)
    return str(int(match["num"].translate(_DIGITS))) if match else None


@dataclass(frozen=True)
class ResolvedNumber:
    value: str | None
    explicit: str | None
    inferred: str | None
    conflict: bool
    requested: str | None = None
    source: str | None = None


def resolve_record_number(record: BookRecord, existing_issue: str = "") -> ResolvedNumber:
    """Keep NDL data intact; preserve explicit > existing > inferred unless sources conflict.

    Matching callers first resolve WITHOUT existing_issue so a request cannot
    prove its own match. Requested values are never treated as source data.
    """
    # Deduplicate after normalization. Retain unrecognized labels as opaque values:
    # dropping them would hide conflicts (e.g. ["1", "上"]) and lose Issue labels.
    explicit_values = list(dict.fromkeys(explicit_volume_number(v) or v for v in record.volumes if v.strip()))
    explicit = explicit_values[0] if len(explicit_values) == 1 else None
    inferred = infer_volume(record.title)[1]
    requested = issue_number(existing_issue) if existing_issue.strip() else None
    conflict = len(explicit_values) > 1 or bool(explicit and inferred and explicit != inferred)
    value, source = None, None
    if not conflict:
        for candidate, origin in ((explicit, "ndl"), (requested, "existing"), (inferred, "title")):
            if candidate:
                value, source = candidate, origin
                break
    return ResolvedNumber(value, explicit, inferred, conflict, requested, source)


def number_details(record: BookRecord, resolved: ResolvedNumber) -> list[str]:
    details = []
    if record.volumes:
        details.append("NDL 巻次（原データ）: " + " / ".join(record.volumes))
    if resolved.inferred:
        details.append("タイトル推定巻: " + resolved.inferred)
    if resolved.requested:
        details.append("既存・要求巻: " + resolved.requested)
    if resolved.conflict:
        details.append(
            "巻番号の不一致: NDL 明示値とタイトル推定値、または複数の明示値が矛盾しています。"
            "巻番号は未出力です。"
        )
    return details


_ROLES = {
    "原作": ("Writer",),
    "著": ("Writer",),
    "著者": ("Writer",),
    "作": ("Writer",),
    "文": ("Writer",),
    "作画": ("Artist",),
    "漫画": ("Artist",),
    "画": ("Artist",),
    "絵": ("Artist",),
    "訳": ("Translator",),
    "翻訳": ("Translator",),
    "訳者": ("Translator",),
    "監訳": ("Translator",),
    "編": ("Editor",),
    "編集": ("Editor",),
    "編者": ("Editor",),
    "編著": ("Writer", "Editor"),
    "原案": ("Plotter",),
    "構成": ("Plotter",),
    "脚本": ("Scripter",),
    "シナリオ": ("Scripter",),
    "原作・脚本": ("Writer", "Scripter"),
    "線画": ("Inker",),
    "ペン入れ": ("Inker",),
    "彩色": ("Colorist",),
    "着色": ("Colorist",),
    "カラー": ("Colorist",),
    "下絵": ("Penciller",),
    # A manuscript, cover or lettering-related label alone need not mean drawing/lettering.
    "作画原稿": ("Other",),
    "表紙": ("Other",),
    "カバー": ("Other",),
    "表紙画": ("Cover Artist",),
    "表紙イラスト": ("Cover Artist",),
    "カバーイラスト": ("Cover Artist",),
    "カバー画": ("Cover Artist",),
    "装画": ("Cover Artist",),
    "レタリング": ("Letterer",),
    "写植": ("Letterer",),
    "植字": ("Letterer",),
    "文字": ("Other",),
    "監修": ("Other",),
    "解説": ("Other",),
    "校閲": ("Other",),
    "企画": ("Other",),
    "写真": ("Other",),
    "撮影": ("Other",),
    "デザイン": ("Other",),
    "装丁": ("Other",),
    "校注": ("Other",),
    "注": ("Other",),
    "注釈": ("Other",),
    "解題": ("Other",),
    "協力": ("Other",),
    "監修協力": ("Other",),
    "編集協力": ("Other",),
}
_ROLE_BRACKETS = {"[": "]", "［": "］", "(": ")", "（": "）"}
_BRACKET_CHARS = "".join(_ROLE_BRACKETS) + "".join(_ROLE_BRACKETS.values())


def normalize_role_syntax(value: str) -> str:
    """Strip one matching outer bracket pair from a role, never normalize a name."""
    value = value.strip()
    if len(value) >= 2 and _ROLE_BRACKETS.get(value[0]) == value[-1]:
        return value[1:-1].strip()
    return value


def split_person_and_role(value: str) -> tuple[str, str | None]:
    """Require a known whitespace-delimited role or an explicit terminal bracket.

    Unknown bare words cannot reliably be distinguished from names. Keep them
    intact unless the token explicitly ends in 担当/協力. Never split people.
    Malformed/nested brackets are kept verbatim rather than partially stripped.
    """
    text = value.rstrip()
    if text and text[-1] in _ROLE_BRACKETS.values():
        opening = next(k for k, v in _ROLE_BRACKETS.items() if v == text[-1])
        index = text.rfind(opening)
        if index > 0:
            person, wrapped = text[:index].rstrip(), text[index:]
            role = normalize_role_syntax(wrapped)
            if person.strip() and role and not any(c in _BRACKET_CHARS for c in person + role):
                return person, role
    parts = text.rsplit(None, 1)
    if len(parts) == 2:
        person, role = parts
        if role in _ROLES or (role.endswith(("担当", "協力")) and not any(c in _BRACKET_CHARS for c in role)):
            return person, role
    return value, None


def map_role(role: str) -> tuple[str, ...]:
    return _ROLES.get(normalize_role_syntax(role), ("Other",))


def parse_responsibility(value: str, *, creator_fallback: bool = False) -> list[Credit]:
    if not value.strip():
        return []
    person, role = split_person_and_role(value)
    roles = map_role(role) if role is not None else ("Writer" if creator_fallback else "Other",)
    return [Credit(person=person, role=mapped) for mapped in roles]


def map_credits(record: BookRecord) -> list[Credit]:
    # Responsibility statements carry roles and lack authority birth/death qualifiers.
    # Avoid adding authority names a second time when literal statements are available.
    values = record.responsibilities or record.creators
    credits: list[Credit] = []
    for entries, creator_fallback in ((values, not record.responsibilities), (record.contributors, False)):
        for value in entries:
            for credit in parse_responsibility(value, creator_fallback=creator_fallback):
                if (credit.person, credit.role) not in {(c.person, c.role) for c in credits}:
                    credits.append(credit)
    return credits


@dataclass(frozen=True)
class ResolvedDate:
    year: int | None = None
    month: int | None = None
    day: int | None = None
    source: str = "none"
    raw_value: str | None = None
    source_uri: str = ""
    field: str = ""
    warning: str = ""

    @property
    def value(self) -> tuple[int | None, int | None, int | None]:
        return self.year, self.month, self.day


def _resolve_date_values(issued: list[str], dates: list[str], *, source: str, uri: str = "") -> ResolvedDate:
    """Refine only compatible dates within ONE source; retain original precision."""
    parsed: list[ResolvedDate] = []
    for value, field in [(v, "dcterms:issued") for v in issued] + [(v, "dcterms:date") for v in dates]:
        match = re.fullmatch(r"([0-9]{4})(?:[-.]([0-9]{1,2})(?:[-.]([0-9]{1,2}))?)?", value)
        if not match:
            continue
        year, month, day = (int(v) if v else None for v in match.groups())
        try:
            datetime.date(year, month if month is not None else 1, day if day is not None else 1)
        except (ValueError, TypeError):
            continue
        parsed.append(ResolvedDate(year, month, day, source, value, uri, field))
    if not parsed:
        return ResolvedDate()
    best = parsed[0]
    for candidate in parsed[1:]:
        if all(a is None or a == b for a, b in zip(best.value, candidate.value, strict=True)):
            best = candidate
    return best


def publication_date(record: BookRecord) -> tuple[int | None, int | None, int | None]:
    """Backwards-compatible bibliographic date; never consume Item dates."""
    return _resolve_date_values(record.issued, record.dates, source="bibliographic").value


_DIGITAL_TYPES = {
    "http://ndl.go.jp/ndltype/OnlineResource",
    "http://ndl.go.jp/ndltype/OnlineJournal",
    "http://ndl.go.jp/ndltype/ElectronicResource",
    "http://ndl.go.jp/ndltype/Document",
    "http://ndl.go.jp/ndltype/ComputerDisc",
    "http://ndl.go.jp/ndltype/Magneticdisk",
    "オンライン資料",
    "オンラインジャーナル",
    "電子資料",
}
_DIGITAL_FORMATS = {"epub", "application/epub+zip", "pdf", "application/pdf"}
_DIGITAL_DESCRIPTIONS = {"電子書籍", "電子資料", "オンライン資料", "デジタル資料"}


def _digital_evidence(types: list[str], formats: list[str], descriptions: list[str]) -> bool:
    # Parser stores "label URI". Compare the whole URI/token, never a substring.
    return (
        any(v in _DIGITAL_TYPES or v.rsplit(" ", 1)[-1] in _DIGITAL_TYPES for v in types)
        or any(v.casefold() in _DIGITAL_FORMATS for v in formats)
        or bool(_DIGITAL_DESCRIPTIONS.intersection(descriptions))
    )


def _own_item(record: BookRecord, item: ContentDates) -> bool:
    return bool(record.url) and item.uri.partition("#")[0] == record.url


def _digital_item(item: ContentDates) -> bool:
    return bool(item.digitized) or _digital_evidence(item.material_types, item.formats, item.descriptions)


def is_digital_record(record: BookRecord) -> bool:
    # A linked digital edition alone does not turn a paper catalog record into an ebook.
    return (
        bool(record.digitized_dates)
        or _digital_evidence(record.material_types, record.formats, record.descriptions)
        or any(_own_item(record, item) and _digital_item(item) for item in record.content_dates)
    )


def _digital_date_items(record: BookRecord) -> list[ContentDates]:
    return [
        item
        for item in record.content_dates
        if _digital_item(item) or (_own_item(record, item) and is_digital_record(record))
    ]


def resolve_publication_date(record: BookRecord, *, source_mode: str = "auto") -> ResolvedDate:
    if source_mode not in ("auto", "bibliographic", "digital"):
        raise ValueError("日付の取得元は auto・bibliographic・digital のいずれかにしてください。")
    bibliographic = _resolve_date_values(record.issued, record.dates, source="bibliographic", uri=record.url)
    if source_mode == "bibliographic" or (source_mode == "auto" and not is_digital_record(record)):
        return bibliographic
    items = _digital_date_items(record)
    own = [item for item in items if _own_item(record, item)]
    # Prefer the selected record's own digital content; never refine it using another edition.
    candidates = []
    for item in own or items:
        resolved = _resolve_date_values(item.issued, item.dates, source="digital", uri=item.uri)
        if resolved.year is None:
            resolved = _resolve_date_values(item.digitized, [], source="digital", uri=item.uri)
            if resolved.year is not None:
                resolved = replace(resolved, field="dcndl:dateDigitized")
        if resolved.year is not None:
            candidates.append(resolved)
    if len({candidate.value for candidate in candidates}) > 1:
        return replace(bibliographic, warning="デジタル資料間の日付が異なるため、書誌日付を使用します。")
    if candidates:
        return candidates[0]  # Same resolved value if multiple; no cross-item precision merging.
    digitized = _resolve_date_values(record.digitized_dates, [], source="digital", uri=record.url)
    if digitized.year is not None:
        return replace(digitized, field="dcndl:dateDigitized")
    return bibliographic


def date_details(record: BookRecord, resolved: ResolvedDate) -> list[str]:
    bibliographic = list(dict.fromkeys(record.issued + record.dates))
    digital = [(record.url, record.digitized_dates)] + [
        (item.uri, list(dict.fromkeys(item.issued + item.dates + item.digitized)))
        for item in _digital_date_items(record)
    ]
    different = [(uri, values) for uri, values in digital if values and set(values) != set(bibliographic)]
    details = []
    if different:
        if bibliographic:
            details.append("書誌上の日付: " + " / ".join(bibliographic))
        details.extend(
            "デジタル版の日付: " + " / ".join(values) + " [" + uri + "]" for uri, values in different
        )
    if different or resolved.source == "digital":
        details.append(f"日付取得元: {resolved.source} / {resolved.source_uri} / {resolved.field}")
    if resolved.warning:
        details.append(resolved.warning)
    return details


def language_code(values: list[str]) -> str | None:
    if not values:
        return None  # Japanese-looking titles alone do not prove the language.
    code = values[0].rsplit("/", 1)[-1].lower()
    for key in ("alpha_2", "alpha_3", "bibliographic"):
        found = isocodes.languages.get(**{key: code})
        if found and found.get("alpha_2"):
            return found["alpha_2"]
    return None  # Keep unsupported/multiple codes in the source record, not a false 'ja'.


def to_metadata(
    record: BookRecord,
    *,
    existing_series: str = "",
    existing_issue: str = "",
    preferred_isbn: str = "",
    subject_tags: bool = False,
    volume_output: str = "issue",
    date_source: str = "auto",
) -> GenericMetadata:
    if volume_output not in ("volume", "issue", "both"):
        raise ValueError("巻番号の書き込み先は volume・issue・both のいずれかにしてください。")
    resolved = resolve_record_number(record, existing_issue)
    logical_number = resolved.value
    inferred_series, _ = infer_volume(record.title)
    # NDL seriesTitle may identify an imprint, publishing series or magazine.
    # Preserve it as source data, never treat it as a work title or work alias.
    series = existing_series or inferred_series
    volume = None
    if volume_output in ("volume", "both") and logical_number and re.fullmatch(r"[0-9]{1,3}", logical_number):
        volume = int(logical_number)
    issue = logical_number if volume_output in ("issue", "both") else None
    resolved_date = resolve_publication_date(record, source_mode=date_source)
    year, month, day = resolved_date.value
    isbns = list(dict.fromkeys(v for raw in record.isbns if (v := isbn13(raw))))
    preferred = isbn13(preferred_isbn)
    gtin = preferred if preferred in isbns else (isbns[0] if len(isbns) == 1 else None)
    notes = ["NDL サーチの API を使用", record.url]
    notes.extend(number_details(record, resolved))
    notes.extend(date_details(record, resolved_date))
    if volume_output in ("volume", "both") and logical_number and volume is None:
        notes.append("Volume へ整数変換できない巻番号（未出力）: " + logical_number)
    for label, values in (
        ("ISBN", record.isbns),
        ("NDL シリーズ表記（原データ）", record.series_titles),
        ("責任表示", record.responsibilities),
        ("著者原表記", record.creators),
        ("寄与者原表記", record.contributors),
        ("版", record.editions),
        ("資料種別", record.material_types),
        ("データ提供元", record.providers),
        ("利用条件", record.rights),
        ("書誌注記", record.descriptions),
    ):
        if values:
            notes.append(f"{label}: " + " / ".join(values))
    if record.summary_item_id:
        notes.append(
            f"要約提供元: {record.summary_provider or 'NDL Search'}"
            f" / {record.summary_medium} / {record.summary_item_id}"
        )
    return GenericMetadata(
        data_origin=MetadataOrigin("jpbooks", "Japanese Books"),
        issue_id=record.id,
        series_id=record.id,
        title=record.title,
        series=series,
        issue=issue,
        volume=volume,
        publisher=" / ".join(record.publishers) or None,
        gtin=gtin,
        year=year,
        month=month,
        day=day,
        language=language_code(record.languages),
        description="\n\n".join(record.abstracts) or None,
        web_links=[parse_url(record.url)] if record.url else [],
        credits=map_credits(record),
        tags=set(record.subjects[:10]) if subject_tags else set(),
        notes="\n".join(v for v in notes if v),
        format=" / ".join(record.editions + record.material_types) or None,
    )


def to_series(record: BookRecord, warning: str = "", *, date_source: str = "auto") -> ComicSeries:
    # Keep title/volume visible. Description is rendered as HTML by ComicTagger.
    import html

    md = to_metadata(record, date_source=date_source)
    details = [record.title, "Series: " + (md.series or "")]
    details.extend(number_details(record, resolve_record_number(record)))
    details.extend(date_details(record, resolve_publication_date(record, source_mode=date_source)))
    for label, values in (
        ("Author", record.responsibilities or record.creators),
        ("NDL シリーズ表記（原データ）", record.series_titles),
        ("ISBN", record.isbns),
        ("Publisher", record.publishers),
        ("Bibliographic date", record.issued + record.dates),
        ("Edition", record.editions),
        ("Material", record.material_types),
        ("Provider", record.providers),
        ("Rights", record.rights),
    ):
        if values:
            details.append(label + ": " + " / ".join(values))
    details.extend(record.abstracts)
    if record.descriptions:
        details.append("書誌注記: " + " / ".join(record.descriptions))
    if warning:
        details.insert(0, warning)
    return ComicSeries(
        id=record.id,
        name=record.title,
        aliases=set(),  # NDL does not establish alternate titles of the manga work here.
        count_of_issues=1,
        count_of_volumes=None,
        description="<br>".join(html.escape(v) for v in details),
        image_url="",
        publisher=md.publisher or "",
        start_year=md.year,
        format=md.format,
        web_links=md.web_links,
    )
