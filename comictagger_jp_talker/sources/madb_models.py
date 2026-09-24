"""MADB source evidence, deliberately independent of NDL and GenericMetadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from comictalker.comictalker import TalkerError

Completeness = Literal["complete", "truncated", "partial"]
ErrorKind = Literal[
    "network", "http", "rate_limited", "timeout", "protocol", "query", "schema", "not_found", "truncated"
]


class MADBError(TalkerError):
    """One internal error with machine-readable classification and host compatibility."""

    def __init__(
        self, kind: ErrorKind, message: str, *, status: int | None = None, retry_after: str | None = None
    ) -> None:
        super().__init__(
            "MADB", message, code=2 if kind in ("network", "http", "rate_limited", "timeout") else 3
        )
        self.kind = kind
        self.status = status
        self.retry_after = retry_after


@dataclass(frozen=True)
class RDFTerm:
    kind: Literal["uri", "literal", "bnode"]
    value: str
    datatype: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class MADBStatement:
    subject: str
    predicate: str
    object: RDFTerm


@dataclass(frozen=True)
class MADBCredit:
    raw: RDFTerm
    source_predicate: str
    name_candidate: str | None = None
    role_raw: str | None = None
    agent_uri: str | None = None
    association: Literal["explicit", "name_match", "unresolved"] = "unresolved"


@dataclass(frozen=True)
class ExternalIdentifier:
    scheme: str
    raw: RDFTerm
    normalized: str | None
    subject_uri: str
    predicate: str
    provider: str | None = None


@dataclass(frozen=True, kw_only=True)
class MADBBookRecord:
    id: str
    uri: str
    types: tuple[str, ...]
    titles: tuple[RDFTerm, ...]
    alternative_titles: tuple[RDFTerm, ...]
    subtitles: tuple[RDFTerm, ...]
    display_labels: tuple[RDFTerm, ...]
    volumes: tuple[RDFTerm, ...]
    positions: tuple[RDFTerm, ...]
    isbns: tuple[RDFTerm, ...]
    editions: tuple[RDFTerm, ...]
    publication_dates: tuple[RDFTerm, ...]
    publishers: tuple[RDFTerm, ...]
    publisher_references: tuple[RDFTerm, ...]
    labels: tuple[RDFTerm, ...]
    series_statements: tuple[RDFTerm, ...]
    series_uris: tuple[str, ...]
    credits: tuple[MADBCredit, ...]
    creator_references: tuple[RDFTerm, ...]
    languages: tuple[RDFTerm, ...]
    genres: tuple[RDFTerm, ...]
    extent: tuple[MADBStatement, ...]
    external_identifiers: tuple[ExternalIdentifier, ...]
    statements: tuple[MADBStatement, ...]
    completeness: Completeness


@dataclass(frozen=True, kw_only=True)
class MADBSeriesRecord:
    id: str
    uri: str
    types: tuple[str, ...]
    titles: tuple[RDFTerm, ...]
    alternative_titles: tuple[RDFTerm, ...]
    publishers: tuple[RDFTerm, ...]
    publisher_references: tuple[RDFTerm, ...]
    labels: tuple[RDFTerm, ...]
    credits: tuple[MADBCredit, ...]
    creator_references: tuple[RDFTerm, ...]
    editions: tuple[RDFTerm, ...]
    publication_dates: tuple[RDFTerm, ...]
    number_of_items: tuple[RDFTerm, ...]
    statements: tuple[MADBStatement, ...]
    completeness: Completeness


@dataclass(frozen=True, kw_only=True)
class MADBAgentRecord:
    uri: str
    names: tuple[RDFTerm, ...]
    classifications: tuple[RDFTerm, ...]
    ndla: tuple[RDFTerm, ...]
    external_identifiers: tuple[ExternalIdentifier, ...]
    statements: tuple[MADBStatement, ...]
    completeness: Completeness


@dataclass(frozen=True, kw_only=True)
class MADBHoldingRecord:
    """Book-scoped snapshot; a Supplement URI is NOT permanent Book identity."""

    uri: str
    book_uri: str
    provider_names: tuple[RDFTerm, ...]
    material_identifiers: tuple[RDFTerm, ...]
    owner_identifiers: tuple[RDFTerm, ...]
    notes: tuple[RDFTerm, ...]
    external_identifiers: tuple[ExternalIdentifier, ...]
    statements: tuple[MADBStatement, ...]
    completeness: Completeness


@dataclass(frozen=True)
class MADBRecordBundle:
    book: MADBBookRecord
    series: tuple[MADBSeriesRecord, ...] = ()
    agents: tuple[MADBAgentRecord, ...] = ()
    holdings: tuple[MADBHoldingRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    completeness: Completeness = "complete"


@dataclass(frozen=True)
class MADBSearchResult:
    id: str
    uri: str
    identifiers: tuple[RDFTerm, ...]
    isbns: tuple[RDFTerm, ...]  # Matched terms only; never a full resource.


@dataclass(frozen=True)
class MADBSearchPage:
    records: tuple[MADBSearchResult, ...]
    truncated: bool = False
    warnings: tuple[str, ...] = ()
