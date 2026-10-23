"""Read-only MADB source, also used by the opt-in missing-Series supplement."""

from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import requests
from comictalker.comiccacher import ComicCacher
from comictalker.comiccacher import Series as CachedSeries
from comictalker.vendor.pyrate_limiter import Limiter, RequestRate
from urllib3.exceptions import ReadTimeoutError

from comictagger_jp_talker import __version__
from comictagger_jp_talker.acquisition import AcquisitionReason as Reason
from comictagger_jp_talker.acquisition import AcquisitionStage as Stage
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.sources import madb_parser
from comictagger_jp_talker.sources.madb_acquisition import (
    MADBAcquisition,
    _Recorder,
    aggregate,
    failure,
    utc_now,
)
from comictagger_jp_talker.sources.madb_models import MADBError, MADBRecordBundle, MADBSearchPage
from comictagger_jp_talker.sources.madb_parser import (
    MAX_RESPONSE_BYTES,
    parse_resource,
    parse_search,
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


@dataclass
class _Receipt:
    """Local transport facts; never escape into immutable acquisition outcomes."""

    status: int | None = None
    retry_after: str | None = None
    received_at: str | None = None
    byte_limit: bool = False


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

    def _request(self, query: str, *, _receipt: _Receipt | None = None) -> bytes:
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
                    if _receipt is not None:
                        _receipt.status = status
                        _receipt.retry_after = response.headers.get("Retry-After")
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
                            if _receipt is not None:
                                _receipt.byte_limit = True
                            raise MADBError("truncated", "MADB response exceeds byte cap")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    if _receipt is not None:
                        _receipt.received_at = utc_now()
                    return content
        except requests.Timeout as exc:
            raise MADBError("timeout", "MADB request timed out") from exc
        except requests.ConnectionError as exc:
            # requests wraps its existing urllib3 transport's streaming read timeout.
            if exc.args and isinstance(exc.args[0], ReadTimeoutError):
                raise MADBError("timeout", "MADB response read timed out") from exc
            raise MADBError("network", "MADB connection failed") from exc
        except requests.RequestException as exc:
            raise MADBError("network", f"MADB transport failure ({type(exc).__name__})") from exc

    def _load(
        self,
        namespace: str,
        query: str,
        parser,
        *,
        refresh: bool,
        context: str = "",
        _trace: _Recorder | None = None,
        kind: str = "discovery",
        uri: str | None = None,
        parent: str = "",
        relation: str = "",
        isbn: str | None = None,
    ):
        # Endpoint + template text/limits + parser version namespace + relation scope.
        key = hashlib.sha256(f"{ENDPOINT}\n{namespace}\n{context}\n{query}".encode()).hexdigest()
        facts = dict(
            kind=kind,
            uri=uri,
            parent_uri=parent or None,
            predicate=relation or None,
            isbn=isbn,
            namespace=namespace,
            query_key=key,
        )

        def emit(stage, state, reason, **extra):
            if _trace is not None:
                _trace.emit(stage, state, reason, **facts, **extra)

        def result_state(result):
            return (
                (State.TRUNCATED if result.truncated else State.COMPLETE)
                if isinstance(result, MADBSearchPage)
                else State(result.completeness)
            )

        with _LOCK:  # One request at a time across source instances, including body streaming.
            if self._closed:
                raise RuntimeError("MADBSource is closed")
            cached = [] if refresh else self.cache.get_search_results(namespace, key)
            if cached:
                digest = hashlib.sha256(cached[0].data.data).hexdigest() if _trace is not None else None
                try:
                    result = parser(cached[0].data.data)
                    if not cached[0].complete or not self._complete(result):
                        raise MADBError("truncated", "Incomplete cached response")
                    emit(Stage.CACHE, State.COMPLETE, Reason.CACHE_HIT, response_sha256=digest)
                    emit(Stage.SNAPSHOT, result_state(result), Reason.PARSED, response_sha256=digest)
                    return result
                except MADBError as exc:
                    emit(
                        Stage.CACHE,
                        State.UNAVAILABLE,
                        Reason.CACHE_INVALID,
                        response_sha256=digest,
                        error=failure(exc),
                    )
                    logger.warning("Invalid cached MADB response; refreshing %s:%s", namespace, key)
            else:
                emit(Stage.CACHE, State.NOT_REQUESTED, Reason.REFRESH if refresh else Reason.CACHE_MISS)
            receipt = _Receipt()
            started_at = utc_now() if _trace is not None else None
            try:
                content = self._request(query) if _trace is None else self._request(query, _receipt=receipt)
            except MADBError as exc:
                state = State.TRUNCATED if exc.kind == "truncated" else State.UNAVAILABLE
                reason = Reason.BYTE_LIMIT if receipt.byte_limit else Reason.FAILED
                extra = dict(
                    started_at=started_at,
                    status=receipt.status,
                    retry_after=receipt.retry_after,
                    error=failure(exc),
                    limit=MAX_RESPONSE_BYTES if receipt.byte_limit else None,
                )
                emit(Stage.NETWORK, state, reason, **extra)
                emit(Stage.SNAPSHOT, state, reason, **extra)
                raise
            digest = hashlib.sha256(content).hexdigest() if _trace is not None else None
            extra = dict(
                started_at=started_at,
                status=receipt.status,
                retry_after=receipt.retry_after,
                origin_fetched_at=receipt.received_at,
                response_sha256=digest,
            )
            emit(Stage.NETWORK, State.COMPLETE, Reason.FETCHED, **extra)
            try:
                result = parser(content)
            except MADBError as exc:
                reason = (
                    (Reason.BYTE_LIMIT if len(content) > madb_parser.MAX_RESPONSE_BYTES else Reason.ROW_LIMIT)
                    if exc.kind == "truncated"
                    else Reason.FAILED
                )
                emit(
                    Stage.SNAPSHOT,
                    State.TRUNCATED if exc.kind == "truncated" else State.UNAVAILABLE,
                    reason,
                    error=failure(exc),
                    limit=(
                        madb_parser.MAX_RESPONSE_BYTES
                        if reason == Reason.BYTE_LIMIT
                        else (self.maximum_candidates if kind == "discovery" else self.maximum_triples)
                        if reason == Reason.ROW_LIMIT
                        else None
                    ),
                    **extra,
                )
                raise
            state = result_state(result)
            emit(
                Stage.SNAPSHOT,
                state,
                Reason.ROW_LIMIT if state == State.TRUNCATED else Reason.PARSED,
                limit=(
                    (self.maximum_candidates if kind == "discovery" else self.maximum_triples)
                    if state == State.TRUNCATED
                    else None
                ),
                **extra,
            )
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
        return self._search_by_isbn(isbn, refresh=refresh)

    def _search_by_isbn(self, isbn: str, *, refresh: bool, _trace: _Recorder | None = None):
        query = isbn_query(isbn, self.maximum_candidates)
        return self._load(
            QUERY_CACHE,
            query,
            lambda data: parse_search(data, isbn, self.maximum_candidates),
            refresh=refresh,
            _trace=_trace,
            isbn=isbn,
        )

    def _resource(
        self,
        uri: str,
        kind: ResourceKind,
        *,
        refresh: bool,
        parent: str = "",
        relation: str = "",
        _trace: _Recorder | None = None,
    ):
        query = resource_query(uri, kind, self.maximum_triples)
        return self._load(
            RELATION_CACHE if parent else RESOURCE_CACHE,
            query,
            lambda data: parse_resource(data, uri, kind, self.maximum_triples, book_uri=parent),
            refresh=refresh,
            context=f"{parent}|{relation}|{kind}",
            _trace=_trace,
            kind=kind,
            uri=uri,
            parent=parent,
            relation=relation,
        )

    def _search_by_isbn_with_trace(self, isbn: str, *, refresh: bool = False) -> MADBAcquisition:
        trace = _Recorder()
        try:
            page = self._search_by_isbn(isbn, refresh=refresh, _trace=trace)
        except MADBError as exc:
            return trace.finish(None, failure(exc))
        return trace.finish(page)

    def _get_with_trace(
        self,
        book_id: str,
        *,
        refresh: bool = False,
        series_only: bool = False,
    ) -> MADBAcquisition:
        trace = _Recorder()
        # Preserve invalid-input ValueError and lifecycle/storage exceptions.
        uri = resource_uri(book_id, "book")
        try:
            bundle = self._get_bundle(book_id, refresh=refresh, series_only=series_only, _trace=trace)
        except MADBError as exc:
            trace.interrupted(uri, series_only)
            return trace.finish(None, failure(exc))
        return trace.finish(bundle)

    def get(self, book_id: str, *, refresh: bool = False) -> MADBRecordBundle:
        """Full Book, Series, Agent and Holding evidence, preserving the public source API."""
        return self._get_bundle(book_id, refresh=refresh, series_only=False)

    def get_for_series_linkage(self, book_id: str, *, refresh: bool = False) -> MADBRecordBundle:
        """Bounded whole Book/Series snapshots; Agent and Holding details are not requested.

        Whole direct triples retain all identity contradictions and row-limit evidence.
        Completeness refers only to the requested scope, not the full related graph.
        """
        return self._get_bundle(book_id, refresh=refresh, series_only=True)

    def _get_bundle(
        self,
        book_id: str,
        *,
        refresh: bool,
        series_only: bool,
        _trace: _Recorder | None = None,
    ) -> MADBRecordBundle:
        uri = resource_uri(book_id, "book")
        book = self._resource(uri, "book", refresh=refresh, _trace=_trace)
        series, agents, holdings, warnings = [], [], [], []
        if book.completeness != "complete":
            warnings.append("Book direct triple limit reached")
        seen: set[tuple[str, str]] = set()
        resolved: dict[tuple[str, str], State] = {}
        attempted = 0

        def related(record, predicate: str, kind: ResourceKind, target: list) -> None:
            nonlocal attempted
            states = []
            references = tuple((i, s) for i, s in enumerate(record.statements) if s.predicate == predicate)
            if _trace is not None:
                _trace.emit(
                    Stage.SCOPE,
                    State.COMPLETE if record.completeness == "complete" else State.PARTIAL,
                    Reason.ENUMERATED,
                    kind,
                    parent_uri=record.uri,
                    predicate=predicate,
                )
            for index, statement in references:
                term = statement.object
                facts = dict(
                    parent_uri=record.uri,
                    predicate=predicate,
                    statement=statement,
                    statement_index=index,
                )

                def observed(state, reason, target_uri=None, error=None, facts=facts):
                    states.append(state)
                    if _trace is not None:
                        _trace.emit(
                            Stage.RELATION,
                            state,
                            reason,
                            kind,
                            uri=target_uri,
                            error=error,
                            limit=MAX_RELATIONS if reason == Reason.RELATION_BUDGET else None,
                            **facts,
                        )

                try:
                    if term.kind != "uri":
                        raise ValueError
                    target_uri = resource_uri(term.value, kind)
                except ValueError:
                    # Retain raw evidence, including bnodes; never interpolate it in a query.
                    warnings.append(f"Unresolved {kind} reference on {record.uri}")
                    observed(State.PARTIAL, Reason.INVALID_REFERENCE)
                    continue
                if (kind, target_uri) in seen:
                    observed(resolved[(kind, target_uri)], Reason.DUPLICATE, target_uri)
                    continue
                seen.add((kind, target_uri))
                if attempted >= MAX_RELATIONS:
                    warnings.append("Related resource budget reached")
                    resolved[(kind, target_uri)] = State.NOT_REQUESTED
                    observed(State.NOT_REQUESTED, Reason.RELATION_BUDGET, target_uri)
                    continue
                attempted += 1
                try:
                    result = self._resource(
                        target_uri,
                        kind,
                        refresh=refresh,
                        parent=record.uri,
                        relation=predicate,
                        _trace=_trace,
                    )
                except MADBError as exc:
                    warnings.append(f"{kind} {target_uri}: {exc.kind} ({exc.desc})")
                    state = State.TRUNCATED if exc.kind == "truncated" else State.UNAVAILABLE
                    resolved[(kind, target_uri)] = state
                    observed(state, Reason.FAILED, target_uri, failure(exc))
                else:
                    target.append(result)
                    if result.completeness != "complete":
                        warnings.append(f"{kind} {target_uri}: direct triple limit reached")
                    state = State(result.completeness)
                    resolved[(kind, target_uri)] = state
                    observed(state, Reason.RESOLVED, target_uri)
            if _trace is not None:
                state = aggregate(tuple(states))
                reason = Reason.RESOLVED
                if record.completeness != "complete":
                    state, reason = State.PARTIAL, Reason.PARENT_INCOMPLETE
                elif not references:
                    state, reason = State.NOT_RELATED, Reason.NO_RELATION
                elif state == State.NOT_REQUESTED:
                    state = State.PARTIAL  # Budget-excluded references are unresolved relations.
                _trace.emit(Stage.SCOPE, state, reason, kind, parent_uri=record.uri, predicate=predicate)

        def not_requested(record, predicate, kind, reason):
            if _trace is None:
                return
            for index, statement in enumerate(record.statements):
                if statement.predicate != predicate:
                    continue
                try:
                    target_uri = (
                        resource_uri(statement.object.value, kind) if statement.object.kind == "uri" else None
                    )
                except ValueError:
                    target_uri = None
                _trace.emit(
                    Stage.RELATION,
                    State.NOT_REQUESTED,
                    reason,
                    kind,
                    uri=target_uri,
                    parent_uri=record.uri,
                    predicate=predicate,
                    statement=statement,
                    statement_index=index,
                )
            _trace.emit(
                Stage.SCOPE,
                State.NOT_REQUESTED,
                reason,
                kind,
                parent_uri=record.uri,
                predicate=predicate,
            )

        related(book, SCHEMA_NS + "isPartOf", "series", series)
        if not series_only:
            if _trace is not None:
                # Missing Series snapshots may contain further Agent references.
                # Retain that unobserved scope instead of attesting global absence.
                for event in tuple(_trace.events):
                    if event.stage != Stage.RELATION or event.kind != "series":
                        continue
                    if event.uri and any(s.uri == event.uri for s in series):
                        continue
                    _trace.emit(
                        Stage.SCOPE,
                        State.NOT_REQUESTED,
                        Reason.UPSTREAM_FAILED,
                        "agent",
                        parent_uri=event.uri,
                        statement=event.statement,
                    )
            for record in (book, *series):
                related(record, DCTERMS_NS + "creator", "agent", agents)
                # P... literals remain raw; only genuine URI references are Agent lookups.
                if any(t.kind == "uri" for t in record.publisher_references):
                    related(record, DCTERMS_NS + "publisher", "agent", agents)
                elif record.publisher_references:
                    not_requested(record, DCTERMS_NS + "publisher", "agent", Reason.NON_URI_PUBLISHER)
            related(book, SCHEMA_NS + "provider", "holding", holdings)
        else:
            for record in (book, *series):
                not_requested(record, DCTERMS_NS + "creator", "agent", Reason.SCOPE_EXCLUDED)
                not_requested(record, DCTERMS_NS + "publisher", "agent", Reason.SCOPE_EXCLUDED)
            not_requested(book, SCHEMA_NS + "provider", "holding", Reason.SCOPE_EXCLUDED)
        # No Work lookup: current Phase 2A evidence has not established that capability.
        completeness = "partial" if warnings else "complete"
        if book.completeness == "truncated":
            completeness = "truncated"
        return MADBRecordBundle(
            book,
            tuple(series),
            tuple(agents),
            tuple(holdings),
            tuple(dict.fromkeys(warnings)),
            completeness,
            "series_linkage" if series_only else "full",
        )

    def check_status(self) -> None:
        """Source-only bounded SELECT; never used by JapaneseBooksTalker.check_status."""
        self.search_by_isbn("9784832241190", refresh=True)
