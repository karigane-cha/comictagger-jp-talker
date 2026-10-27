"""Synthetic trace/transport cases. No authority assertions or live MADB requests."""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import datetime
from unittest.mock import Mock

import pytest
import requests
from test_linkage import ISBN, literal, resource_bytes
from test_madb import fixture, response, serve_bundle

from comictagger_jp_talker import acquisition, imprint_candidates
from comictagger_jp_talker.acquisition import (
    AcquisitionContext,
    AcquisitionEvent,
    AcquisitionFailure,
    AcquisitionTrace,
    ResourceAcquisition,
)
from comictagger_jp_talker.acquisition import AcquisitionReason as Reason
from comictagger_jp_talker.acquisition import AcquisitionStage as Stage
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_acquisition import MADBAcquisition
from comictagger_jp_talker.sources.madb_models import MADBError, RDFTerm
from comictagger_jp_talker.sources.madb_queries import DCTERMS_NS, ID_NS, SCHEMA_NS


@pytest.fixture
def sources(tmp_path, monkeypatch):
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    opened = []

    def create():
        source = madb.MADBSource(tmp_path / str(len(opened)))
        source.session.post = Mock()
        opened.append(source)
        return source

    yield create
    for source in opened:
        source.close()


def events(result, *, stage=None, kind=None, reason=None):
    return tuple(
        e
        for e in result.trace.events
        if (stage is None or e.stage == stage)
        and (kind is None or e.kind == kind)
        and (reason is None or e.reason == reason)
    )


def serve_series(source, references):
    """Preserve the supplied raw references; every valid C ID is a synthetic Series."""
    content = serve_bundle(source)
    content[ID_NS + "M1"] = resource_bytes(
        "M1", "MangaBook", [(SCHEMA_NS + "isPartOf", term) for term in references]
    )
    for term in references:
        if term.kind == "uri" and term.value.startswith(ID_NS + "C"):
            identifier = term.value.rsplit("/", 1)[-1]
            content[term.value] = resource_bytes(
                identifier, "MangaBookSeries", [(SCHEMA_NS + "name", literal(" Series "))]
            )
    return content


def assert_deep_frozen(value):
    if is_dataclass(value):
        assert value.__dataclass_params__.frozen
        for field in fields(value):
            assert_deep_frozen(getattr(value, field.name))
    elif isinstance(value, tuple):
        for item in value:
            assert_deep_frozen(item)
    else:
        assert value is None or isinstance(value, (str, int, bool))


@pytest.mark.parametrize("series_only", [False, True])
@pytest.mark.parametrize("book", ["book", "book_without_series"])
def test_success_public_and_traced_result_request_order_and_cache_are_identical(sources, series_only, book):
    plain, traced = sources(), sources()
    raw = serve_bundle(plain, book=book)
    serve_bundle(traced, book=book)
    public = plain.get_for_series_linkage if series_only else plain.get
    baseline = public("M1")
    result = traced._get_with_trace("M1", series_only=series_only)
    assert result.value == baseline and result.error is None
    assert plain.session.post.call_args_list == traced.session.post.call_args_list
    assert result.context.book == result.context.book_series_scope == State.COMPLETE
    has_series = book == "book"
    assert (
        result.context.series
        == result.context.relations
        == (State.COMPLETE if has_series else State.NOT_RELATED)
    )
    assert result.context.discovery == State.NOT_REQUESTED
    assert result.context.acquired_at is None
    for event in events(result, stage=Stage.NETWORK):
        assert event.response_sha256 == hashlib.sha256(raw[event.uri]).hexdigest()
        assert event.status == 200 and event.origin_fetched_at is not None
        assert datetime.fromisoformat(event.started_at).utcoffset() is not None
        assert event.cache_stored_at is None
    for event in events(result, stage=Stage.RELATION):
        parent = next(r for r in (result.value.book, *result.value.series) if r.uri == event.parent_uri)
        assert event.statement is parent.statements[event.statement_index]
        assert event.statement.subject == event.parent_uri
        assert event.statement.predicate == event.predicate
    count = traced.session.post.call_count
    warm = traced._get_with_trace("M1", series_only=series_only)
    assert warm.value == baseline and traced.session.post.call_count == count
    assert not events(warm, stage=Stage.NETWORK)
    for event in events(warm, reason=Reason.CACHE_HIT):
        assert event.origin_fetched_at is event.cache_stored_at is event.status is None
        assert event.response_sha256 == hashlib.sha256(raw[event.uri]).hexdigest()
    if series_only:
        assert result.context.agents == result.context.holdings == State.NOT_REQUESTED
        assert not events(result, stage=Stage.NETWORK, kind="agent")
        assert not events(result, stage=Stage.NETWORK, kind="holding")
        assert events(result, reason=Reason.SCOPE_EXCLUDED, kind="agent")
    assert_deep_frozen(result)
    with pytest.raises(FrozenInstanceError):
        result.context.book = State.UNAVAILABLE
    assert result.trace.run_id != warm.trace.run_id


@pytest.mark.parametrize("count", [1, 2, 13])
def test_multiple_series_budget_keeps_unrequested_references_and_raw(sources, count):
    source = sources()
    refs = tuple(RDFTerm("uri", ID_NS + f"C{i}") for i in range(1, count + 1))
    serve_series(source, refs)
    result = source._get_with_trace("M1", series_only=True)
    assert source.session.post.call_count == 1 + min(count, 12)
    assert len(result.value.series) == min(count, 12)
    relation_events = events(result, stage=Stage.RELATION, kind="series")
    assert tuple(e.statement.object for e in relation_events) == refs
    if count > 12:
        assert relation_events[-1].state == State.NOT_REQUESTED
        assert relation_events[-1].reason == Reason.RELATION_BUDGET
        assert relation_events[-1].limit == 12
        assert result.context.series == result.context.relations == State.PARTIAL
        assert result.context.resources[-1] == ResourceAcquisition(
            uri=ID_NS + "C13", state=State.NOT_REQUESTED
        )
        assert result.value.warnings == ("Related resource budget reached",)
    else:
        assert result.context.series == result.context.relations == State.COMPLETE


@pytest.mark.parametrize("with_valid", [False, True])
@pytest.mark.parametrize(
    "term",
    [
        RDFTerm("uri", "https://invalid.example/C9"),
        RDFTerm("uri", ID_NS + "M9"),
        RDFTerm("literal", " C9 ", language="ja"),
        RDFTerm("bnode", "raw-node"),
    ],
)
def test_invalid_relation_is_not_absence_and_preserves_qualifiers(sources, with_valid, term):
    plain, traced = sources(), sources()
    references = (RDFTerm("uri", ID_NS + "C1"), term) if with_valid else (term,)
    serve_series(plain, references)
    serve_series(traced, references)
    baseline = plain.get_for_series_linkage("M1")
    result = traced._get_with_trace("M1", series_only=True)
    assert result.value == baseline
    assert plain.session.post.call_args_list == traced.session.post.call_args_list
    assert result.context.relations == State.PARTIAL
    assert result.context.book_series_scope == State.PARTIAL
    assert result.context.series == (State.COMPLETE if with_valid else State.NOT_REQUESTED)
    (event,) = events(result, reason=Reason.INVALID_REFERENCE)
    assert event.uri is None and event.statement.object == term
    assert result.value.warnings == (f"Unresolved series reference on {ID_NS}M1",)


@pytest.mark.parametrize("stage", ["discovery", "book", "series"])
@pytest.mark.parametrize("problem", ["429", "503", "timeout", "network", "protocol", "schema", "not_found"])
def test_failure_outcomes_preserve_public_errors_partial_evidence_and_request_order(sources, stage, problem):
    plain, traced = sources(), sources()
    for source in (plain, traced):
        content = serve_series(source, tuple(RDFTerm("uri", ID_NS + f"C{i}") for i in range(1, 4)))

        def post(url, *, data, content=content, **kwargs):
            query = data["query"]
            target = "discovery" if "SELECT DISTINCT" in query else query.split("<", 1)[1].split(">", 1)[0]
            if target == {"discovery": "discovery", "book": ID_NS + "M1", "series": ID_NS + "C2"}[stage]:
                if problem == "timeout":
                    raise requests.Timeout("synthetic")
                if problem == "network":
                    raise requests.ConnectionError("synthetic")
                if problem.isdigit():
                    resp = response(b"", status=int(problem))
                    resp.headers["Retry-After"] = "17"
                    return resp
                if problem == "not_found":
                    return response(
                        resource_bytes("M9", "MangaBook", [])
                        if stage == "discovery"
                        else b'{"head":{"vars":["p","o"]},"results":{"bindings":[]}}'
                    )
                if problem == "schema":
                    return response(resource_bytes("M9", "MangaBook", []))
                return response(b"not JSON")
            return response(fixture("single") if target == "discovery" else content[target])

        source.session.post.side_effect = post
    if stage == "series":
        baseline = plain.get_for_series_linkage("M1")
        result = traced._get_with_trace("M1", series_only=True)
        assert result.error is None and result.value == baseline
        assert [r.id for r in result.value.series] == ["C1", "C3"]  # Continue after C2 fails.
        assert result.context.series == result.context.relations == State.PARTIAL
        assert [r.state for r in result.context.resources] == [
            State.COMPLETE,
            State.COMPLETE,
            State.UNAVAILABLE,
            State.COMPLETE,
        ]
    else:
        with pytest.raises(MADBError) as caught:
            plain.search_by_isbn(ISBN) if stage == "discovery" else plain.get_for_series_linkage("M1")
        result = (
            traced._search_by_isbn_with_trace(ISBN)
            if stage == "discovery"
            else traced._get_with_trace("M1", series_only=True)
        )
        assert result.value is None
        assert (result.error.kind, result.error.message, result.error.status, result.error.retry_after) == (
            caught.value.kind,
            caught.value.desc,
            caught.value.status,
            caught.value.retry_after,
        )
        if stage == "book":
            assert result.context.series == result.context.relations == State.NOT_REQUESTED
            assert events(result, reason=Reason.UPSTREAM_FAILED, kind="series")
        else:
            assert result.context.discovery == State.UNAVAILABLE
    assert traced.session.post.call_args_list == plain.session.post.call_args_list
    (snapshot_error,) = (e for e in events(result, stage=Stage.SNAPSHOT) if e.error)
    if problem.isdigit():
        assert snapshot_error.status == int(problem)
        assert snapshot_error.retry_after == "17"
    assert_deep_frozen(result)


@pytest.mark.parametrize("kind", ["book", "series", "discovery"])
def test_exact_row_cap_is_incomplete_and_not_cached(sources, kind):
    source = sources()
    if kind == "discovery":
        source.maximum_candidates = 1
        source.session.post.side_effect = lambda *a, **kw: response(fixture("single"))
    else:
        serve_series(source, (RDFTerm("uri", ID_NS + "C1"),) if kind == "series" else ())
        source.maximum_triples = 3 if kind == "series" else 2

    def get():
        if kind == "discovery":
            return source._search_by_isbn_with_trace(ISBN)
        return source._get_with_trace("M1", series_only=True)

    result = get()
    assert events(result, stage=Stage.SNAPSHOT, kind=kind, reason=Reason.ROW_LIMIT)
    if kind == "book":
        assert result.context.book == State.TRUNCATED
        assert result.context.relations == State.PARTIAL  # Empty truncated Book is not absence.
    elif kind == "series":
        assert result.context.series == State.TRUNCATED
    else:
        assert result.context.discovery == State.TRUNCATED
    count = source.session.post.call_count
    get()
    assert source.session.post.call_count > count


def test_partial_book_snapshot_cannot_attest_no_relation(sources, monkeypatch):
    """Synthetic parser output: the production parser currently emits complete/truncated only."""
    source = sources()
    serve_series(source, ())
    original = madb.parse_resource
    monkeypatch.setattr(
        madb, "parse_resource", lambda *a, **kw: replace(original(*a, **kw), completeness="partial")
    )
    result = source._get_with_trace("M1", series_only=True)
    assert result.context.book == State.PARTIAL
    assert result.context.series == State.NOT_REQUESTED
    assert result.context.relations == result.context.book_series_scope == State.PARTIAL
    assert result.value.book.completeness == "partial"


@pytest.mark.parametrize("kind", ["book", "discovery"])
def test_byte_cap_and_excess_rows_are_distinct(sources, monkeypatch, kind):
    source = sources()
    source.session.post.side_effect = lambda *a, **kw: response(b"x" * 11)
    monkeypatch.setattr(madb, "MAX_RESPONSE_BYTES", 10)
    get = (
        (lambda: source._get_with_trace("M1", series_only=True))
        if kind == "book"
        else lambda: source._search_by_isbn_with_trace(ISBN)
    )
    result = get()
    (event,) = events(result, stage=Stage.NETWORK)
    assert event.reason == Reason.BYTE_LIMIT and event.state == State.TRUNCATED
    assert event.limit == 10
    assert event.response_sha256 is event.origin_fetched_at is None
    assert result.error.kind == "truncated" and result.value is None
    monkeypatch.setattr(madb, "MAX_RESPONSE_BYTES", 2 * 1024 * 1024)
    source.maximum_candidates = source.maximum_triples = 1
    source.session.post.side_effect = lambda *a, **kw: response(
        fixture("book_without_series" if kind == "book" else "equivalent")
    )
    result = get()
    assert events(result, stage=Stage.SNAPSHOT, reason=Reason.ROW_LIMIT)
    assert result.value is None and result.error.kind == "truncated"


def test_zero_discovery_cache_invalid_refresh_and_no_origin_time_fabrication(sources):
    source = sources()
    source.session.post.side_effect = lambda *a, **kw: response(fixture("empty"))
    original = source.cache.add_search_results
    source.cache.add_search_results = Mock(wraps=original)
    first = source._search_by_isbn_with_trace(ISBN)
    assert first.value.records == () and first.context.discovery == State.COMPLETE
    assert events(first, reason=Reason.CACHE_MISS)
    namespace, key, entries, _ = source.cache.add_search_results.call_args.args
    warm = source._search_by_isbn_with_trace(ISBN)
    assert warm.value == first.value and source.session.post.call_count == 1
    assert events(warm, reason=Reason.CACHE_HIT)
    original(namespace, key, [type(entries[0])(key, b"not-json")], True)
    renewed = source._search_by_isbn_with_trace(ISBN)
    (bad,) = events(renewed, reason=Reason.CACHE_INVALID)
    assert bad.error.kind == "protocol"
    assert bad.response_sha256 == hashlib.sha256(b"not-json").hexdigest()
    assert bad.origin_fetched_at is bad.cache_stored_at is None
    assert renewed.value == first.value and source.session.post.call_count == 2
    refreshed = source._search_by_isbn_with_trace(ISBN, refresh=True)
    assert refreshed.value == first.value and source.session.post.call_count == 3
    assert events(refreshed, reason=Reason.REFRESH) and not events(refreshed, reason=Reason.CACHE_HIT)
    assert len({e.query_key for r in (first, warm, renewed, refreshed) for e in r.trace.events}) == 1


@pytest.mark.parametrize("incomplete_flag", [False, True])
def test_invalid_book_cache_keeps_invalid_evidence_then_fetches_once(sources, incomplete_flag):
    source = sources()
    serve_bundle(source, book="book_without_series")
    original = source.cache.add_search_results
    source.cache.add_search_results = Mock(wraps=original)
    first = source._get_with_trace("M1", series_only=True)
    namespace, key, entries, _ = source.cache.add_search_results.call_args.args
    raw = fixture("book_without_series") if incomplete_flag else b"{}"
    original(namespace, key, [type(entries[0])(key, raw)], not incomplete_flag)
    if incomplete_flag:
        # ComicCacher refuses to downgrade a complete row; inject the legacy read contract.
        cached = source.cache.get_search_results(namespace, key)
        source.cache.get_search_results = Mock(return_value=[cached[0]._replace(complete=False)])
    result = source._get_with_trace("M1", series_only=True)
    assert first.value == result.value and source.session.post.call_count == 2
    assert events(result, reason=Reason.CACHE_INVALID)
    assert result.context.book == State.COMPLETE


def test_cache_expiration_is_a_miss_without_invented_expiration_timestamp(sources):
    source = sources()
    serve_bundle(source, book="book_without_series")
    first = source._get_with_trace("M1", series_only=True)
    # Simulate the host cache's absent/expired return, without changing its expiration policy.
    source.cache.get_search_results = Mock(return_value=[])
    result = source._get_with_trace("M1", series_only=True)
    assert result.value == first.value and source.session.post.call_count == 2
    assert events(result, reason=Reason.CACHE_MISS)
    assert all(e.cache_stored_at is None for e in result.trace.events)


def test_full_scope_duplicate_relations_do_not_refetch_and_light_does_not_claim_absence(sources):
    source = sources()
    content = serve_bundle(source)
    raw = json.loads(content[ID_NS + "M1"])
    raw["results"]["bindings"] = [
        r for r in raw["results"]["bindings"] if r["p"]["value"] != DCTERMS_NS + "publisher"
    ]
    raw["results"]["bindings"].append(
        {"p": {"type": "uri", "value": DCTERMS_NS + "publisher"}, "o": {"type": "uri", "value": ID_NS + "C2"}}
    )
    content[ID_NS + "M1"] = json.dumps(raw).encode()
    light = source._get_with_trace("M1", series_only=True)
    assert light.context.agents == light.context.holdings == State.NOT_REQUESTED
    full = source._get_with_trace("M1")
    assert full.context.agents == full.context.holdings == State.COMPLETE
    (duplicate,) = events(full, reason=Reason.DUPLICATE)
    assert duplicate.uri == ID_NS + "C2" and duplicate.state == State.COMPLETE
    assert len(events(full, stage=Stage.NETWORK)) == 3
    assert full.value.book == light.value.book and full.value.series == light.value.series


def test_storage_and_programming_errors_keep_original_boundaries(sources):
    source = sources()
    for error in (OSError("synthetic"), sqlite3.OperationalError("synthetic"), AssertionError("synthetic")):
        source.cache.get_search_results = Mock(side_effect=error)
        with pytest.raises(type(error)) as caught:
            source._get_with_trace("M1")
        assert caught.value is error
    with pytest.raises(ValueError):
        source._get_with_trace("https://invalid.example/M1")
    with pytest.raises(ValueError):
        source._search_by_isbn_with_trace("invalid")
    source.session.post.assert_not_called()
    source.close()
    with pytest.raises(RuntimeError, match="closed"):
        source._get_with_trace("M1")


def test_models_reexport_exact_types_and_reject_mutable_contracts():
    for name in ("AcquisitionState", "ResourceAcquisition", "AcquisitionContext"):
        assert getattr(acquisition, name) is getattr(imprint_candidates, name)
    assert [s.value for s in State] == [
        "complete",
        "truncated",
        "partial",
        "unavailable",
        "not_requested",
        "not_related",
    ]
    assert AcquisitionContext().resources == ()
    with pytest.raises(ValueError):
        AcquisitionContext(resources=[])
    with pytest.raises(ValueError):
        AcquisitionContext(book="complete")
    with pytest.raises(ValueError):
        ResourceAcquisition(uri="", state=State.COMPLETE)
    with pytest.raises(ValueError):
        AcquisitionTrace(run_id="run", started_at="start", finished_at="end", events=[])
    with pytest.raises(ValueError):
        AcquisitionFailure(kind="http", message="error", status={})
    with pytest.raises(ValueError):
        AcquisitionEvent(
            stage=Stage.CACHE,
            state=State.COMPLETE,
            reason=Reason.CACHE_HIT,
            kind="book",
            observed_at="now",
            statement={},
        )
    with pytest.raises(ValueError):
        MADBAcquisition(
            value=None,
            context=AcquisitionContext(),
            trace=AcquisitionTrace(run_id="run", started_at="start", finished_at="end", events=()),
        )


@pytest.mark.parametrize("series_only", [False, True])
@pytest.mark.parametrize("mode", ["refresh", "budget", "invalid_cache"])
def test_bounded_and_refetched_public_trace_parity(sources, monkeypatch, series_only, mode):
    if mode == "budget":
        monkeypatch.setattr(madb, "MAX_RELATIONS", 1)
    plain, traced = sources(), sources()
    for source in (plain, traced):
        serve_bundle(source)
        source.cache.add_search_results = Mock(wraps=source.cache.add_search_results)
    public = plain.get_for_series_linkage if series_only else plain.get
    baseline = public("M1")
    first = traced._get_with_trace("M1", series_only=series_only)
    if mode == "invalid_cache":
        for source in (plain, traced):
            namespace, key, entries, _ = source.cache.add_search_results.call_args.args
            source.cache.add_search_results(namespace, key, [type(entries[0])(key, b"{}")], True)
    output = public("M1", refresh=mode == "refresh")
    result = traced._get_with_trace("M1", refresh=mode == "refresh", series_only=series_only)
    assert baseline == first.value == output == result.value
    assert plain.session.post.call_args_list == traced.session.post.call_args_list
    assert plain.cache.add_search_results.call_args_list == traced.cache.add_search_results.call_args_list
    if mode == "invalid_cache":
        assert len(events(result, reason=Reason.CACHE_INVALID)) == 1
    if mode == "refresh":
        assert not events(result, reason=Reason.CACHE_HIT)


def test_book_series_resource_context_is_not_overwritten_by_excluded_agent_role(sources):
    source = sources()
    content = serve_series(source, (RDFTerm("uri", ID_NS + "C1"),))
    content[ID_NS + "M1"] = resource_bytes(
        "M1",
        "MangaBook",
        [
            (SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + "C1")),
            (DCTERMS_NS + "creator", RDFTerm("uri", ID_NS + "C1")),
        ],
    )
    result = source._get_with_trace("M1", series_only=True)
    assert result.context.resources[-1] == ResourceAcquisition(uri=ID_NS + "C1", state=State.COMPLETE)
    assert result.context.agents == State.NOT_REQUESTED
    (excluded,) = events(result, stage=Stage.RELATION, kind="agent")
    assert excluded.uri == ID_NS + "C1" and excluded.reason == Reason.SCOPE_EXCLUDED


def test_all_series_failures_are_unavailable_not_absent(sources):
    source = sources()
    content = serve_series(source, (RDFTerm("uri", ID_NS + "C1"),))
    content[ID_NS + "C1"] = b"{}"
    result = source._get_with_trace("M1", series_only=True)
    assert result.value.series == ()
    assert result.context.series == result.context.relations == State.UNAVAILABLE
    assert result.context.book_series_scope == State.PARTIAL


def test_full_scope_records_unobserved_agents_of_a_failed_series(sources):
    source = sources()
    content = serve_series(source, (RDFTerm("uri", ID_NS + "C1"),))
    content[ID_NS + "C1"] = b"{}"
    result = source._get_with_trace("M1")
    assert result.context.agents == State.NOT_REQUESTED
    assert result.context.holdings == State.NOT_RELATED
    (missing,) = events(result, kind="agent", reason=Reason.UPSTREAM_FAILED)
    assert missing.parent_uri == ID_NS + "C1"
    assert missing.statement in result.value.book.statements
