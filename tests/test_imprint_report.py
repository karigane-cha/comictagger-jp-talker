"""R1 diagnostics: acquired fixtures only, never synthetic authority assertions."""

from __future__ import annotations

import builtins
import io
import json
import logging
import sqlite3
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from comicapi.comicarchive import ComicArchive
from comicapi.genericmetadata import GenericMetadata
from test_imprint_candidates import (
    MEASURED,
    acquired,
    evaluate,
    measured_bundle,
    measured_ndl,
    ndl_synthetic,
    synthetic,
)
from test_imprint_host_boundary import VALUES, cbz
from test_linkage import OTHER_ISBN, record, source_for
from test_linkage_evidence import CASES, TracedFake, scenario, serve_linkage
from test_madb_acquisition import assert_deep_frozen, serve_series
from test_madb_acquisition import sources as sources

from comictagger_jp_talker import imprint_candidates as evaluator
from comictagger_jp_talker import imprint_report as reports
from comictagger_jp_talker.acquisition import AcquisitionReason as Reason
from comictagger_jp_talker.acquisition import AcquisitionStage as Stage
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.imprint_candidates import ImprintEligibilityState as Decision
from comictagger_jp_talker.linkage import acquire_linked_record_evidence
from comictagger_jp_talker.sources import madb, ndl
from comictagger_jp_talker.sources.madb_models import MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_queries import ID_NS, SCHEMA_NS


def evidence_for(bundle=None, ndl_record=None, **context_changes):
    """Reuse synthetic RDF builders, explicitly attest a test-only context."""
    bundle = bundle if bundle is not None else synthetic()
    ndl_record = ndl_record if ndl_record is not None else ndl_synthetic()
    source = source_for(bundle)
    source.get_for_series_linkage.side_effect = source.get.side_effect
    result = acquire_linked_record_evidence(ndl_record, TracedFake(source))
    ledger = result.acquisition_context
    context = acquired(bundle, **context_changes)
    book = replace(
        ledger.books[0],
        context=context,
        acquisition=replace(
            ledger.books[0].acquisition, context=replace(context, discovery=State.NOT_REQUESTED)
        ),
    )
    return replace(result, acquisition_context=replace(ledger, books=(book,)))


def roundtrip(report):
    data = reports.report_to_json_data(report)
    encoded = json.dumps(data, ensure_ascii=True, allow_nan=False)
    assert json.loads(encoded) == data
    assert reports.report_to_json_data(report) == data
    # Independent dataclass traversal checks that the explicit schema loses no
    # field, enum, duplicate, raw value, event or source outcome.
    assert json.loads(json.dumps(asdict(report), ensure_ascii=True, allow_nan=False)) == data
    return data


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("traced", [False, True])
@pytest.mark.parametrize("scope", ["full", "series_linkage"])
def test_all_linkage_outcomes_keep_ledger_order_and_original_evaluator(name, traced, scope):
    original_ndl, source = scenario(name)
    evidence = acquire_linked_record_evidence(
        original_ndl, TracedFake(source) if traced else source, scope=scope
    )
    before = deepcopy((evidence, original_ndl))
    report = reports.describe_imprint_evidence(evidence)
    assert report == reports.describe_imprint_evidence(evidence)
    assert (evidence, original_ndl) == before
    assert report.linkage is evidence.linkage
    assert report.acquisition is evidence.acquisition_context
    assert len(report.books) == len(report.acquisition.books)
    assert_deep_frozen(report)
    data = roundtrip(report)
    assert data["acquisition"]["issues"] == list(evidence.acquisition_context.issues)
    for index, diagnostic in enumerate(report.books):
        book = evidence.acquisition_context.books[index]
        assert diagnostic.book_index == index
        if book.bundle is None:
            assert diagnostic.state == reports.BookEvaluationState.BUNDLE_UNAVAILABLE
            assert diagnostic.evaluation is diagnostic.excluded_classification is None
        elif not book.included_in_linkage:
            assert diagnostic.state == reports.BookEvaluationState.EXCLUDED
            assert diagnostic.evaluation is None
            assert diagnostic.excluded_classification.extraction.bundle is book.bundle
        else:
            assert diagnostic.evaluation == evaluate(
                book.bundle,
                ndl=evidence.acquisition_context.ndl_input.to_record(),
                context=book.context,
                linkage=evidence.linkage,
            )
            assert diagnostic.evaluation.state != Decision.ELIGIBLE


@pytest.mark.parametrize("identifier", sorted(MEASURED["expected_states"]))
def test_measured_rdf_is_never_promoted_to_authority(identifier):
    bundle = measured_bundle(identifier)
    original_ndl = measured_ndl(identifier) if identifier in MEASURED["ndl_records"] else ndl_synthetic()
    report = reports.describe_imprint_evidence(evidence_for(bundle, original_ndl))
    comparison = report.books[0].evaluation.comparison
    assert comparison.state.value == MEASURED["expected_states"][identifier]
    assert all(
        t.semantic_kind != evaluator.ImprintSemanticKind.VERIFIED_LABEL
        for t in comparison.classification.terms
    )
    assert report.books[0].evaluation.authority == ()
    assert report.authority_state == report.archive_state == "not_supplied"
    assert not any(
        (report.target_known, report.existing_value_assessed, report.apply_allowed, report.writes_performed)
    )
    roundtrip(report)


@pytest.mark.parametrize(
    "labels,series_labels,extra,comparison,decision,reason",
    [
        (("Label",), None, (), "book_only", "hold", "semantic_unverified"),
        ((), None, (), "none", "skip", "no_display"),
        (("Label", "Other"), None, (), "multiple", "hold", "multiple_displays"),
        (("Label",), ("Label",), (), "both_agree", "hold", "semantic_unverified"),
        ((), ("Label",), (), "series_only", "hold", "series_only_disabled"),
        (("Label",), ("Other",), (), "both_conflict", "reject", "series_conflict"),
        ((RDFTerm("literal", "ヨミ", language="ja-hrkt"),), None, (), "none", "skip", "no_display"),
        ((RDFTerm("uri", "https://example.invalid/label"),), None, (), "none", "hold", "unsupported_term"),
        ((RDFTerm("bnode", "label"),), None, (), "none", "hold", "unsupported_term"),
        (
            (RDFTerm("literal", "Label", datatype="urn:unknown"),),
            None,
            (),
            "none",
            "hold",
            "unsupported_term",
        ),
        (("Publisher",), None, (), "book_only", "hold", "publisher_equal"),
        (
            ("Edition",),
            None,
            ((SCHEMA_NS + "version", RDFTerm("literal", "Edition")),),
            "book_only",
            "reject",
            "edition_equal",
        ),
        (("Label / Other",), None, (), "book_only", "hold", "semantic_unverified"),
        (("Label", "Label Upper"), None, (), "multiple", "hold", "multiple_displays"),
        (("週刊架空雑誌",), None, (), "book_only", "hold", "semantic_unverified"),
        (("12345",), None, (), "book_only", "hold", "numeric_like"),
        (("A\x00B",), None, (), "book_only", "reject", "invalid_xml"),
    ],
)
def test_semantics_preserve_hold_reject_skip_and_never_infer_labels(
    labels, series_labels, extra, comparison, decision, reason
):
    evidence = evidence_for(synthetic(labels, series_labels=series_labels, extra=extra))
    report = reports.describe_imprint_evidence(evidence)
    result = report.books[0].evaluation
    assert result.comparison.state.value == comparison
    assert result.state.value == decision
    assert reason in [r.value for r in result.reasons]
    assert result.selected_candidate is None
    assert result == evaluate(evidence.bundles[0], context=evidence.acquisition_context.books[0].context)
    roundtrip(report)


@pytest.mark.parametrize(
    "case",
    [v for v in VALUES if v[1] is not None] + [("controls", "\x1b[31m\x00\x01\x0b\x1f\x85", None, None)],
)
def test_json_raw_unicode_whitespace_and_controls_are_lossless(case):
    raw = case[1]
    report = reports.describe_imprint_evidence(evidence_for(synthetic((raw,))))
    data = roundtrip(report)
    term = data["books"][0]["evaluation"]["comparison"]["classification"]["terms"][0]
    assert term["candidate"]["evidence"]["raw_value"]["value"] == raw
    assert term["candidate"]["statements"][0]["object"]["value"] == raw
    assert term["candidate"]["statement_indices"]
    assert term["candidate"]["label_indices"] == [0]
    assert term["candidate"]["evidence"]["predicate_or_path"] == SCHEMA_NS + "brand"
    assert data["schema_version"] == "imprint-report-v1"
    assert data["plugin_version"] == "0.4.0"
    assert data["identity_algorithm_version"] == "phase2b2-v1"
    assert data["evaluator_version"] == "phase2c2b-v1"
    assert data["books"][0]["evaluation"]["selected_candidate"] is None


@pytest.mark.parametrize("warm", [False, True])
def test_apis_are_pure_after_import_and_do_not_touch_metadata_or_archives(
    sources, tmp_path, monkeypatch, capsys, caplog, warm
):
    source = sources()
    serve_linkage(source)
    original_ndl = record()
    evidence = acquire_linked_record_evidence(original_ndl, source)
    if warm:
        evidence = acquire_linked_record_evidence(original_ndl, source)
    original_ndl.isbns.append(OTHER_ISBN)  # A later caller edit must not change the run snapshot.
    metadata = GenericMetadata(imprint=" 既存値 ", notes="Notes\r\n", description="description")
    archive = cbz(tmp_path)
    history = tmp_path / "latest-error.txt"
    history.write_bytes(b"previous error\r\n")
    bytes_before = archive.read_bytes(), history.read_bytes()
    before = deepcopy((original_ndl, evidence, metadata))
    forbidden = Mock(side_effect=AssertionError("Report API attempted a side effect"))
    with monkeypatch.context() as patch:
        for cls, method in (
            (madb.MADBSource, "__init__"),
            (ndl.NDLSource, "__init__"),
            (requests.Session, "__init__"),
            (requests.Session, "request"),
            (requests.Session, "get"),
            (requests.Session, "post"),
            (GenericMetadata, "__init__"),
            (GenericMetadata, "__setattr__"),
            (ComicArchive, "__init__"),
            (ComicArchive, "write_tags"),
            (Path, "open"),
            (Path, "stat"),
            (logging.Logger, "_log"),
        ):
            patch.setattr(cls, method, forbidden)
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(sqlite3, "connect", forbidden)
        patch.setattr(source.session, "post", forbidden)
        patch.setattr(type(source.cache), "get_search_results", forbidden)
        patch.setattr(type(source.cache), "add_search_results", forbidden)
        patch.setattr("comictagger_jp_talker.linkage.utc_now", forbidden)
        patch.setattr("comictagger_jp_talker.sources.madb_acquisition.utc_now", forbidden)
        first = reports.describe_imprint_evidence(evidence)
        assert first == reports.describe_imprint_evidence(evidence)
        roundtrip(first)
    forbidden.assert_not_called()
    assert (original_ndl, evidence, metadata) == before
    assert (archive.read_bytes(), history.read_bytes()) == bytes_before
    assert capsys.readouterr() == ("", "") and not caplog.records
    assert first.acquisition.ndl_input.isbns != tuple(original_ndl.isbns)
    with pytest.raises(FrozenInstanceError):
        first.apply_allowed = True


@pytest.mark.parametrize("scope", ["series_linkage", "full"])
@pytest.mark.parametrize("warm", [False, True])
def test_real_source_events_cache_times_hashes_and_scopes_remain_distinct(sources, scope, warm):
    source = sources()
    serve_linkage(source)
    evidence = acquire_linked_record_evidence(record(), source, scope=scope)
    if warm:
        evidence = acquire_linked_record_evidence(record(), source, scope=scope)
    count = source.session.post.call_count
    report = reports.describe_imprint_evidence(evidence)
    data = roundtrip(report)
    assert source.session.post.call_count == count
    assert report.acquisition.events == evidence.acquisition_context.events
    assert [event for trace in data["acquisition"]["traces"] for event in trace["events"]] == [
        json.loads(json.dumps(asdict(event))) for event in evidence.acquisition_context.events
    ]
    assert report.snapshot_simultaneity == "unknown" and report.parsed_snapshot_digest is None
    assert all(b.context.acquired_at is None for b in report.acquisition.books)
    if warm:
        assert all(e.origin_fetched_at is None for e in report.acquisition.events)
        assert any(e.reason == Reason.CACHE_HIT and e.response_sha256 for e in report.acquisition.events)
        assert not any(e.stage == Stage.NETWORK for e in report.acquisition.events)
    else:
        assert any(e.origin_fetched_at and e.response_sha256 for e in report.acquisition.events)
    if scope == "series_linkage":
        assert report.acquisition.books[0].context.agents == State.NOT_REQUESTED
        assert report.acquisition.books[0].context.holdings == State.NOT_REQUESTED


@pytest.mark.parametrize(
    "mode", ["zero", "budget", "series_failure", "book_failure", "row", "byte", "partial_zero", "no_relation"]
)
def test_real_source_incompleteness_and_zero_are_not_fabricated(sources, monkeypatch, mode):
    source = sources()
    refs = tuple(RDFTerm("uri", ID_NS + f"C{i}") for i in range(1, 14 if mode == "budget" else 3))
    if mode == "no_relation":
        refs = ()
    raw = serve_series(source, refs)
    serve_linkage(
        source,
        raw=raw,
        search="empty" if mode in ("zero", "partial_zero") else "single",
        fail_uri={"series_failure": ID_NS + "C2", "book_failure": ID_NS + "M1"}.get(mode),
        transport=503,
    )
    if mode == "row":
        source.maximum_triples = 2
    elif mode == "byte":
        monkeypatch.setattr(madb, "MAX_RESPONSE_BYTES", 1)
    elif mode == "partial_zero":
        original = source._search_by_isbn_with_trace

        def partial(*args, **kwargs):
            outcome = original(*args, **kwargs)
            return replace(outcome, context=replace(outcome.context, discovery=State.PARTIAL))

        monkeypatch.setattr(source, "_search_by_isbn_with_trace", partial)
    evidence = acquire_linked_record_evidence(record(), source)
    report = reports.describe_imprint_evidence(evidence)
    roundtrip(report)
    ctx = report.acquisition
    if mode == "zero":
        assert ctx.discovery.state == State.COMPLETE and not report.books
    elif mode == "partial_zero":
        assert ctx.discovery.state == State.PARTIAL and not report.books
    elif mode == "budget":
        assert any(e.reason == Reason.RELATION_BUDGET and e.state == State.NOT_REQUESTED for e in ctx.events)
    elif mode == "series_failure":
        assert ctx.books[0].context.series == State.PARTIAL
        assert any(e.error and e.error.status == 503 for e in ctx.events)
    elif mode == "book_failure":
        assert ctx.books[0].bundle is None and ctx.books[0].context.book == State.UNAVAILABLE
        assert report.books[0].evaluation is None
    elif mode == "row":
        assert any(e.reason == Reason.ROW_LIMIT for e in ctx.events)
    elif mode == "byte":
        assert any(e.reason == Reason.BYTE_LIMIT for e in ctx.events)
    else:
        assert ctx.books[0].context.series == ctx.books[0].context.relations == State.NOT_RELATED


def test_duplicate_ledger_entries_and_large_evidence_are_not_deduplicated_or_truncated():
    # Assemble an already-parsed snapshot: the existing fixture parser has a
    # 300-row cap, which this report test must not change or pretend to bypass.
    bundle = synthetic(())
    labels = tuple(RDFTerm("literal", f" 候補 {i} 📚 ") for i in range(500))
    bundle = replace(
        bundle,
        book=replace(
            bundle.book,
            labels=labels,
            statements=(
                *bundle.book.statements,
                *(MADBStatement(bundle.book.uri, SCHEMA_NS + "brand", term) for term in labels),
            ),
        ),
    )
    evidence = evidence_for(bundle)
    ledger = evidence.acquisition_context
    book = ledger.books[0]
    # Distinct ledger occurrences, even with identical IDs and URIs.
    evidence = replace(
        evidence,
        bundles=evidence.bundles * 2,
        acquisition_context=replace(
            ledger,
            books=(book, book),
            traces=(*ledger.traces, book.acquisition.trace),
            issues=("synthetic_duplicate", "synthetic_duplicate"),
        ),
    )
    report = reports.describe_imprint_evidence(evidence)
    data = roundtrip(report)
    assert len(data["books"]) == 2
    assert data["acquisition"]["issues"] == ["synthetic_duplicate", "synthetic_duplicate"]
    for diagnostic in data["books"]:
        assert len(diagnostic["evaluation"]["comparison"]["classification"]["terms"]) == 500


@pytest.mark.parametrize("bad", [object(), [], {}, float("nan"), float("inf"), b"value", 1.2])
def test_unknown_types_and_nonfinite_values_are_rejected(bad):
    report = reports.describe_imprint_evidence(evidence_for())
    with pytest.raises(TypeError):
        reports.report_to_json_data(replace(report, plugin_version=bad))
    with pytest.raises(TypeError):
        reports.describe_imprint_evidence(bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("apply_allowed", True),
        ("writes_performed", True),
        ("target_known", True),
        ("schema_version", "imprint-report-v2"),
        ("authority_state", "verified"),
        ("archive_state", "missing"),
    ],
)
def test_serialization_rejects_false_save_authority_and_schema_claims(field, value):
    report = reports.describe_imprint_evidence(evidence_for())
    with pytest.raises(TypeError):
        reports.report_to_json_data(replace(report, **{field: value}))


@pytest.mark.parametrize("timestamp", ["unknown", "2026-10-23T12:00:00", "2026-10-23"])
def test_invalid_or_naive_timestamp_is_a_contract_error(timestamp):
    evidence = evidence_for()
    evidence = replace(
        evidence, acquisition_context=replace(evidence.acquisition_context, started_at=timestamp)
    )
    with pytest.raises(ValueError):
        reports.describe_imprint_evidence(evidence)


def test_timestamp_offset_and_missing_values_are_kept():
    evidence = evidence_for()
    ledger = replace(
        evidence.acquisition_context,
        started_at="2026-10-23T12:00:00.123+09:00",
        finished_at="2026-10-23T03:00:01Z",
    )
    data = roundtrip(reports.describe_imprint_evidence(replace(evidence, acquisition_context=ledger)))
    assert data["acquisition"]["started_at"] == ledger.started_at
    assert data["acquisition"]["finished_at"] == ledger.finished_at
    assert data["acquisition"]["books"][0]["context"]["acquired_at"] is None


@pytest.mark.parametrize("broken", ["bundles", "trace", "discovery_context", "source_value"])
def test_structural_inconsistency_is_not_hidden_as_hold(broken):
    evidence = evidence_for()
    ledger = evidence.acquisition_context
    if broken == "bundles":
        evidence = replace(evidence, bundles=())
    elif broken == "trace":
        evidence = replace(evidence, acquisition_context=replace(ledger, traces=()))
    else:
        book = ledger.books[0]
        book = (
            replace(book, context=replace(book.context, discovery=State.PARTIAL))
            if broken == "discovery_context"
            else replace(book, acquisition=replace(book.acquisition, value=synthetic(("Different",))))
        )
        evidence = replace(evidence, acquisition_context=replace(ledger, books=(book,)))
    with pytest.raises(ValueError):
        reports.describe_imprint_evidence(evidence)


def test_excluded_candidate_is_not_compared_or_evaluated(monkeypatch):
    original_ndl, source = scenario("book_id_mismatch")
    evidence = acquire_linked_record_evidence(original_ndl, source)
    forbidden = Mock(side_effect=AssertionError("Excluded candidate evaluated"))
    monkeypatch.setattr(evaluator, "compare_imprint_candidates", forbidden)
    monkeypatch.setattr(evaluator, "evaluate_imprint_eligibility", forbidden)
    report = reports.describe_imprint_evidence(evidence)
    assert report.books[0].excluded_classification is not None
    assert report.acquisition.books[0].bundle.book.id == "M9"
    assert report.acquisition.books[0].book_id == "M1"
    forbidden.assert_not_called()


def test_unexpected_evaluator_failure_is_propagated(monkeypatch):
    evidence = evidence_for()
    monkeypatch.setattr(
        evaluator, "evaluate_imprint_eligibility", Mock(side_effect=RuntimeError("program bug"))
    )
    with pytest.raises(RuntimeError, match="program bug"):
        reports.describe_imprint_evidence(evidence)


def test_many_duplicate_events_are_kept_in_source_order(sources):
    source = sources()
    serve_linkage(source)
    evidence = acquire_linked_record_evidence(record(), source)
    ledger = evidence.acquisition_context
    attempt = ledger.discovery.attempts[0]
    trace = replace(attempt.acquisition.trace, events=attempt.acquisition.trace.events * 500)
    attempt = replace(attempt, acquisition=replace(attempt.acquisition, trace=trace))
    ledger = replace(
        ledger, discovery=replace(ledger.discovery, attempts=(attempt,)), traces=(trace, *ledger.traces[1:])
    )
    data = roundtrip(reports.describe_imprint_evidence(replace(evidence, acquisition_context=ledger)))
    assert len(data["acquisition"]["traces"][0]["events"]) == len(trace.events) >= 1000


def test_json_result_is_fresh_and_report_ledger_alignment_is_checked():
    report = reports.describe_imprint_evidence(evidence_for())
    data = roundtrip(report)
    data["acquisition"]["ndl_input"]["isbns"].append("not an ISBN")
    assert data != reports.report_to_json_data(report)
    for broken in (
        replace(report, books=()),
        replace(report, books=(replace(report.books[0], book_index=1),)),
        replace(report, books=(replace(report.books[0], evaluation=None),)),
    ):
        with pytest.raises(ValueError):
            reports.report_to_json_data(broken)


def test_unmatched_acquired_book_keeps_raw_candidates():
    evidence = evidence_for(synthetic(urls=(), isbns=()))
    report = reports.describe_imprint_evidence(evidence)
    assert report.linkage.status.value == "unmatched"
    assert report.books[0].evaluation.comparison.book_values == ("Label",)
    assert evaluator.ImprintEligibilityReason.NOT_MATCHED in report.books[0].evaluation.reasons
    roundtrip(report)
