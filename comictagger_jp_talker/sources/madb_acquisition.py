"""Internal source trace assembly; no requests or linkage policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from comictagger_jp_talker.acquisition import (
    AcquisitionContext,
    AcquisitionEvent,
    AcquisitionFailure,
    AcquisitionReason,
    AcquisitionStage,
    AcquisitionState,
    AcquisitionTrace,
    ResourceAcquisition,
)
from comictagger_jp_talker.sources.madb_models import MADBError, MADBRecordBundle, MADBSearchPage
from comictagger_jp_talker.sources.madb_queries import SCHEMA_NS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def failure(error: MADBError) -> AcquisitionFailure:
    return AcquisitionFailure(
        kind=error.kind, message=error.desc, status=error.status, retry_after=error.retry_after
    )


def aggregate(states: tuple[AcquisitionState, ...]) -> AcquisitionState:
    if not states:
        return AcquisitionState.NOT_REQUESTED
    relevant = set(states) - {AcquisitionState.NOT_RELATED}
    if not relevant:
        return AcquisitionState.NOT_RELATED
    if len(relevant) == 1:
        return next(iter(relevant))
    return AcquisitionState.PARTIAL


@dataclass(frozen=True, kw_only=True)
class MADBAcquisition:
    """Internal outcome. Public source methods retain their original exceptions."""

    value: MADBRecordBundle | MADBSearchPage | None
    context: AcquisitionContext
    trace: AcquisitionTrace
    error: AcquisitionFailure | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.error is None):
            raise ValueError("Acquisition must contain either a value or an error")
        if self.value is not None and not isinstance(self.value, (MADBRecordBundle, MADBSearchPage)):
            raise ValueError("Invalid acquisition value")
        if not isinstance(self.context, AcquisitionContext) or not isinstance(self.trace, AcquisitionTrace):
            raise ValueError("Invalid acquisition context or trace")
        if self.error is not None and not isinstance(self.error, AcquisitionFailure):
            raise ValueError("Invalid acquisition error")


class _Recorder:
    """Mutable only during a single call; never stored on the source or returned."""

    def __init__(self) -> None:
        self.run_id = uuid4().hex
        self.started_at = utc_now()
        self.events: list[AcquisitionEvent] = []

    def emit(self, stage, state, reason, kind, **facts) -> None:
        self.events.append(
            AcquisitionEvent(
                stage=stage, state=state, reason=reason, kind=kind, observed_at=utc_now(), **facts
            )
        )

    def finish(self, value, error=None) -> MADBAcquisition:
        events = tuple(self.events)
        snapshots = tuple(e for e in events if e.stage == AcquisitionStage.SNAPSHOT)
        scopes = tuple(
            e
            for e in events
            if e.stage == AcquisitionStage.SCOPE and e.reason != AcquisitionReason.ENUMERATED
        )
        discovery = tuple(e.state for e in snapshots if e.kind == "discovery")
        books = tuple(e.state for e in snapshots if e.kind == "book")
        series_scope = tuple(e.state for e in scopes if e.kind == "series")
        resources = {}
        for event in events:
            if (
                event.uri
                and event.kind in ("book", "series")
                and (event.stage == AcquisitionStage.SNAPSHOT or event.stage == AcquisitionStage.RELATION)
            ):
                resources[event.uri] = ResourceAcquisition(uri=event.uri, state=event.state)
        series = tuple(
            e.state for e in events if e.stage == AcquisitionStage.RELATION and e.kind == "series" and e.uri
        )
        relations = aggregate(series_scope)
        series_state = (
            AcquisitionState.NOT_RELATED if relations == AcquisitionState.NOT_RELATED else aggregate(series)
        )
        book_state = aggregate(books)
        complete_scope = (
            book_state == AcquisitionState.COMPLETE
            and series_state in (AcquisitionState.COMPLETE, AcquisitionState.NOT_RELATED)
            and relations in (AcquisitionState.COMPLETE, AcquisitionState.NOT_RELATED)
        )
        context = AcquisitionContext(
            discovery=aggregate(discovery),
            book=book_state,
            series=series_state,
            relations=relations,
            resources=tuple(resources.values()),
            agents=aggregate(tuple(e.state for e in scopes if e.kind == "agent")),
            holdings=aggregate(tuple(e.state for e in scopes if e.kind == "holding")),
            request_id=self.run_id,
            # Individual network event times cannot attest one origin time for a bundle.
            acquired_at=None,
            book_series_scope=(
                AcquisitionState.COMPLETE
                if complete_scope
                else book_state
                if book_state != AcquisitionState.COMPLETE
                else AcquisitionState.PARTIAL
            ),
        )
        return MADBAcquisition(
            value=value,
            error=error,
            context=context,
            trace=AcquisitionTrace(
                run_id=self.run_id, started_at=self.started_at, finished_at=utc_now(), events=events
            ),
        )

    def interrupted(self, uri: str, series_only: bool) -> None:
        for kind in ("series", "agent", "holding"):
            excluded = series_only and kind != "series"
            self.emit(
                AcquisitionStage.SCOPE,
                AcquisitionState.NOT_REQUESTED,
                AcquisitionReason.SCOPE_EXCLUDED if excluded else AcquisitionReason.UPSTREAM_FAILED,
                kind,
                parent_uri=uri,
                predicate=SCHEMA_NS + "isPartOf" if kind == "series" else None,
            )
