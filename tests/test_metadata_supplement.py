"""Synthetic stage C integration; fixed outputs captured before moving the entry."""

import contextlib
import json
import logging
import sqlite3
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from comicapi.genericmetadata import GenericMetadata
from test_linkage import ISBN, OTHER_ISBN, bundle, record, source_for
from test_linkage_evidence import CASES, scenario, serve_linkage
from test_madb import fixture, response
from test_summary import ID
from test_summary import details as details
from test_summary import no_abstract as no_abstract
from test_summary_policy import response as ndl_response

from comictagger_jp_talker import metadata_supplement, series_supplement
from comictagger_jp_talker import talker as talker_module
from comictagger_jp_talker.linkage import acquire_linked_record_evidence
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import SearchPage
from comictagger_jp_talker.sources import madb, ndl
from comictagger_jp_talker.sources.madb_models import MADBError, RDFTerm
from comictagger_jp_talker.sources.madb_queries import ID_NS, PROPERTY_NS, SCHEMA_NS
from comictagger_jp_talker.sources.ndl_summary import DETAIL_ENDPOINT

OUTPUT_CASES = (*CASES, "raw_display", "reading_only", "multiple_display", "multiple_series", "xml_invalid")


def output_case(name):
    if name in CASES:
        ndl, source = scenario(name)
    else:
        ndl = record(title="")
        names, identifiers = ("作品名",), ("C1",)
        if name == "raw_display":
            names = (" 髙﨑𠮷は\u3099? ",)
        elif name == "reading_only":
            names = (RDFTerm("literal", "ヨミ", language="ja-hrkt"),)
        elif name == "multiple_display":
            names = ("作品名", "別作品")
        elif name == "multiple_series":
            identifiers = ("C1", "C2")
        elif name == "xml_invalid":
            names = ("作品\x00名",)
        source = source_for(bundle(names=names, series_ids=identifiers))
        source.get_for_series_linkage.side_effect = source.get.side_effect
    metadata = replace(
        to_metadata(ndl),
        notes="既存 Notes\r\n原文末尾 ",
        imprint=" 既存 Imprint ",
        publisher="NDL publisher",
        description="NDL summary",
        tags={"tag"},
        genres={"genre"},
    )
    source.__enter__ = lambda self: self

    def exit_source(self, *args):
        self.close()

    source.__exit__ = exit_source
    return ndl, source, metadata


def json_metadata(metadata):
    return json.loads(json.dumps(asdict(metadata), default=sorted))


def invoke(entry, metadata, ndl, path, *, enabled=True, talker=None, monkeypatch=None):
    if entry == "legacy":
        return series_supplement.supplement_series(metadata, ndl, path, enabled=enabled)
    if entry == "talker":
        talker.madb_series_supplement = enabled
        talker._source = Mock()
        talker.source.get.return_value = ndl
        monkeypatch.setattr(talker_module, "to_metadata", Mock(return_value=metadata))
        return talker.fetch_comic_data(issue_id=ndl.id)
    return metadata_supplement.supplement_metadata(metadata, ndl, path, series_enabled=enabled)


@pytest.mark.parametrize("entry", ["common", "legacy", "talker"])
@pytest.mark.parametrize("name", OUTPUT_CASES)
def test_complete_metadata_and_logs_match_pre_migration_fixture(
    name, entry, tmp_path, talker, monkeypatch, caplog
):
    expected = json.loads(
        (Path(__file__).parent / "fixtures/metadata_supplement_baseline.json").read_text(encoding="utf-8")
    )["cases"][name]
    ndl, source, metadata = output_case(name)
    original = deepcopy((ndl, metadata))
    factory = Mock(return_value=source)
    monkeypatch.setattr(metadata_supplement, "MADBSource", factory)
    core = Mock(wraps=acquire_linked_record_evidence)
    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", core)
    caplog.set_level(logging.WARNING)
    output = invoke(entry, metadata, ndl, tmp_path, talker=talker, monkeypatch=monkeypatch)
    assert json_metadata(output) == expected["metadata"]
    assert [[r.name, r.levelname, r.getMessage()] for r in caplog.records] == expected["logs"]
    assert (ndl, metadata) == original
    assert {k for k, v in asdict(metadata).items() if asdict(output)[k] != v} <= {"series", "notes"}
    assert output.notes.startswith(metadata.notes)
    factory.assert_called_once_with(tmp_path)
    core.assert_called_once_with(ndl, source, scope="series_linkage")
    source.close.assert_called_once()
    source.get.assert_not_called()


@pytest.mark.parametrize("entry", ["common", "legacy", "talker"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("series", [None, "", " \t\n\u3000", "既存 Series"])
def test_need_gate_precedes_all_source_and_core_creation(
    entry, enabled, series, talker, tmp_path, monkeypatch
):
    ndl = record(title="")
    metadata = GenericMetadata(series=series, notes="既存", imprint=" ")
    factory = Mock(side_effect=AssertionError("No source"))
    core = Mock(side_effect=AssertionError("No acquisition"))
    monkeypatch.setattr(metadata_supplement, "MADBSource", factory)
    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", core)
    need = enabled and not (series or "").strip()
    if need:
        with pytest.raises(AssertionError, match="No source"):
            invoke(entry, metadata, ndl, tmp_path, enabled=enabled, talker=talker, monkeypatch=monkeypatch)
        factory.assert_called_once()
    else:
        assert (
            invoke(entry, metadata, ndl, tmp_path, enabled=enabled, talker=talker, monkeypatch=monkeypatch)
            is metadata
        )
        factory.assert_not_called()
    core.assert_not_called()


def test_apply_runs_after_close_with_the_exact_acquired_linkage(tmp_path, monkeypatch):
    ndl, source, metadata = output_case("exact")
    evidence = acquire_linked_record_evidence(ndl, source)
    events = []
    source.close.side_effect = lambda: events.append("close")
    monkeypatch.setattr(metadata_supplement, "MADBSource", Mock(return_value=source))

    def acquire(*args, **kwargs):
        events.append("acquire")
        return evidence

    def apply(value, linkage):
        assert value is metadata and linkage is evidence.linkage
        assert events == ["acquire", "close"]
        events.append("apply")
        return series_supplement.apply_series_supplement(value, linkage)

    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", acquire)
    monkeypatch.setattr(metadata_supplement, "apply_series_supplement", apply)
    bundles, context = evidence.bundles, evidence.acquisition_context
    output = metadata_supplement.supplement_metadata(metadata, ndl, tmp_path, series_enabled=True)
    assert output.series == " Series "
    assert events == ["acquire", "close", "apply"]
    assert evidence.bundles is bundles and evidence.acquisition_context is context
    source.close.assert_called_once()


@pytest.mark.parametrize("phase", ["constructor", "acquire", "close"])
@pytest.mark.parametrize("kind", ["madb", "os", "sqlite"])
def test_expected_failures_keep_ndl_history_and_close_once(phase, kind, talker, monkeypatch, caplog):
    ndl, source, metadata = output_case("exact")
    history = talker.cache_folder / "jpbooks/latest-error.txt"
    history.parent.mkdir(parents=True, exist_ok=True)
    raw_history = b"NDL failure\r\n\x00existing raw history\n"
    history.write_bytes(raw_history)
    errors = {
        "madb": MADBError("timeout", "synthetic failure"),
        "os": OSError("synthetic failure"),
        "sqlite": sqlite3.OperationalError("synthetic failure"),
    }
    factory = Mock(return_value=source)
    core = Mock(wraps=acquire_linked_record_evidence)
    apply = Mock(side_effect=AssertionError("No apply before successful close"))
    if phase == "constructor":
        factory.side_effect = errors[kind]
    elif phase == "acquire":
        core.side_effect = errors[kind]
    else:
        source.close.side_effect = errors[kind]
    monkeypatch.setattr(metadata_supplement, "MADBSource", factory)
    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", core)
    monkeypatch.setattr(metadata_supplement, "apply_series_supplement", apply)
    assert (
        invoke("talker", metadata, ndl, talker.cache_folder, talker=talker, monkeypatch=monkeypatch)
        is metadata
    )
    assert history.read_bytes() == raw_history
    factory.assert_called_once()
    assert source.close.call_count == (0 if phase == "constructor" else 1)
    assert core.call_count == (0 if phase == "constructor" else 1)
    apply.assert_not_called()
    assert len(caplog.records) == 1
    assert caplog.records[0].name == "comictagger_jp_talker.series_supplement"
    assert "retaining NDL metadata" in caplog.records[0].getMessage()


@pytest.mark.parametrize("exception", [TypeError, ValueError, AssertionError, RuntimeError])
@pytest.mark.parametrize("phase", ["constructor", "acquire", "close"])
def test_unexpected_exceptions_propagate_and_never_apply(exception, phase, tmp_path, monkeypatch):
    ndl, source, metadata = output_case("exact")
    factory = Mock(return_value=source)
    core = Mock(wraps=acquire_linked_record_evidence)
    apply = Mock(side_effect=AssertionError("No apply"))
    failing = {"constructor": factory, "acquire": core, "close": source.close}[phase]
    failing.side_effect = exception("internal failure")
    monkeypatch.setattr(metadata_supplement, "MADBSource", factory)
    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", core)
    monkeypatch.setattr(metadata_supplement, "apply_series_supplement", apply)
    with pytest.raises(exception, match="internal failure"):
        metadata_supplement.supplement_metadata(metadata, ndl, tmp_path, series_enabled=True)
    assert source.close.call_count == (0 if phase == "constructor" else 1)
    apply.assert_not_called()


def test_notes_are_identical_when_series_is_cleared_and_reapplied(tmp_path, monkeypatch):
    ndl, source, metadata = output_case("raw_display")
    monkeypatch.setattr(metadata_supplement, "MADBSource", Mock(return_value=source))
    first = metadata_supplement.supplement_metadata(metadata, ndl, tmp_path, series_enabled=True)
    second = series_supplement.supplement_series(replace(first, series=""), ndl, tmp_path, enabled=True)
    assert second == first
    assert first.series == " 髙﨑𠮷は\u3099? "
    assert first.notes.startswith("既存 Notes\r\n原文末尾 ")
    assert second.imprint == " 既存 Imprint "


def test_candidates_and_status_never_enter_supplement(talker, monkeypatch):
    ndl = replace(record(title=""), volumes=["1"])
    talker.madb_series_supplement = True
    talker._source = Mock()
    talker.source.get.return_value = ndl
    talker.source.search.return_value = SearchPage([ndl], 1)
    blocked = Mock(side_effect=AssertionError("Candidate/status path"))
    monkeypatch.setattr(talker_module, "supplement_metadata", blocked)
    status_source = Mock()
    monkeypatch.setattr(talker_module, "NDLSource", Mock(return_value=status_source))
    assert talker.search_for_series("作品", refresh_cache=True)
    assert talker.search_metadata(GenericMetadata(series="作品"))
    assert talker.fetch_series(ndl.id)
    assert talker.fetch_issues_in_series(ndl.id)
    assert talker.fetch_issues_by_series_issue_num_and_year([ndl.id], "1", None)
    assert talker.check_status({"jpbooks_madb_series_supplement": True})[1]
    assert all(c.kwargs["summary_mode"] == "cache" for c in talker.source.get.call_args_list)
    status_source.session.close.assert_called_once()
    status_source.cache.close.assert_called_once()
    blocked.assert_not_called()


@pytest.mark.parametrize("case", ["fetch_failure", "requested_mismatch", "record_conflict", "no_id"])
def test_ndl_errors_stop_before_common_entry(case, talker, monkeypatch):
    from comictalker.comictalker import TalkerDataError

    ndl = replace(record(title=""), volumes=["1"])
    if case == "record_conflict":
        ndl.title = "作品 2"
    talker.madb_series_supplement = True
    talker._source = Mock()
    talker.source.get.return_value = ndl
    if case == "fetch_failure":
        talker.source.get.side_effect = TalkerDataError("NDL", 3, "synthetic failure")
    blocked = Mock(side_effect=AssertionError("Must finish NDL checks"))
    monkeypatch.setattr(talker_module, "supplement_metadata", blocked)
    with pytest.raises(TalkerDataError):
        talker.fetch_comic_data(issue_id=None if case == "no_id" else ndl.id, issue_number="2")
    blocked.assert_not_called()
    if case != "no_id":
        talker.source.get.assert_called_once_with(ndl.id, summary_mode="fetch", on_rate_limit=None)


@pytest.mark.parametrize(
    "order", [("metadata_supplement", "series_supplement"), ("series_supplement", "metadata_supplement")]
)
def test_import_orders_are_acyclic_and_have_no_network(order, tmp_path):
    code = """
import importlib
from unittest.mock import patch
import requests
with patch.object(requests.Session, "__init__", side_effect=AssertionError("No session at import")):
    for name in NAMES:
        importlib.import_module("comictagger_jp_talker." + name)
    from comictagger_jp_talker.series_supplement import apply_series_supplement as old
    from comictagger_jp_talker.series_supplement_policy import apply_series_supplement as policy
    assert old is policy
"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code.replace("NAMES", repr(order))],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def tracked_sources(monkeypatch):
    """Real source/cache with synthetic HTTP and observed close calls."""
    opened, options = [], {}
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())

    def create(path):
        source = madb.MADBSource(path)
        source.session.post = Mock()
        raw = serve_linkage(source, fail_uri=options.get("fail_uri"), transport=options.get("transport"))
        book = json.loads(raw[ID_NS + "M1"])
        book["results"]["bindings"] = [
            row for row in book["results"]["bindings"] if row["p"]["value"] != PROPERTY_NS + "dataUrl"
        ]  # Synthetic STRONG match, independent of the NDL test ID.
        raw[ID_NS + "M1"] = json.dumps(book).encode()
        source.close = Mock(wraps=source.close)
        source.session.close = Mock(wraps=source.session.close)
        source.cache.close = Mock(wraps=source.cache.close)
        source.cache.add_search_results = Mock(wraps=source.cache.add_search_results)
        if "configure" in options:
            options["configure"](source, raw)
        opened.append(source)
        return source

    factory = Mock(side_effect=create)
    monkeypatch.setattr(metadata_supplement, "MADBSource", factory)
    return opened, options, factory


def setup_final_talker(talker):
    item = replace(record(title=""), volumes=["1"])
    talker._source = Mock()
    talker.source.get.return_value = item
    talker.source.search.return_value = SearchPage([item], 1)
    talker.madb_series_supplement = True
    return item


def assert_closed_once(source):
    source.close.assert_called_once()
    source.session.close.assert_called_once()
    source.cache.close.assert_called_once()
    assert source._closed


def test_talker_shared_cold_warm_and_explicit_internal_refresh(talker, tracked_sources, monkeypatch):
    opened, options, factory = tracked_sources
    item = setup_final_talker(talker)
    core = Mock(wraps=acquire_linked_record_evidence)
    monkeypatch.setattr(metadata_supplement, "acquire_linked_record_evidence", core)
    baseline = to_metadata(item, existing_issue="1")
    first = talker.fetch_comic_data(issue_id=item.id, issue_number="1")
    assert first.series == "Series"
    assert {k for k, v in asdict(baseline).items() if asdict(first)[k] != v} == {"series", "notes"}
    core.assert_called_once_with(item, opened[0], scope="series_linkage")
    assert factory.call_count == 1 and opened[0].session.post.call_count == 3
    queries = [c.kwargs["data"]["query"] for c in opened[0].session.post.call_args_list]
    assert "SELECT DISTINCT" in queries[0] and "/M1>" in queries[1] and "/C1>" in queries[2]
    assert not any("/C2>" in q or "/C3>" in q or "/ref/" in q for q in queries)
    # Search refresh affects NDL only and must not make the next MADB fetch refresh.
    talker.search_for_series(ISBN, refresh_cache=True)
    assert talker.fetch_comic_data(issue_id=item.id, issue_number="1") == first
    assert factory.call_count == core.call_count == 2
    assert opened[1].session.post.call_count == 0
    assert core.call_args.kwargs == {"scope": "series_linkage"}
    assert all(c.kwargs["summary_mode"] == "fetch" for c in talker.source.get.call_args_list)
    assert talker.source.search.call_args.kwargs["refresh"] is True
    # The existing internal refresh contract remains explicit, outside the host API.
    with factory(talker.cache_folder) as source:
        refreshed = acquire_linked_record_evidence(item, source, refresh=True, scope="series_linkage")
    assert source.session.post.call_count == 3
    assert series_supplement.apply_series_supplement(baseline, refreshed.linkage) == first
    for source in opened:
        assert_closed_once(source)


@pytest.mark.parametrize("mode", ["expired", "invalid"])
def test_talker_partial_cache_renews_only_series(talker, tracked_sources, mode):
    opened, options, factory = tracked_sources
    item = setup_final_talker(talker)
    first = talker.fetch_comic_data(issue_id=item.id)
    namespace, key, entries, _ = opened[0].cache.add_search_results.call_args.args

    def configure(source, raw):
        if mode == "expired":
            read = source.cache.get_search_results
            source.cache.get_search_results = Mock(
                side_effect=lambda ns, k: [] if (ns, k) == (namespace, key) else read(ns, k)
            )
        else:
            source.cache.add_search_results(namespace, key, [type(entries[0])(key, b"bad JSON")], True)

    options["configure"] = configure
    assert talker.fetch_comic_data(issue_id=item.id) == first
    assert len(opened) == 2 and opened[0].session.post.call_count == 3
    assert opened[1].session.post.call_count == 1
    assert "/C1>" in opened[1].session.post.call_args.kwargs["data"]["query"]
    for source in opened:
        assert_closed_once(source)


@pytest.mark.parametrize(
    "case,count", [("no_series", 2), ("multiple_isbn", 4), ("multiple_book", 5), ("truncated", 3)]
)
def test_talker_other_acquisition_shapes(talker, tracked_sources, case, count):
    opened, options, factory = tracked_sources
    item = setup_final_talker(talker)
    if case == "multiple_isbn":
        item.isbns = [OTHER_ISBN, ISBN, "4592880714"]

    def configure(source, raw):
        if case == "no_series":
            body = json.loads(raw[ID_NS + "M1"])
            body["results"]["bindings"] = [
                row for row in body["results"]["bindings"] if row["p"]["value"] != SCHEMA_NS + "isPartOf"
            ]
            raw[ID_NS + "M1"] = json.dumps(body).encode()
        elif case == "truncated":
            source.maximum_candidates = 1
        elif case == "multiple_isbn":
            body = json.loads(fixture("single"))
            body["results"]["bindings"][0]["isbn"]["value"] = OTHER_ISBN
            original = source.session.post.side_effect
            source.session.post.side_effect = lambda url, **kw: (
                response(json.dumps(body).encode())
                if "SELECT DISTINCT" in kw["data"]["query"] and OTHER_ISBN in kw["data"]["query"]
                else original(url, **kw)
            )
        elif case == "multiple_book":
            # Existing relation cache keys include the parent Book: two Series reads.
            raw[ID_NS + "M2"] = raw[ID_NS + "M1"].replace(b"M1", b"M2")
            body = json.loads(fixture("single"))
            row = body["results"]["bindings"][0]
            second = json.loads(json.dumps(row).replace("M1", "M2"))
            body["results"]["bindings"].append(second)
            original = source.session.post.side_effect
            source.session.post.side_effect = lambda url, **kw: (
                response(json.dumps(body).encode())
                if "SELECT DISTINCT" in kw["data"]["query"]
                else original(url, **kw)
            )

    options["configure"] = configure
    output = talker.fetch_comic_data(issue_id=item.id)
    assert opened[0].session.post.call_count == count
    assert factory.call_count == 1
    if case == "multiple_isbn":
        assert output.series == "Series"
    else:
        assert output == to_metadata(item)
    assert_closed_once(opened[0])


@pytest.mark.parametrize("phase,count", [("discovery", 1), ("book", 2), ("series", 3)])
@pytest.mark.parametrize("error", [429, 503, "timeout"])
def test_transport_failure_keeps_history_bytes_and_no_retries(talker, tracked_sources, phase, count, error):
    opened, options, factory = tracked_sources
    item = setup_final_talker(talker)
    options.update(
        fail_uri={"discovery": "discovery", "book": ID_NS + "M1", "series": ID_NS + "C1"}[phase],
        transport=requests.Timeout("synthetic") if error == "timeout" else error,
    )
    history = talker.cache_folder / "jpbooks/latest-error.txt"
    history.parent.mkdir(parents=True, exist_ok=True)
    raw = b"previous NDL error\r\n\x00"
    history.write_bytes(raw)
    assert talker.fetch_comic_data(issue_id=item.id) == to_metadata(item)
    assert history.read_bytes() == raw
    assert factory.call_count == 1 and opened[0].session.post.call_count == count
    assert_closed_once(opened[0])


@pytest.mark.parametrize("part", ["session", "cache"])
def test_actual_source_close_failure_attempts_both_handles_and_keeps_baseline(talker, tracked_sources, part):
    opened, options, factory = tracked_sources
    item = setup_final_talker(talker)

    def configure(source, raw):
        handle = source.session if part == "session" else source.cache
        close = handle.close._mock_wraps

        def fail():
            close()
            raise OSError("synthetic close failure")

        handle.close.side_effect = fail

    options["configure"] = configure
    assert talker.fetch_comic_data(issue_id=item.id) == to_metadata(item)
    opened[0].close.assert_called_once()
    opened[0].session.close.assert_called_once()
    opened[0].cache.close.assert_called_once()
    assert opened[0].session.post.call_count == 3


@pytest.mark.parametrize("summary_status", [200, 429])
@pytest.mark.parametrize("missing_series", [False, True])
def test_real_ndl_summary_and_madb_budgets_are_separate(
    talker, no_abstract, details, tracked_sources, summary_status, missing_series, monkeypatch
):
    opened, options, factory = tracked_sources
    xml = no_abstract.replace(b"4-88594-287-X", ISBN.encode())
    talker.madb_series_supplement = True

    def get(url, **kwargs):
        result = (
            ndl_response(json.dumps(details).encode(), summary_status)
            if url == DETAIL_ENDPOINT
            else ndl_response(xml)
        )
        result.headers["Retry-After"] = "120"
        return result

    transport = talker.source.session.get = Mock(side_effect=get)
    if missing_series:
        # Production NDL parsing requires a title. Inject the synthetic missing
        # comparison input AFTER real SRU/summary retrieval, without relaxing it.
        get_record = talker.source.get
        monkeypatch.setattr(talker.source, "get", lambda *a, **kw: replace(get_record(*a, **kw), title=""))
    common = Mock(wraps=metadata_supplement.supplement_metadata)
    monkeypatch.setattr(talker_module, "supplement_metadata", common)
    history = talker.cache_folder / "jpbooks/latest-error.txt"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_bytes(b"NDL previous error")
    result = talker.fetch_comic_data(issue_id=ID, issue_number="74")
    baseline = common.call_args.args[0]
    if missing_series:
        assert not baseline.series and result.series == "Series"
        assert {k for k, v in asdict(baseline).items() if asdict(result)[k] != v} == {"series", "notes"}
    else:
        assert baseline.series and result == baseline
        factory.assert_not_called()
    if summary_status == 200:
        assert result.description == "紙版の要約・𠮷野"
    assert history.read_bytes() == b"NDL previous error"
    assert [c.args[0] for c in transport.call_args_list] == [ndl.ENDPOINT, DETAIL_ENDPOINT]
    if missing_series:
        assert opened[0].session.post.call_count == 3
    transport.reset_mock()
    assert talker.fetch_comic_data(issue_id=ID, issue_number="74") == result
    transport.assert_not_called()
    if missing_series:
        assert opened[1].session.post.call_count == 0
    for source in opened:
        assert_closed_once(source)
