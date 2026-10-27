"""Immutable acquisition facts; no network, linkage, or metadata policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from comictagger_jp_talker.sources.madb_models import MADBStatement


class AcquisitionState(str, Enum):
    COMPLETE = "complete"
    TRUNCATED = "truncated"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"
    NOT_RELATED = "not_related"


@dataclass(frozen=True, kw_only=True)
class ResourceAcquisition:
    uri: str
    state: AcquisitionState

    def __post_init__(self) -> None:
        if not isinstance(self.uri, str) or not self.uri or not isinstance(self.state, AcquisitionState):
            raise ValueError("Invalid resource acquisition")


@dataclass(frozen=True, kw_only=True)
class AcquisitionContext:
    """Caller-supplied completion, not an instruction to fetch anything.

    NOT_REQUESTED defaults deliberately withhold eligibility. Resource states
    augment the Book/Series states; they cannot override incomplete snapshots.
    Agent/Holding states are informational and never used to infer absence.
    """

    discovery: AcquisitionState = AcquisitionState.NOT_REQUESTED
    book: AcquisitionState = AcquisitionState.NOT_REQUESTED
    series: AcquisitionState = AcquisitionState.NOT_REQUESTED
    relations: AcquisitionState = AcquisitionState.NOT_REQUESTED
    resources: tuple[ResourceAcquisition, ...] = ()
    agents: AcquisitionState = AcquisitionState.NOT_REQUESTED
    holdings: AcquisitionState = AcquisitionState.NOT_REQUESTED
    request_id: str | None = None
    acquired_at: str | None = None
    medium: str | None = None
    # Explicitly attested requested Book/Series scope, for a full bundle whose
    # partial state is confined to unneeded Agent/Holding acquisition.
    book_series_scope: AcquisitionState = AcquisitionState.NOT_REQUESTED

    def __post_init__(self) -> None:
        for name in ("discovery", "book", "series", "relations", "agents", "holdings", "book_series_scope"):
            if not isinstance(getattr(self, name), AcquisitionState):
                raise ValueError(f"Acquisition {name} must be an enum")
        if not isinstance(self.resources, tuple) or any(
            not isinstance(r, ResourceAcquisition) for r in self.resources
        ):
            raise ValueError("Acquisition resources must be an immutable tuple")
        for name in ("request_id", "acquired_at", "medium"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"Invalid acquisition {name}")


class AcquisitionStage(str, Enum):
    CACHE = "cache"
    NETWORK = "network"
    SNAPSHOT = "snapshot"
    RELATION = "relation"
    SCOPE = "scope"


class AcquisitionReason(str, Enum):
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_INVALID = "cache_invalid"
    REFRESH = "refresh"
    FETCHED = "fetched"
    FAILED = "failed"
    PARSED = "parsed"
    ROW_LIMIT = "row_limit"
    BYTE_LIMIT = "byte_limit"
    ENUMERATED = "enumerated"
    RESOLVED = "resolved"
    DUPLICATE = "duplicate"
    RELATION_BUDGET = "relation_budget"
    INVALID_REFERENCE = "invalid_reference"
    SCOPE_EXCLUDED = "scope_excluded"
    NON_URI_PUBLISHER = "non_uri_publisher"
    UPSTREAM_FAILED = "upstream_failed"
    NO_RELATION = "no_relation"
    PARENT_INCOMPLETE = "parent_incomplete"


@dataclass(frozen=True, kw_only=True)
class AcquisitionFailure:
    """A copy of error facts, never an exception with a mutable traceback."""

    kind: str
    message: str
    status: int | None = None
    retry_after: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind or not isinstance(self.message, str):
            raise ValueError("Invalid acquisition failure")
        if self.status is not None and type(self.status) is not int:
            raise ValueError("Invalid HTTP status")
        if self.retry_after is not None and not isinstance(self.retry_after, str):
            raise ValueError("Invalid Retry-After")


@dataclass(frozen=True, kw_only=True)
class AcquisitionEvent:
    """Ordered observations, separate from aggregate completeness.

    response_sha256 covers the exact complete response bytes available locally.
    A cache read never attests original HTTP headers or origin_fetched_at.
    statement_index addresses the parent's parsed statements, not HTTP row order.
    """

    stage: AcquisitionStage
    state: AcquisitionState
    reason: AcquisitionReason
    kind: str
    observed_at: str
    uri: str | None = None
    parent_uri: str | None = None
    predicate: str | None = None
    statement: MADBStatement | None = None
    statement_index: int | None = None
    isbn: str | None = None
    namespace: str | None = None
    query_key: str | None = None
    started_at: str | None = None
    origin_fetched_at: str | None = None
    cache_stored_at: str | None = None
    response_sha256: str | None = None
    limit: int | None = None
    status: int | None = None
    retry_after: str | None = None
    error: AcquisitionFailure | None = None

    def __post_init__(self) -> None:
        for name, cls in (
            ("stage", AcquisitionStage),
            ("state", AcquisitionState),
            ("reason", AcquisitionReason),
        ):
            if not isinstance(getattr(self, name), cls):
                raise ValueError(f"Invalid event {name}")
        if self.kind not in ("discovery", "book", "series", "agent", "holding"):
            raise ValueError("Invalid event kind")
        for name in (
            "observed_at",
            "uri",
            "parent_uri",
            "predicate",
            "isbn",
            "namespace",
            "query_key",
            "started_at",
            "origin_fetched_at",
            "cache_stored_at",
            "response_sha256",
            "retry_after",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Invalid event {name}")
        if not self.observed_at:
            raise ValueError("Missing observation time")
        if self.error is not None and not isinstance(self.error, AcquisitionFailure):
            raise ValueError("Invalid event failure")
        if self.status is not None and type(self.status) is not int:
            raise ValueError("Invalid event HTTP status")
        if self.limit is not None and (type(self.limit) is not int or self.limit < 1):
            raise ValueError("Invalid acquisition limit")
        if self.statement is not None and not isinstance(self.statement, MADBStatement):
            raise ValueError("Invalid event statement")
        if self.statement_index is not None and (
            type(self.statement_index) is not int or self.statement_index < 0 or self.statement is None
        ):
            raise ValueError("Invalid statement index")


@dataclass(frozen=True, kw_only=True)
class AcquisitionTrace:
    run_id: str
    started_at: str
    finished_at: str
    events: tuple[AcquisitionEvent, ...]

    def __post_init__(self) -> None:
        for name in ("run_id", "started_at", "finished_at"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"Invalid trace {name}")
        if not isinstance(self.events, tuple) or any(
            not isinstance(event, AcquisitionEvent) for event in self.events
        ):
            raise ValueError("Trace events must be an immutable tuple")
