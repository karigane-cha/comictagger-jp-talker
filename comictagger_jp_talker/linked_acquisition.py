"""Immutable linkage-run facts, independent of identity and supplement policy."""

from __future__ import annotations

from dataclasses import dataclass, fields

from comictagger_jp_talker.acquisition import (
    AcquisitionContext,
    AcquisitionEvent,
    AcquisitionFailure,
    AcquisitionState,
    AcquisitionTrace,
)
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.sources.madb_acquisition import MADBAcquisition
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, MADBSearchPage


def _tuple(value, item_type) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, item_type) for item in value):
        raise ValueError("Expected an immutable typed tuple")


@dataclass(frozen=True, kw_only=True)
class NDLInputSnapshot:
    """Raw comparison inputs only; no mutable BookRecord or inferred values."""

    id: str
    url: str
    title: str
    isbns: tuple[str, ...]
    volumes: tuple[str, ...]
    publishers: tuple[str, ...]
    editions: tuple[str, ...]
    issued: tuple[str, ...]
    dates: tuple[str, ...]
    series_titles: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in ("id", "url", "title"):
                if not isinstance(value, str):
                    raise ValueError("Invalid raw NDL scalar")
            else:
                _tuple(value, str)

    @classmethod
    def from_record(cls, record: BookRecord) -> NDLInputSnapshot:
        return cls(
            **{
                field.name: (
                    getattr(record, field.name)
                    if field.name in ("id", "url", "title")
                    else tuple(getattr(record, field.name))
                )
                for field in fields(cls)
            }
        )

    def to_record(self) -> BookRecord:
        """Create an independent private comparison input on every invocation."""
        return BookRecord(
            **{
                field.name: (
                    getattr(self, field.name)
                    if field.name in ("id", "url", "title")
                    else list(getattr(self, field.name))
                )
                for field in fields(self)
            }
        )


@dataclass(frozen=True, kw_only=True)
class ISBNDiscovery:
    isbn: str
    state: AcquisitionState
    reason: str
    page: MADBSearchPage | None = None
    acquisition: MADBAcquisition | None = None
    error: AcquisitionFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.isbn, str) or not isinstance(self.reason, str):
            raise ValueError("Invalid discovery identification")
        if not isinstance(self.state, AcquisitionState):
            raise ValueError("Invalid discovery state")
        for value, cls in (
            (self.page, MADBSearchPage),
            (self.acquisition, MADBAcquisition),
            (self.error, AcquisitionFailure),
        ):
            if value is not None and not isinstance(value, cls):
                raise ValueError("Invalid discovery evidence")


@dataclass(frozen=True, kw_only=True)
class DiscoveryAcquisition:
    planned_isbns: tuple[str, ...]
    attempts: tuple[ISBNDiscovery, ...]
    state: AcquisitionState
    truncated: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _tuple(self.planned_isbns, str)
        _tuple(self.attempts, ISBNDiscovery)
        _tuple(self.reasons, str)
        if tuple(item.isbn for item in self.attempts) != self.planned_isbns:
            raise ValueError("Discovery plan and outcomes differ")
        if not isinstance(self.state, AcquisitionState) or type(self.truncated) is not bool:
            raise ValueError("Invalid discovery aggregate")


@dataclass(frozen=True, kw_only=True)
class BookAcquisitionContext:
    """Discovery identity and its outcome; rejected returned bundles remain here.

    context adds run-wide discovery to the original source context. The untouched
    source outcome is acquisition. A mismatch must never be supplied to an evaluator
    as an accepted bundle; included_in_linkage explicitly distinguishes that case.
    """

    book_id: str
    book_uri: str
    context: AcquisitionContext
    reason: str
    acquisition: MADBAcquisition | None = None
    bundle: MADBRecordBundle | None = None
    error: AcquisitionFailure | None = None
    included_in_linkage: bool = False

    def __post_init__(self) -> None:
        if any(not isinstance(v, str) for v in (self.book_id, self.book_uri, self.reason)):
            raise ValueError("Invalid Book identification")
        if not isinstance(self.context, AcquisitionContext) or type(self.included_in_linkage) is not bool:
            raise ValueError("Invalid Book context")
        for value, cls in (
            (self.acquisition, MADBAcquisition),
            (self.bundle, MADBRecordBundle),
            (self.error, AcquisitionFailure),
        ):
            if value is not None and not isinstance(value, cls):
                raise ValueError("Invalid Book evidence")
        if self.included_in_linkage and (
            self.bundle is None
            or self.error is not None
            or (self.bundle.book.id, self.bundle.book.uri) != (self.book_id, self.book_uri)
        ):
            raise ValueError("Accepted Book differs from discovery")


@dataclass(frozen=True, kw_only=True)
class LinkedAcquisitionContext:
    """One local run, not a claim of atomic server snapshots or acquisition time."""

    run_id: str
    started_at: str
    finished_at: str
    scope: str
    ndl_input: NDLInputSnapshot
    discovery: DiscoveryAcquisition
    books: tuple[BookAcquisitionContext, ...]
    traces: tuple[AcquisitionTrace, ...]
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if any(not isinstance(v, str) or not v for v in (self.run_id, self.started_at, self.finished_at)):
            raise ValueError("Invalid linkage run identification")
        if self.scope not in ("full", "series_linkage"):
            raise ValueError("Invalid acquisition scope")
        if not isinstance(self.ndl_input, NDLInputSnapshot) or not isinstance(
            self.discovery, DiscoveryAcquisition
        ):
            raise ValueError("Invalid linkage input or discovery")
        _tuple(self.books, BookAcquisitionContext)
        _tuple(self.traces, AcquisitionTrace)
        _tuple(self.issues, str)

    @property
    def events(self) -> tuple[AcquisitionEvent, ...]:
        """Original objects in source-call and event order; never reinterpreted."""
        return tuple(event for trace in self.traces for event in trace.events)
