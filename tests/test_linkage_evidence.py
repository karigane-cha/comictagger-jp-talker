"""Synthetic linkage runs; golden results were captured before the core migration."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from unittest.mock import Mock, call

import pytest
import requests
from test_linkage import ISBN, OTHER_ISBN, OTHER_URL, URL, bundle, record, source_for
from test_madb import fixture, response, serve_bundle
from test_madb_acquisition import assert_deep_frozen, serve_series
from test_madb_acquisition import sources as sources

from comictagger_jp_talker.acquisition import AcquisitionContext, AcquisitionTrace
from comictagger_jp_talker.acquisition import AcquisitionReason as Reason
from comictagger_jp_talker.acquisition import AcquisitionStage as Stage
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.linkage import (
    LinkageStatus,
    acquire_linked_record_evidence,
    link_ndl_record,
    link_ndl_record_for_series,
)
from comictagger_jp_talker.linked_acquisition import NDLInputSnapshot
from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_acquisition import MADBAcquisition, failure
from comictagger_jp_talker.sources.madb_models import MADBError, MADBSearchPage, MADBSearchResult, RDFTerm
from comictagger_jp_talker.sources.madb_queries import ID_NS

CASES = (
    "no_isbn",
    "empty",
    "exact",
    "strong",
    "ambiguous",
    "direct_winner",
    "two_direct",
    "unsafe",
    "exact_isbn_conflict",
    "truncated",
    "truncated_exact",
    "book_truncated",
    "series_missing",
    "series_truncated",
    "first_discovery_failure",
    "second_discovery_failure",
    "truncated_then_failure",
    "first_book_failure",
    "second_book_failure",
    "two_exact_then_failure",
    "book_id_mismatch",
    "book_uri_mismatch",
    "duplicate_discovery",
    "conflicting_discovery_uri",
)


def scenario(name):
    ndl = record(title="")
    first = bundle(urls=(URL,), names=(" Series ",))
    second = bundle("M2", names=("Other",), series_ids=("C2",))
    candidates = [first]
    if name == "no_isbn":
        ndl.isbns = ["bad"]
    elif name == "empty":
        candidates = []
    elif name in ("strong", "ambiguous", "truncated"):
        first = bundle(names=(" Series ",))
        candidates = [first, second] if name == "ambiguous" else [first]
    elif name == "direct_winner":
        candidates = [second, first]
    elif name in ("two_direct", "two_exact_then_failure"):
        candidates = [first, bundle("M2", urls=(URL,), names=("Other",), series_ids=("C2",))]
        if name == "two_exact_then_failure":
            candidates.append(bundle("M3"))
    elif name == "unsafe":
        candidates = [bundle(urls=(OTHER_URL,), names=(" Series ",))]
    elif name == "exact_isbn_conflict":
        candidates = [bundle(isbns=(OTHER_ISBN,), urls=(URL,), names=(" Series ",))]
    elif name == "book_truncated":
        candidates = [
            replace(first, book=replace(first.book, completeness="truncated"), completeness="truncated")
        ]
    elif name == "series_missing":
        candidates = [
            replace(first, series=(), warnings=("Synthetic missing Series",), completeness="partial")
        ]
    elif name == "series_truncated":
        candidates = [
            replace(
                first, series=(replace(first.series[0], completeness="truncated"),), completeness="partial"
            )
        ]
    elif name == "second_book_failure":
        candidates = [first, second]
    source = source_for(*candidates, truncated=name in ("truncated", "truncated_exact"))
    if name == "first_discovery_failure":
        source.search_by_isbn.side_effect = MADBError(
            "rate_limited", "synthetic search", status=429, retry_after="17"
        )
    elif name in (
        "second_discovery_failure",
        "truncated_then_failure",
        "duplicate_discovery",
        "conflicting_discovery_uri",
    ):
        ndl.isbns = [OTHER_ISBN, ISBN, "4-592-88071-4"]
        page = source.search_by_isbn.return_value
        if name == "conflicting_discovery_uri":
            source.search_by_isbn.side_effect = [
                MADBSearchPage((MADBSearchResult("M1", ID_NS + "M9", (), ()),)),
                page,
            ]
        elif name == "duplicate_discovery":
            source.search_by_isbn.side_effect = [page, page]
        else:
            source.search_by_isbn.side_effect = [
                replace(
                    page, truncated=name == "truncated_then_failure", warnings=("discovery observation",)
                ),
                MADBError("timeout", "synthetic later search"),
            ]
    elif name == "first_book_failure":
        source.get.side_effect = MADBError("http", "synthetic Book", status=503, retry_after="23")
    elif name == "second_book_failure":
        source.get.side_effect = [first, MADBError("not_found", "synthetic disappeared")]
    elif name == "two_exact_then_failure":
        source.get.side_effect = [*candidates[:2], MADBError("timeout", "synthetic third Book")]
    elif name == "book_id_mismatch":
        source.get.side_effect = [bundle("M9")]
    elif name == "book_uri_mismatch":
        source.get.side_effect = [replace(first, book=replace(first.book, uri=ID_NS + "M9"))]
    source.get_for_series_linkage.side_effect = source.get.side_effect
    return ndl, source


class TracedFake:
    """Explicit synthetic trace contract; never represents measured source evidence."""

    def __init__(self, source):
        self.source = source
        self.outcomes = []
        self.search_by_isbn = source.search_by_isbn
        self.get = source.get
        self.get_for_series_linkage = source.get_for_series_linkage

    def outcome(self, operation, key, kind, refresh):
        try:
            value, error = operation(key, refresh=refresh), None
        except MADBError as exc:
            value, error = None, failure(exc)
        state = State.UNAVAILABLE if error else State.COMPLETE
        if kind == "discovery" and value is not None and value.truncated:
            state = State.TRUNCATED
        if kind == "book" and value is not None:
            state = State(value.book.completeness)
        result = MADBAcquisition(
            value=value,
            error=error,
            context=AcquisitionContext(**{kind: state}),
            trace=AcquisitionTrace(
                run_id=f"synthetic-{len(self.outcomes)}",
                started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:01+00:00",
                events=(),
            ),
        )
        self.outcomes.append(result)
        return result

    def _search_by_isbn_with_trace(self, key, *, refresh=False):
        return self.outcome(self.search_by_isbn, key, "discovery", refresh)

    def _get_with_trace(self, key, *, refresh=False, series_only=False):
        return self.outcome(self.get_for_series_linkage if series_only else self.get, key, "book", refresh)


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("scope", ["full", "series_linkage"])
@pytest.mark.parametrize("traced", [False, True])
def test_public_result_matches_pre_migration_golden(name, scope, traced):
    expected = json.loads(
        (Path(__file__).parent / "fixtures/linkage_evidence_baseline.json").read_text(encoding="utf-8")
    )["cases"][name][scope]
    ndl, source = scenario(name)
    selected = TracedFake(source) if traced else source
    wrapper = link_ndl_record if scope == "full" else link_ndl_record_for_series
    result = wrapper(ndl, selected)
    assert json.loads(json.dumps(asdict(result))) == expected
    assert source.get.call_count + source.get_for_series_linkage.call_count <= len(result.candidates)


@pytest.mark.parametrize(
    "name,state,attempt_states",
    [
        ("no_isbn", State.NOT_REQUESTED, ()),
        ("empty", State.COMPLETE, (State.COMPLETE,)),
        ("exact", State.COMPLETE, (State.COMPLETE,)),
        ("duplicate_discovery", State.COMPLETE, (State.COMPLETE, State.COMPLETE)),
        ("first_discovery_failure", State.UNAVAILABLE, (State.UNAVAILABLE, State.NOT_REQUESTED)),
        ("second_discovery_failure", State.PARTIAL, (State.COMPLETE, State.UNAVAILABLE, State.NOT_REQUESTED)),
        ("truncated", State.TRUNCATED, (State.TRUNCATED,)),
        ("truncated_then_failure", State.PARTIAL, (State.TRUNCATED, State.UNAVAILABLE, State.NOT_REQUESTED)),
    ],
)
def test_discovery_plan_and_each_outcome(name, state, attempt_states):
    ndl, legacy = scenario(name)
    if name == "first_discovery_failure":
        ndl.isbns.append(OTHER_ISBN)
    elif name in ("second_discovery_failure", "truncated_then_failure"):
        ndl.isbns.append("9791090636071")
    source = TracedFake(legacy)
    result = acquire_linked_record_evidence(ndl, source)
    discovery = result.acquisition_context.discovery
    assert discovery.state == state
    assert tuple(item.state for item in discovery.attempts) == attempt_states
    assert discovery.planned_isbns == tuple(sorted(set(discovery.planned_isbns)))
    assert len(source.outcomes) == legacy.search_by_isbn.call_count + legacy.get_for_series_linkage.call_count
    if name == "no_isbn":
        assert discovery.reasons == ("no_valid_isbn",)
        assert not source.outcomes
    for attempt in discovery.attempts:
        if attempt.state == State.NOT_REQUESTED:
            assert attempt.page is attempt.acquisition is attempt.error is None
            assert attempt.reason == "upstream_failed"
        else:
            assert attempt.acquisition in source.outcomes
            assert attempt.page is attempt.acquisition.value
    if name in ("second_discovery_failure", "truncated_then_failure"):
        assert all(b.context.book == State.NOT_REQUESTED for b in result.acquisition_context.books)
        assert all(
            b.bundle is None and b.reason == "upstream_failed" for b in result.acquisition_context.books
        )
    if name == "truncated_then_failure":
        assert discovery.truncated and "discovery_truncated" in discovery.reasons
        assert "discovery_failed" in discovery.reasons


def test_union_order_refresh_context_and_snapshot_identity():
    first, second = bundle(), bundle("M2")
    legacy = source_for(first, second)
    legacy.get_for_series_linkage.side_effect = legacy.get.side_effect
    pages = [
        MADBSearchPage((MADBSearchResult("M2", second.book.uri, (), ()),)),
        MADBSearchPage(tuple(MADBSearchResult(b.book.id, b.book.uri, (), ()) for b in (second, first))),
    ]
    legacy.search_by_isbn.side_effect = pages
    source = TracedFake(legacy)
    result = acquire_linked_record_evidence(
        record(isbns=(OTHER_ISBN, ISBN, "4592880714")), source, refresh=True
    )
    assert legacy.search_by_isbn.call_args_list == [call(ISBN, refresh=True), call(OTHER_ISBN, refresh=True)]
    assert legacy.get_for_series_linkage.call_args_list == [
        call("M1", refresh=True),
        call("M2", refresh=True),
    ]
    assert result.bundles == (first, second)
    for item, value, outcome in zip(
        result.acquisition_context.books, (first, second), source.outcomes[2:], strict=True
    ):
        assert item.bundle is value is outcome.value
        assert item.acquisition is outcome
        assert item.context.discovery == State.COMPLETE
        assert item.acquisition.context.discovery == State.NOT_REQUESTED
    assert_deep_frozen(result)


@pytest.mark.parametrize("name", ["second_book_failure", "two_exact_then_failure"])
def test_interrupted_book_run_retains_success_and_never_fetches_remaining(name):
    ndl, legacy = scenario(name)
    page = legacy.search_by_isbn.return_value
    legacy.search_by_isbn.return_value = replace(
        page, records=(*page.records, MADBSearchResult("M9", ID_NS + "M9", (), ()))
    )
    result = acquire_linked_record_evidence(ndl, TracedFake(legacy))
    books = result.acquisition_context.books
    assert result.linkage.status == LinkageStatus.UNAVAILABLE
    assert result.bundles == tuple(b.bundle for b in books if b.included_in_linkage)
    assert books[-2].context.book == State.UNAVAILABLE and books[-2].error is not None
    assert books[-1].context.book == State.NOT_REQUESTED and books[-1].bundle is None
    assert books[-1].reason == "upstream_failed"
    assert result.linkage.matches[0].series is None
    assert legacy.get_for_series_linkage.call_count == len(books) - 1


@pytest.mark.parametrize("name", ["book_id_mismatch", "book_uri_mismatch", "conflicting_discovery_uri"])
def test_conflicts_are_retained_without_silently_changing_identity(name):
    ndl, legacy = scenario(name)
    result = acquire_linked_record_evidence(ndl, TracedFake(legacy))
    ctx = result.acquisition_context
    if name == "conflicting_discovery_uri":
        assert ctx.issues == ("conflicting_discovery_uri:M1",)
        assert ctx.discovery.attempts[0].page.records[0].uri == ID_NS + "M9"
        assert ctx.discovery.attempts[1].page.records[0].uri == ID_NS + "M1"
        assert result.linkage.status == LinkageStatus.MATCHED
        assert ctx.books[0].book_uri == ID_NS + "M1"
    else:
        assert ctx.issues == ("discovered_book_mismatch:M1",)
        assert not result.bundles
        item = ctx.books[0]
        assert item.bundle is item.acquisition.value  # Rejected raw snapshot remains observable.
        assert not item.included_in_linkage and item.error.kind == "schema"
        assert result.linkage.error.message == "Retrieved Book differs from discovered candidate"


def test_input_is_fixed_before_source_callbacks_and_raw_values_are_unchanged():
    ndl, legacy = scenario("exact")
    ndl.publishers = [" 出版社\u0001 "]
    ndl.editions = ["初版"]
    ndl.volumes = ["１"]
    ndl.issued = ["2020-01"]
    ndl.dates = ["令和二年"]
    ndl.series_titles = [" 叢書 "]
    before = NDLInputSnapshot.from_record(ndl)
    page = legacy.search_by_isbn.return_value
    expected, baseline = scenario("exact")
    expected = before.to_record()
    expected_result = link_ndl_record_for_series(expected, baseline)

    def search(*args, **kwargs):
        ndl.id = "changed"
        ndl.title = "changed"
        ndl.url = OTHER_URL
        for name in ("isbns", "publishers", "editions", "volumes", "issued", "dates", "series_titles"):
            getattr(ndl, name).clear()
        return page

    legacy.search_by_isbn.side_effect = search
    result = acquire_linked_record_evidence(ndl, TracedFake(legacy))
    assert result.linkage == expected_result
    assert result.acquisition_context.ndl_input == before
    assert before.publishers == (" 出版社\u0001 ",) and before.volumes == ("１",)
    private = before.to_record()
    private.publishers.clear()
    assert before.publishers
    with pytest.raises(FrozenInstanceError):
        before.id = "changed"
    with pytest.raises(ValueError):
        replace(before, isbns=[])


@pytest.mark.parametrize("phase", ["discovery", "book"])
@pytest.mark.parametrize(
    "exception", [ValueError, RuntimeError, OSError, sqlite3.DatabaseError, AssertionError]
)
@pytest.mark.parametrize("traced", [False, True])
def test_non_madb_exceptions_still_propagate(phase, exception, traced):
    ndl, legacy = scenario("exact")
    operation = legacy.search_by_isbn if phase == "discovery" else legacy.get_for_series_linkage
    operation.side_effect = exception("synthetic failure")
    with pytest.raises(exception, match="synthetic failure"):
        acquire_linked_record_evidence(ndl, TracedFake(legacy) if traced else legacy)


def test_legacy_adapter_never_attests_complete_or_retries():
    ndl, legacy = scenario("exact")
    result = acquire_linked_record_evidence(ndl, legacy)
    ctx = result.acquisition_context
    assert result.linkage.status == LinkageStatus.MATCHED
    assert ctx.discovery.state == ctx.books[0].context.book == State.PARTIAL
    assert ctx.traces == ctx.events == ()
    assert ctx.books[0].acquisition is None
    assert "discovery_trace_unavailable" in ctx.issues
    legacy.search_by_isbn.assert_called_once()
    legacy.get_for_series_linkage.assert_called_once()
    legacy._get_with_trace.assert_not_called()


@pytest.mark.parametrize("class_patch", [False, True])
def test_public_monkeypatch_is_respected_without_trace_probe(sources, monkeypatch, class_patch):
    source = sources()
    value = bundle()
    page = MADBSearchPage((MADBSearchResult("M1", ID_NS + "M1", (), ()),))
    target = madb.MADBSource if class_patch else source
    search, get = Mock(return_value=page), Mock(return_value=value)
    monkeypatch.setattr(target, "search_by_isbn", search)
    monkeypatch.setattr(target, "get_for_series_linkage", get)
    result = acquire_linked_record_evidence(record(), source)
    assert result.bundles[0] is value
    search.assert_called_once_with(ISBN, refresh=False)
    get.assert_called_once_with("M1", refresh=False)
    source.session.post.assert_not_called()


def serve_linkage(source, *, raw=None, search="single", fail_uri=None, transport=None):
    """Mock HTTP only. Sources and every fixture in this module are synthetic."""
    raw = serve_bundle(source) if raw is None else raw

    def post(url, **kwargs):
        query = kwargs["data"]["query"]
        key = "discovery" if query.startswith("PREFIX") else query.split("<", 1)[1].split(">", 1)[0]
        if key == fail_uri:
            if isinstance(transport, Exception):
                raise transport
            result = response(b"", status=transport)
            result.headers["Retry-After"] = "47"
            return result
        return response(fixture(search) if key == "discovery" else raw[key])

    source.session.post.side_effect = post
    return raw


@pytest.mark.parametrize("scope,requests_count", [("full", 6), ("series_linkage", 3)])
def test_actual_source_cold_warm_refresh_and_original_events(sources, scope, requests_count):
    source = sources()
    serve_linkage(source)
    cold = acquire_linked_record_evidence(record(), source, scope=scope)
    assert source.session.post.call_count == requests_count
    ctx = cold.acquisition_context
    assert ctx.discovery.state == ctx.books[0].context.book == State.COMPLETE
    assert len(ctx.traces) == 2
    assert ctx.run_id not in {trace.run_id for trace in ctx.traces}
    assert ctx.books[0].bundle is cold.bundles[0] is ctx.books[0].acquisition.value
    original_events = tuple(e for trace in ctx.traces for e in trace.events)
    assert all(a is b for a, b in zip(original_events, ctx.events, strict=True))
    for event in ctx.events:
        if event.stage == Stage.RELATION:
            parent = next(
                r for r in (cold.bundles[0].book, *cold.bundles[0].series) if r.uri == event.parent_uri
            )
            assert event.statement is parent.statements[event.statement_index]
    if scope == "series_linkage":
        assert ctx.books[0].context.agents == ctx.books[0].context.holdings == State.NOT_REQUESTED
    warm = acquire_linked_record_evidence(record(), source, scope=scope)
    assert warm.linkage == cold.linkage and warm.bundles == cold.bundles
    assert source.session.post.call_count == requests_count
    assert not any(e.stage == Stage.NETWORK for e in warm.acquisition_context.events)
    assert all(e.origin_fetched_at is None for e in warm.acquisition_context.events)
    refreshed = acquire_linked_record_evidence(record(), source, scope=scope, refresh=True)
    assert refreshed.linkage == cold.linkage
    assert source.session.post.call_count == 2 * requests_count
    assert_deep_frozen(cold)


@pytest.mark.parametrize("mode", ["partial_expiry", "invalid"])
def test_partial_cache_refreshes_only_affected_resource(sources, mode):
    source = sources()
    serve_linkage(source)
    writes = source.cache.add_search_results
    source.cache.add_search_results = Mock(wraps=writes)
    cold = acquire_linked_record_evidence(record(), source)
    namespace, key, entries, _ = source.cache.add_search_results.call_args.args
    if mode == "invalid":
        writes(namespace, key, [type(entries[0])(key, b"bad JSON")], True)
    else:
        original = source.cache.get_search_results
        source.cache.get_search_results = Mock(
            side_effect=lambda ns, k: [] if (ns, k) == (namespace, key) else original(ns, k)
        )
    renewed = acquire_linked_record_evidence(record(), source)
    assert renewed.linkage == cold.linkage
    assert source.session.post.call_count == 4
    events = renewed.acquisition_context.events
    network = [e for e in events if e.stage == Stage.NETWORK]
    assert len(network) == 1 and network[0].uri == ID_NS + "C1"
    assert sum(e.reason == Reason.CACHE_HIT for e in events) == 2
    if mode == "invalid":
        assert any(e.reason == Reason.CACHE_INVALID for e in events)


@pytest.mark.parametrize("scope", ["full", "series_linkage"])
@pytest.mark.parametrize("failure_at", [None, "discovery", ID_NS + "M1", ID_NS + "C1"])
def test_traced_and_original_public_source_calls_have_identical_io(sources, scope, failure_at):
    legacy, traced = sources(), sources()
    for source in (legacy, traced):
        serve_linkage(source, fail_uri=failure_at, transport=429)
        source.cache.add_search_results = Mock(wraps=source.cache.add_search_results)
    # Honor public overrides through the compatibility adapter. Wrapped native
    # methods execute the original untraced source path exactly once.
    legacy.search_by_isbn = Mock(wraps=legacy.search_by_isbn)
    legacy.get = Mock(wraps=legacy.get)
    legacy.get_for_series_linkage = Mock(wraps=legacy.get_for_series_linkage)
    for refresh in (False, False, True):
        old = acquire_linked_record_evidence(record(), legacy, scope=scope, refresh=refresh)
        new = acquire_linked_record_evidence(record(), traced, scope=scope, refresh=refresh)
        assert old.linkage == new.linkage and old.bundles == new.bundles
        assert legacy.session.post.call_args_list == traced.session.post.call_args_list
        assert (
            legacy.cache.add_search_results.call_args_list == traced.cache.add_search_results.call_args_list
        )


@pytest.mark.parametrize("phase", ["discovery", "book", "series"])
@pytest.mark.parametrize(
    "transport,kind",
    [
        (429, "rate_limited"),
        (503, "http"),
        (requests.Timeout(), "timeout"),
        (requests.ConnectionError(), "network"),
    ],
)
def test_transport_failure_preserves_source_facts_and_exception_boundary(sources, phase, transport, kind):
    source = sources()
    uri = {"discovery": "discovery", "book": ID_NS + "M1", "series": ID_NS + "C1"}[phase]
    serve_linkage(source, fail_uri=uri, transport=transport)
    result = acquire_linked_record_evidence(record(), source)
    events = result.acquisition_context.events
    failures = [e for e in events if e.stage == Stage.NETWORK and e.error]
    assert len(failures) == 1 and failures[0].error.kind == kind
    assert source.session.post.call_count == {"discovery": 1, "book": 2, "series": 3}[phase]
    if isinstance(transport, int):
        assert failures[0].status == transport and failures[0].retry_after == "47"
    if phase == "series":
        assert result.linkage.status != LinkageStatus.UNAVAILABLE
        assert result.bundles[0].completeness == "partial"
        assert result.acquisition_context.books[0].context.series == State.UNAVAILABLE
    else:
        assert result.linkage.status == LinkageStatus.UNAVAILABLE
        assert result.linkage.error.kind == kind
        assert not result.bundles


@pytest.mark.parametrize(
    "kind",
    ["empty", "book_truncated", "series_truncated", "budget", "invalid", "series_failure", "book_partial"],
)
def test_source_incompleteness_is_preserved_with_raw_relation_evidence(sources, monkeypatch, kind):
    source = sources()
    refs = (RDFTerm("uri", ID_NS + "C1"),)
    if kind == "budget":
        refs = tuple(RDFTerm("uri", ID_NS + f"C{i}") for i in range(1, 14))
    elif kind == "invalid":
        refs = (RDFTerm("literal", " C1 "), RDFTerm("bnode", "raw"), RDFTerm("uri", "https://bad.invalid/C1"))
    elif kind == "series_failure":
        refs = (*refs, RDFTerm("uri", ID_NS + "C2"))
    elif kind in ("book_truncated", "book_partial"):
        refs = ()
    raw = serve_series(source, refs)
    serve_linkage(
        source,
        raw=raw,
        search="empty" if kind == "empty" else "single",
        fail_uri=ID_NS + "C2" if kind == "series_failure" else None,
        transport=503,
    )
    if kind in ("book_truncated", "series_truncated"):
        source.maximum_triples = 2 if kind == "book_truncated" else 3
    elif kind == "book_partial":
        parser = madb.parse_resource
        monkeypatch.setattr(
            madb, "parse_resource", lambda *a, **kw: replace(parser(*a, **kw), completeness="partial")
        )
    result = acquire_linked_record_evidence(record(), source)
    ctx = result.acquisition_context
    if kind == "empty":
        assert ctx.discovery.state == State.COMPLETE and not ctx.books and not result.bundles
        assert source.session.post.call_count == 1
        return
    assert ctx.books[0].acquisition.value is result.bundles[0]
    assert ctx.books[0].context.discovery == State.COMPLETE
    original = ctx.books[0].acquisition.context
    assert replace(ctx.books[0].context, discovery=State.NOT_REQUESTED) == original
    if kind == "budget":
        assert any(e.reason == Reason.RELATION_BUDGET for e in ctx.events)
        assert len(result.bundles[0].series) == 12
    elif kind == "invalid":
        assert tuple(e.statement.object for e in ctx.events if e.stage == Stage.RELATION) == refs
        assert original.relations == State.PARTIAL
    elif kind == "series_failure":
        assert original.series == State.PARTIAL
        assert len(result.bundles[0].series) == 1
    elif kind == "book_partial":
        assert original.book == original.relations == State.PARTIAL
    elif kind == "book_truncated":
        assert original.book == State.TRUNCATED and original.relations == State.PARTIAL
    else:
        assert original.series == State.TRUNCATED
