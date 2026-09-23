"""Small source-neutral models. Preserve original values separately from mappings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchQuery:
    isbn: str = ""
    title: str = ""
    # Search-time volume/issue constraint, independent of GenericMetadata.issue output.
    issue: str = ""
    creator: str = ""
    publisher: str = ""
    mediatype: str = "books"
    from_date: str = ""
    until_date: str = ""
    itemno: str = ""
    sort_order: str = "title"


@dataclass
class ContentDates:
    """Dates and digital evidence for one linked Item; never merge different items."""

    uri: str
    issued: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    digitized: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)
    material_types: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)


@dataclass
class BookRecord:
    id: str
    title: str
    url: str = ""
    # Raw bibliographic series statements (NDL dcndl:seriesTitle), NOT work identity.
    # Future verified work series (e.g. MADB) must have a separate, provenance-bearing field.
    series_titles: list[str] = field(default_factory=list)
    # Original NDL dcndl:volume values, never the GenericMetadata.volume output field.
    volumes: list[str] = field(default_factory=list)
    creators: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    isbns: list[str] = field(default_factory=list)
    issued: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    abstracts: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    summary_provider: str = ""
    summary_medium: str = ""
    summary_item_id: str = ""
    subjects: list[str] = field(default_factory=list)
    classifications: list[str] = field(default_factory=list)
    ndc: list[str] = field(default_factory=list)
    editions: list[str] = field(default_factory=list)
    material_types: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    rights: list[str] = field(default_factory=list)
    # Full selected RDF record stays in ComicCacher; never distributed as a fixture.
    raw_xml: str = ""
    # Bibliographic issued/dates above keep their original meaning.
    digitized_dates: list[str] = field(default_factory=list)
    available_dates: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)
    content_dates: list[ContentDates] = field(default_factory=list)


@dataclass
class SearchPage:
    records: list[BookRecord]
    total: int
    warnings: list[str] = field(default_factory=list)
    truncated: bool = False
