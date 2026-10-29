"""R2: offline source/HTTP contracts, terminal output and process boundaries."""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from comicapi.comicarchive import ComicArchive
from comicapi.genericmetadata import GenericMetadata
from test_imprint_candidates import acquired, synthetic
from test_imprint_host_boundary import cbz
from test_imprint_report import evidence_for
from test_linkage import ISBN, OTHER_ISBN, literal, record, resource_bytes
from test_linkage_evidence import CASES, TracedFake, scenario, serve_linkage
from test_madb import response
from test_madb_acquisition import serve_series

from comictagger_jp_talker import imprint_diagnostics as cli
from comictagger_jp_talker import imprint_report as reports
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.sources import madb, ndl
from comictagger_jp_talker.sources.madb_models import MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_queries import ID_NS, SCHEMA_NS

ID = record().id
ARGS = ["--ndl-id", ID, "--allow-network"]


@pytest.fixture
def factories(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "default_cache_folder", lambda: tmp_path)
    ndl_source = SimpleNamespace(get=Mock(return_value=record()), session=Mock(), cache=Mock())
    madb_source = Mock()
    madb_source.__enter__ = Mock(return_value=madb_source)
    madb_source.__exit__ = Mock()
    return SimpleNamespace(
        ndl=ndl_source,
        madb=madb_source,
        kwargs={"ndl_factory": Mock(return_value=ndl_source), "madb_factory": Mock(return_value=madb_source)},
    )


@pytest.mark.parametrize(
    "args,code,message",
    [
        ([], 2, "the following arguments are required: --ndl-id"),
        (["--allow-network"], 2, "the following arguments are required: --ndl-id"),
        (["--ndl-id", ID], 2, "--allow-network is required"),
        (["--ndl-id", ID, "--format", "json"], 2, "--allow-network is required"),
        (["--ndl-id", "https://ndlsearch.ndl.go.jp/books/" + ID, "--allow-network"], 2, "Invalid NDL ID"),
        (["--ndl-id", 'x" OR title=*', "--allow-network"], 2, "Invalid NDL ID"),
        (["--ndl-id", "日本語", "--allow-network"], 2, "Invalid NDL ID"),
        (["--ndl-id", "", "--allow-network"], 2, "Invalid NDL ID"),
        (["--ndl-id", "id\n", "--allow-network"], 2, "Invalid NDL ID"),
        (ARGS + ["--ndl-id", ID], 2, "Specify --ndl-id exactly once"),
        (ARGS + [ID], 2, "unrecognized arguments:"),
        (ARGS + ["--format", "xml"], 2, "invalid choice:"),
        (ARGS + ["--archive", "a.cbz"], 2, "unrecognized arguments:"),
        (ARGS + ["--refresh"], 2, "unrecognized arguments:"),
        (ARGS + ["--endpoint", "https://example.org"], 2, "unrecognized arguments:"),
        (["--ndl-id", ID, "--allow-net"], 2, "unrecognized arguments:"),
        (["--help"], 0, "Read-only Imprint diagnostics for one NDL record."),
        (["--version"], 0, "0.4.0"),
    ],
)
def test_input_boundary_has_no_source_session_cache_or_http(args, code, message, monkeypatch, capsys):
    forbidden = Mock(side_effect=AssertionError("No I/O before permission"))
    for cls, name in (
        (requests.Session, "__init__"),
        (requests.Session, "request"),
        (ndl.ComicCacher, "__init__"),
        (Path, "mkdir"),
    ):
        monkeypatch.setattr(cls, name, forbidden)
    monkeypatch.setattr(cli, "default_cache_folder", forbidden)
    assert cli.main(args, ndl_factory=forbidden, madb_factory=forbidden) == code
    forbidden.assert_not_called()
    out = capsys.readouterr()
    assert not out.out if code else out.out
    assert message in (out.err if code else out.out)
    if not code:
        assert out.err == ""
    if args == ["--help"]:
        assert "One NDL bibliographic ID (not a URL)" in out.out
        assert "Permit NDL/MADB requests and source cache I/O" in out.out
    elif args == ["--version"]:
        assert out.out == "0.4.0\n"


def test_import_does_not_construct_sources(tmp_path):
    code = """
from unittest.mock import patch
import requests
from comictagger_jp_talker.sources.ndl import NDLSource, ComicCacher
from comictagger_jp_talker.sources.madb import MADBSource
with patch.object(requests.Session, '__init__', side_effect=AssertionError), \
     patch.object(NDLSource, '__init__', side_effect=AssertionError), \
     patch.object(MADBSource, '__init__', side_effect=AssertionError), \
     patch.object(ComicCacher, '__init__', side_effect=AssertionError):
    import comictagger_jp_talker.imprint_diagnostics
"""
    result = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.fixture
def http_sources(tmp_path, monkeypatch, xml_bytes):
    monkeypatch.setattr(cli, "default_cache_folder", lambda: tmp_path)
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    opened = SimpleNamespace(ndl=[], madb=[], configure=lambda source: serve_linkage(source))
    body = xml_bytes.replace(b"R100000002-Itest001", ID.encode()).replace(b"4-88594-287-X", ISBN.encode())
    # The fixture ISBN is an ISBN-10 and raw values remain source parser outputs.
    opened.body = body
    opened.ndl_error = None

    def ndl_factory(path):
        source = ndl.NDLSource(path)
        reply = requests.Response()
        reply.status_code = 200
        reply._content = opened.body
        source.session.get = Mock(return_value=reply, side_effect=opened.ndl_error)
        source.session.close = Mock(wraps=source.session.close)
        source.cache.close = Mock(wraps=source.cache.close)
        opened.ndl.append(source)
        return source

    def madb_factory(path):
        source = madb.MADBSource(path)
        source.session.post = Mock()
        opened.configure(source)
        source.session.close = Mock(wraps=source.session.close)
        source.cache.close = Mock(wraps=source.cache.close)
        source.close = Mock(wraps=source.close)
        opened.madb.append(source)
        return source

    opened.kwargs = {
        "ndl_factory": Mock(side_effect=ndl_factory),
        "madb_factory": Mock(side_effect=madb_factory),
    }
    return opened


@pytest.mark.parametrize("format", ["text", "json"])
@pytest.mark.parametrize("with_series,count", [(True, 3), (False, 2)])
def test_real_sources_cold_warm_scope_summary_free_and_close(
    http_sources, capsys, monkeypatch, format, with_series, count
):
    if not with_series:
        http_sources.configure = lambda source: serve_linkage(source, raw=serve_series(source, ()))
    core = Mock(wraps=cli.acquire_linked_record_evidence)
    describe = Mock(wraps=cli.describe_imprint_evidence)
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", core)
    monkeypatch.setattr(cli, "describe_imprint_evidence", describe)
    for warm in (False, True):
        assert cli.main(ARGS + ["--format", format], **http_sources.kwargs) == 0
        out = capsys.readouterr()
        assert not out.err
        n, m = http_sources.ndl[-1], http_sources.madb[-1]
        assert n.session.get.call_count == (0 if warm else 1)
        assert m.session.post.call_count == (0 if warm else count)
        assert all(
            c.args[0] == ndl.ENDPOINT and c.kwargs["timeout"] == (5, 60) for c in n.session.get.call_args_list
        )
        for c in m.session.post.call_args_list:
            assert c.args[0] == madb.ENDPOINT and c.kwargs["timeout"] == (5, 30)
            assert not any(v in c.kwargs["data"]["query"] for v in ("/C2>", "/C3>", "/ref/S1>"))
        for source in (n, m):
            source.session.close.assert_called_once()
            source.cache.close.assert_called_once()
        m.close.assert_called_once()
        assert core.call_count == describe.call_count == (2 if warm else 1)
        assert core.call_args.kwargs == {"refresh": False, "scope": "series_linkage"}
        evidence = describe.call_args.args[0]
        expected = reports.report_to_json_data(reports.describe_imprint_evidence(evidence))
        assert evidence.acquisition_context.ndl_input.isbns == (ISBN,)
        if format == "json":
            assert json.loads(out.out) == expected
            assert expected["schema_version"] == "imprint-report-v1"
        else:
            assert "Existing Imprint: not assessed" in out.out and "Apply allowed: no" in out.out
        if warm:
            assert all(e.origin_fetched_at is None for e in evidence.acquisition_context.events)


@pytest.mark.parametrize("failure", ["zero", "mismatch", "timeout", "http", "sru", "xml"])
def test_ndl_failures_never_start_madb(http_sources, failure, capsys):
    if failure == "zero":
        http_sources.body = b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/"><numberOfRecords>0</numberOfRecords></searchRetrieveResponse>'
    elif failure == "mismatch":
        http_sources.body = http_sources.body.replace(ID.encode(), b"different")
    elif failure == "timeout":
        http_sources.ndl_error = requests.Timeout("NDL timeout")
    elif failure == "http":
        reply = requests.Response()
        reply.status_code = 503
        http_sources.ndl_error = requests.HTTPError(response=reply)
    elif failure == "sru":
        http_sources.body = (
            b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/"><diagnostics>'
            b'<diagnostic xmlns="http://www.loc.gov/zing/srw/diagnostic/">'
            b"<message>Protocol error</message></diagnostic></diagnostics></searchRetrieveResponse>"
        )
    else:
        http_sources.body = b"<bad xml"
    assert cli.main(ARGS + ["--format", "json"], **http_sources.kwargs) == 3
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("Imprint diagnostics error: ")
    if failure == "zero":
        assert "TalkerDataError" in out.err
    http_sources.kwargs["madb_factory"].assert_not_called()
    http_sources.ndl[0].session.close.assert_called_once()
    http_sources.ndl[0].cache.close.assert_called_once()


def test_cached_ndl_id_mismatch_is_rejected(factories, capsys):
    factories.ndl.get.return_value.id = "different"
    assert cli.main(ARGS, **factories.kwargs) == 3
    assert "different bibliographic ID" in capsys.readouterr().err
    factories.kwargs["madb_factory"].assert_not_called()


@pytest.mark.parametrize(
    "phase,uri,count", [("discovery", "discovery", 1), ("book", ID_NS + "M1", 2), ("series", ID_NS + "C1", 3)]
)
@pytest.mark.parametrize(
    "transport", [429, 503, requests.Timeout("timeout"), requests.ConnectionError("offline")]
)
@pytest.mark.parametrize("format", ["text", "json"])
def test_http_failure_outputs_incomplete_report(http_sources, capsys, phase, uri, count, transport, format):
    http_sources.configure = lambda s: serve_linkage(s, fail_uri=uri, transport=transport)
    assert cli.main(ARGS + ["--format", format], **http_sources.kwargs) == 3
    output = capsys.readouterr()
    assert output.err == ""  # Incomplete evidence is reported in the report, not a new message.
    if format == "json":
        data = json.loads(output.out)
        assert data["apply_allowed"] is data["writes_performed"] is False
        events = [e for t in data["acquisition"]["traces"] for e in t["events"]]
        assert any(e["error"] for e in events)
    else:
        assert output.out.startswith("Read-only Imprint diagnostics\n")
        assert '"failed"' in output.out
        assert "Apply allowed: no\nWrites performed: no" in output.out
        assert "Complete report detail (no display truncation; indices preserve ledger order):" in output.out
    assert http_sources.madb[0].session.post.call_count == count
    http_sources.madb[0].close.assert_called_once()


@pytest.mark.parametrize(
    "case",
    ["empty", "no_isbn", "budget", "book_truncated", "series_truncated", "partial_discovery", "byte_cap"],
)
def test_real_source_incompleteness_and_intentional_nonrequests(http_sources, case, capsys, monkeypatch):
    if case == "no_isbn":
        http_sources.body = http_sources.body.replace(ISBN.encode(), b"invalid")

    def configure(source):
        refs = tuple(RDFTerm("uri", ID_NS + f"C{i}") for i in range(1, 14 if case == "budget" else 2))
        raw = serve_series(source, refs)
        serve_linkage(source, raw=raw, search="empty" if case == "empty" else "single")
        if case in ("book_truncated", "series_truncated"):
            source.maximum_triples = 2 if case == "book_truncated" else 3
        elif case == "partial_discovery":
            parse = madb.parse_search
            monkeypatch.setattr(
                madb, "parse_search", lambda *a, **kw: replace(parse(*a, **kw), truncated=True)
            )
        elif case == "byte_cap":
            source.session.post.side_effect = lambda *a, **kw: response(b"x" * (madb.MAX_RESPONSE_BYTES + 1))

    http_sources.configure = configure
    assert cli.main(ARGS + ["--format", "json"], **http_sources.kwargs) == (
        0 if case in ("empty", "no_isbn") else 3
    )
    data = json.loads(capsys.readouterr().out)
    if case == "no_isbn":
        assert data["acquisition"]["discovery"]["reasons"] == ["no_valid_isbn"]
        http_sources.madb[0].session.post.assert_not_called()
    elif case == "budget":
        assert http_sources.madb[0].session.post.call_count == 14
        assert "relation_budget" in json.dumps(data)
    elif case == "empty":
        assert not data["books"] and data["acquisition"]["discovery"]["state"] == "complete"


class CompleteFake(TracedFake):
    """Synthetic attestation of all required scope, including no-Series cases."""

    def outcome(self, operation, key, kind, refresh):
        result = super().outcome(operation, key, kind, refresh)
        if kind == "book" and result.value is not None:
            result = replace(
                result,
                context=acquired(
                    result.value, discovery=State.NOT_REQUESTED, book_series_scope=State.COMPLETE
                ),
            )
        return result


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("traced", [True, False])
def test_all_ledger_states_are_rendered_without_re_evaluation(name, traced, factories, monkeypatch, capsys):
    original, source = scenario(name)
    evidence = cli.acquire_linked_record_evidence(original, CompleteFake(source) if traced else source)
    expected = reports.describe_imprint_evidence(evidence)
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence))
    describe = Mock(wraps=cli.describe_imprint_evidence)
    monkeypatch.setattr(cli, "describe_imprint_evidence", describe)
    assert cli.main(ARGS + ["--format", "json"], **factories.kwargs) in (0, 3)
    data = json.loads(capsys.readouterr().out)
    assert data == reports.report_to_json_data(expected)
    describe.assert_called_once_with(evidence)
    text = cli.render_text(expected)
    for i, (book, diagnostic) in enumerate(
        zip(evidence.acquisition_context.books, expected.books, strict=True)
    ):
        assert f"Book [{i}]" in text
        assert diagnostic.state.value in text
        assert cli.terminal_string(book.book_id) in text
        assert book.context.book.value in text
    if name in (
        "exact",
        "strong",
        "unsafe",
        "exact_isbn_conflict",
        "ambiguous",
        "two_direct",
        "conflicting_discovery_uri",
    ):
        assert cli.acquisition_exit_code(expected) == (0 if traced else 3)
    elif name == "no_isbn":
        assert cli.acquisition_exit_code(expected) == 0
        assert "without MADB candidate evaluation material" in text
    if name in ("first_book_failure", "second_book_failure", "book_id_mismatch", "book_uri_mismatch"):
        assert cli.acquisition_exit_code(expected) == 3


@pytest.mark.parametrize(
    "labels,extra,state",
    [
        (("Label",), (), "hold"),
        ((), (), "skip"),
        (("Edition",), ((SCHEMA_NS + "version", literal("Edition")),), "reject"),
    ],
)
def test_semantic_hold_reject_skip_are_success(labels, extra, state):
    report = reports.describe_imprint_evidence(
        evidence_for(synthetic(labels, extra=extra), book_series_scope=State.COMPLETE)
    )
    assert report.books[0].evaluation.state.value == state
    assert cli.acquisition_exit_code(report) == 0
    assert f"eligibility={state}" in cli.render_text(report)


@pytest.mark.parametrize("format", ["text", "json"])
def test_english_cli_preserves_japanese_source_evidence(factories, monkeypatch, capsys, format, talker):
    title = "ご注文はうさぎですか? volume 1"
    publisher = "芳文社"
    labels = ("Kirara menu", "Manga time KR comics", "Manga time KR comics　／　Kirara menu")
    # Synthetic combination of raw strings; no live measurement or semantic attestation.
    bundle = synthetic(labels, extra=((SCHEMA_NS + "publisher", literal("芳文社　∥　ホウブンシャ")),))
    evidence = evidence_for(
        bundle, replace(record(), title=title, publishers=[publisher]), book_series_scope=State.COMPLETE
    )
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence))
    assert cli.main(ARGS + ["--format", format], **factories.kwargs) == 0
    output = capsys.readouterr()
    assert output.err == ""
    expected = reports.report_to_json_data(reports.describe_imprint_evidence(evidence))
    if format == "json":
        assert json.loads(output.out) == expected
        assert output.out.isascii()  # Japanese is preserved through the existing Unicode escaping.
        assert "Read-only Imprint diagnostics" not in output.out
    else:
        assert output.out.startswith("Read-only Imprint diagnostics\n")
        for raw in (title, publisher, "芳文社　∥　ホウブンシャ", *labels):
            assert cli.terminal_string(raw) in output.out
        assert "Authority: not supplied\nArchive: not supplied\nExisting Imprint: not assessed" in output.out
        assert "Apply allowed: no\nWrites performed: no" in output.out
    assert expected["acquisition"]["ndl_input"]["title"] == title
    assert expected["books"][0]["evaluation"]["state"] == "reject"
    assert expected["schema_version"] == "imprint-report-v1"
    assert expected["apply_allowed"] is expected["writes_performed"] is False
    assert "日本語書籍・漫画の書誌メタデータ" in talker.about


def test_external_japanese_exception_detail_is_quoted_not_translated(factories, capsys):
    detail = "外部取得失敗\n\x1b[31m"
    factories.ndl.get.side_effect = OSError(detail)
    assert cli.main(ARGS, **factories.kwargs) == 3
    output = capsys.readouterr()
    assert output.out == ""
    prefix = "Imprint diagnostics error: "
    assert output.err.startswith(prefix)
    assert f"OSError: {detail}" in json.loads(output.err.removeprefix(prefix))
    assert output.err.isascii() and "\x1b" not in output.err


RAW_VALUES = [
    " 日本語𠮷📚 &<>\"'　",
    "\\u001b",
    "\r\n\t",
    "\x1b[31mRED\x1b[0m",
    "\x1b]0;title\x07",
    "".join(map(chr, range(0x20))),
    "".join(map(chr, range(0x7F, 0xA0))),
    "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069",
    "\u200b\u200c\u200d\u2060\ufeff\u00ad\u034f\ufe0f\U000e0100",
    "\u115f\u1160\u3164\uffa0\u2028\u2029",
    "e\u0301か\u3099",
    "\ud800",
]


@pytest.mark.parametrize("raw", RAW_VALUES)
def test_terminal_string_is_safe_and_json_reversible(raw):
    escaped = cli.terminal_string(raw)
    assert json.loads(escaped) == raw
    assert all(ord(c) >= 32 and not 0x7F <= ord(c) < 0xA0 for c in escaped)
    for char in "\x1b\u202e\u2066\u200b\u034f\ufe0f\u115f\ud800":
        assert char not in escaped


@pytest.mark.parametrize("raw", RAW_VALUES[:-1])
def test_renderers_preserve_raw_and_do_not_execute_terminal_controls(raw):
    report = reports.describe_imprint_evidence(evidence_for(synthetic((raw,))))
    text = cli.render_text(report)
    data = json.loads(cli.render_json(report))
    assert cli.terminal_string(raw) in text
    assert "\x1b" not in text and "\u202e" not in text and "\r" not in text and "\t" not in text
    assert (
        data["books"][0]["evaluation"]["comparison"]["classification"]["terms"][0]["candidate"]["evidence"][
            "raw_value"
        ]["value"]
        == raw
    )
    assert data == reports.report_to_json_data(report)


@pytest.mark.parametrize("format", ["text", "json"])
def test_full_output_large_evidence_and_duplicate_ledger(http_sources, monkeypatch, capsys, format):
    bundle = synthetic(())
    terms = tuple(literal(f" 候補 {i} 📚 ") for i in range(500))
    bundle = replace(
        bundle,
        book=replace(
            bundle.book,
            labels=terms,
            statements=(
                *bundle.book.statements,
                *(MADBStatement(bundle.book.uri, SCHEMA_NS + "brand", t) for t in terms),
            ),
        ),
    )
    evidence = evidence_for(bundle)
    ledger = evidence.acquisition_context
    book = ledger.books[0]
    # Obtain genuine synthetic-source events, then repeat them without dropping positions.
    n = http_sources.kwargs["ndl_factory"](cli.default_cache_folder())
    s = http_sources.kwargs["madb_factory"](cli.default_cache_folder())
    try:
        observed = cli.acquire_linked_record_evidence(n.get(ID, summary_mode="none"), s)
    finally:
        n.session.close()
        n.cache.close()
        s.close()
    event = observed.acquisition_context.events[0]
    trace = replace(book.acquisition.trace, events=(event,) * 1001)
    book = replace(book, acquisition=replace(book.acquisition, trace=trace))
    evidence = replace(
        evidence,
        bundles=evidence.bundles * 2,
        acquisition_context=replace(ledger, books=(book, book), traces=(ledger.traces[0], trace, trace)),
    )
    report = reports.describe_imprint_evidence(evidence)
    if format == "text":
        text = cli.render_text(report)
        assert "Book [0]" in text and "Book [1]" in text and "[1000]" in text
        assert "no display truncation" in text and "候補 499" in text
    else:
        data = json.loads(cli.render_json(report))
        assert len(data["books"]) == 2
        assert len(data["acquisition"]["traces"][1]["events"]) == 1001
        assert len(data["books"][0]["evaluation"]["comparison"]["classification"]["terms"]) == 500


@pytest.mark.parametrize("stage", ["ndl", "madb_init", "core", "report", "json", "text"])
@pytest.mark.parametrize(
    "error,code",
    [
        (ValueError("contract"), 4),
        (TypeError("type"), 4),
        (AssertionError("bug"), 4),
        (KeyboardInterrupt(), 130),
    ],
)
def test_internal_failures_interrupts_and_cleanup(factories, monkeypatch, capsys, stage, error, code):
    evidence = evidence_for()
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence))
    if stage == "ndl":
        factories.ndl.get.side_effect = error
    elif stage == "madb_init":
        factories.kwargs["madb_factory"].side_effect = error
    else:
        target = {
            "core": "acquire_linked_record_evidence",
            "report": "describe_imprint_evidence",
            "json": "render_json",
            "text": "render_text",
        }[stage]
        monkeypatch.setattr(cli, target, Mock(side_effect=error))
    assert cli.main(ARGS + ["--format", "text" if stage == "text" else "json"], **factories.kwargs) == code
    out = capsys.readouterr()
    assert not out.out and out.err.startswith("Imprint diagnostics error: ")
    assert type(error).__name__ in out.err
    factories.ndl.session.close.assert_called_once()
    factories.ndl.cache.close.assert_called_once()
    if stage not in ("ndl", "madb_init"):
        factories.madb.__exit__.assert_called_once()
        factories.madb.close.assert_not_called()  # The source's exit owns close.


@pytest.mark.parametrize("stage", ["ndl_init", "madb_init", "core"])
@pytest.mark.parametrize("error", [OSError("cache I/O"), sqlite3.DatabaseError("cache DB")])
def test_acquisition_io_failures_are_external(factories, monkeypatch, capsys, stage, error):
    if stage.endswith("init"):
        factories.kwargs[stage.replace("_init", "_factory")].side_effect = error
    else:
        monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(side_effect=error))
    assert cli.main(ARGS, **factories.kwargs) == 3
    assert not capsys.readouterr().out
    if stage == "ndl_init":
        factories.ndl.session.close.assert_not_called()
    else:
        factories.ndl.session.close.assert_called_once()


@pytest.mark.parametrize("where", ["ndl_session", "ndl_cache", "madb_exit", "madb_enter"])
@pytest.mark.parametrize("primary", [None, RuntimeError("original acquisition failure"), KeyboardInterrupt()])
def test_close_failures_preserve_primary_and_close_other_resources(
    factories, monkeypatch, capsys, where, primary
):
    core = Mock(return_value=evidence_for(), side_effect=primary)
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", core)
    target = {
        "ndl_session": factories.ndl.session.close,
        "ndl_cache": factories.ndl.cache.close,
        "madb_exit": factories.madb.__exit__,
        "madb_enter": factories.madb.__enter__,
    }[where]
    target.side_effect = OSError("cleanup/enter problem")
    assert cli.main(ARGS, **factories.kwargs) == (
        3 if where == "madb_enter" else 130 if isinstance(primary, KeyboardInterrupt) else 4
    )
    out = capsys.readouterr()
    assert not out.out and "cleanup/enter problem" in out.err
    if primary is not None and where != "madb_enter":
        assert type(primary).__name__ in out.err
        assert str(primary) in out.err
    factories.ndl.session.close.assert_called_once()
    factories.ndl.cache.close.assert_called_once()
    factories.madb.__exit__.assert_called_once()


def test_real_madb_close_failure_still_closes_cache_and_ndl(http_sources, capsys):
    original = http_sources.kwargs["madb_factory"].side_effect

    def factory(path):
        source = original(path)
        source.session.close.side_effect = OSError("session close failed")
        return source

    http_sources.kwargs["madb_factory"].side_effect = factory
    assert cli.main(ARGS, **http_sources.kwargs) == 4
    assert "session close failed" in capsys.readouterr().err
    http_sources.madb[0].cache.close.assert_called_once()
    http_sources.ndl[0].cache.close.assert_called_once()


@pytest.mark.parametrize(
    "error",
    [BrokenPipeError("pipe"), OSError("disk"), UnicodeEncodeError("ascii", "日本語", 0, 1, "no encoding")],
)
@pytest.mark.parametrize("stage", ["write", "flush"])
def test_output_failures_are_internal_after_close(factories, monkeypatch, capsys, error, stage):
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence_for()))
    stream = Mock()
    stream.write.side_effect = lambda s: len(s)
    getattr(stream, stage).side_effect = error
    monkeypatch.setattr(sys, "stdout", stream)
    assert cli.main(ARGS + ["--format", "json"], **factories.kwargs) == 4
    factories.ndl.cache.close.assert_called_once()
    factories.madb.__exit__.assert_called_once()
    stderr = capsys.readouterr().err
    assert stderr.startswith("Imprint diagnostics error: ") and type(error).__name__ in stderr


@pytest.mark.parametrize("bad", [object(), float("nan"), float("inf"), b"unknown"])
def test_unsupported_serialization_types_do_not_produce_partial_json(factories, monkeypatch, capsys, bad):
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence_for()))
    report = replace(reports.describe_imprint_evidence(evidence_for()), plugin_version=bad)
    monkeypatch.setattr(cli, "describe_imprint_evidence", Mock(return_value=report))
    assert cli.main(ARGS + ["--format", "json"], **factories.kwargs) == 4
    output = capsys.readouterr()
    assert output.out == "" and "TypeError" in output.err


def test_stdout_logging_handlers_are_suppressed_and_restored(factories, monkeypatch, capsys):
    evidence = evidence_for()
    handler = logging.StreamHandler(sys.stdout)
    logger = logging.getLogger("comictagger_jp_talker.sources.ndl")
    before = logging.root.manager.disable
    logger.addHandler(handler)

    def noisy(*args, **kwargs):
        logger.critical("\x1b[31m must never contaminate stdout")
        return evidence

    monkeypatch.setattr(cli, "acquire_linked_record_evidence", noisy)
    try:
        assert cli.main(ARGS + ["--format", "json"], **factories.kwargs) == 3
        data = json.loads(capsys.readouterr().out)
        assert data["schema_version"] == "imprint-report-v1"
        assert logging.root.manager.disable == before and handler in logger.handlers
    finally:
        logger.removeHandler(handler)


def test_cli_cannot_write_metadata_archives_or_error_history(http_sources, tmp_path, monkeypatch, capsys):
    metadata = GenericMetadata(imprint=" 既存値 ", notes="Notes\n", description="description")
    archive = cbz(tmp_path)
    history = tmp_path / "jpbooks" / "latest-error.txt"
    history.parent.mkdir()
    history.write_bytes(b"existing history\r\n")
    before = deepcopy(metadata), archive.read_bytes(), history.read_bytes()
    forbidden = Mock(side_effect=AssertionError("Read-only boundary"))
    monkeypatch.setattr(GenericMetadata, "__init__", forbidden)
    monkeypatch.setattr(GenericMetadata, "__setattr__", forbidden)
    monkeypatch.setattr(ComicArchive, "__init__", forbidden)
    monkeypatch.setattr(ComicArchive, "write_tags", forbidden)
    assert cli.main(ARGS, **http_sources.kwargs) == 0
    assert (metadata, archive.read_bytes(), history.read_bytes()) == before
    forbidden.assert_not_called()
    for file in ("talker.py", "metadata_supplement.py", "series_supplement.py"):
        assert "imprint_diagnostics" not in (Path(cli.__file__).parent / file).read_text(encoding="utf-8")


def test_ndl_raw_fields_are_not_trimmed_by_cli(factories, monkeypatch, capsys):
    ndl_record = factories.ndl.get.return_value
    ndl_record.title = " 原題𠮷\t "
    ndl_record.volumes = [" ００１ "]
    ndl_record.isbns = [" 4-592-88071-4 "]
    before = deepcopy(ndl_record)
    source = CompleteFake(scenario("exact")[1])
    factories.madb.__enter__.return_value = source
    assert cli.main(ARGS + ["--format", "json"], **factories.kwargs) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["acquisition"]["ndl_input"]["title"] == before.title
    assert data["acquisition"]["ndl_input"]["isbns"] == before.isbns
    assert data["acquisition"]["ndl_input"]["volumes"] == before.volumes
    assert ndl_record == before
    factories.ndl.get.assert_called_once_with(ID, summary_mode="none")


def test_multiple_isbn_book_series_http_counts(http_sources, capsys):
    http_sources.body = http_sources.body.replace(
        ISBN.encode(),
        ISBN.encode()
        + b'</dcterms:identifier><dcterms:identifier rdf:datatype="http://ndl.go.jp/dcndl/terms/ISBN">'
        + OTHER_ISBN.encode(),
    )

    def configure(source):
        def post(url, **kwargs):
            q = kwargs["data"]["query"]
            if q.startswith("PREFIX"):
                return response(
                    json.dumps(
                        {
                            "head": {"vars": ["book", "identifier", "isbn"]},
                            "results": {
                                "bindings": [
                                    {
                                        "book": {"type": "uri", "value": ID_NS + identifier},
                                        "isbn": {
                                            "type": "literal",
                                            "value": OTHER_ISBN if OTHER_ISBN in q else ISBN,
                                        },
                                    }
                                    for identifier in ("M1", "M2")
                                ]
                            },
                        }
                    ).encode()
                )
            identifier = q.split("<", 1)[1].split(">", 1)[0].rsplit("/", 1)[1]
            if identifier.startswith("M"):
                return response(
                    resource_bytes(
                        identifier,
                        "MangaBook",
                        [
                            (SCHEMA_NS + "isbn", literal(ISBN)),
                            (SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + "C" + identifier[1:])),
                        ],
                    )
                )
            return response(
                resource_bytes(identifier, "MangaBookSeries", [(SCHEMA_NS + "name", literal("Series"))])
            )

        source.session.post.side_effect = post

    http_sources.configure = configure
    assert cli.main(ARGS + ["--format", "json"], **http_sources.kwargs) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["books"]) == len(data["acquisition"]["discovery"]["attempts"]) == 2
    assert http_sources.ndl[0].session.get.call_count == 1
    assert http_sources.madb[0].session.post.call_count == 6


@pytest.mark.parametrize("stage", ["ndl_session", "ndl_cache", "madb_exit"])
def test_interrupt_during_cleanup_attempts_remaining_closes(factories, monkeypatch, capsys, stage):
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence_for()))
    action = {
        "ndl_session": factories.ndl.session.close,
        "ndl_cache": factories.ndl.cache.close,
        "madb_exit": factories.madb.__exit__,
    }[stage]
    action.side_effect = KeyboardInterrupt()
    assert cli.main(ARGS, **factories.kwargs) == 130
    assert "KeyboardInterrupt" in capsys.readouterr().err
    factories.ndl.session.close.assert_called_once()
    factories.ndl.cache.close.assert_called_once()
    factories.madb.__exit__.assert_called_once()


def test_short_stdout_write_is_failure(factories, monkeypatch, capsys):
    monkeypatch.setattr(cli, "acquire_linked_record_evidence", Mock(return_value=evidence_for()))
    stream = Mock()
    stream.write.return_value = 1
    monkeypatch.setattr(sys, "stdout", stream)
    assert cli.main(ARGS, **factories.kwargs) == 4
    assert "Incomplete stdout write" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--help", "--version"])
def test_help_version_flush_failure_is_not_success(option, monkeypatch, capsys):
    stream = Mock()
    stream.flush.side_effect = OSError("flush failed")
    monkeypatch.setattr(sys, "stdout", stream)
    forbidden = Mock(side_effect=AssertionError("No source for help/version"))
    assert cli.main([option], ndl_factory=forbidden, madb_factory=forbidden) == 4
    assert "flush failed" in capsys.readouterr().err
    forbidden.assert_not_called()


@pytest.mark.parametrize("interrupted", [False, True])
def test_logging_and_all_failure_details_survive_multiple_close_errors(
    factories, monkeypatch, capsys, interrupted
):
    monkeypatch.setattr(
        cli, "acquire_linked_record_evidence", Mock(side_effect=ValueError("primary contract"))
    )
    factories.ndl.session.close.side_effect = OSError("NDL session failure")
    factories.ndl.cache.close.side_effect = OSError("NDL cache failure")

    def exit_with_nested_failures(*exc):
        try:
            if interrupted:
                raise KeyboardInterrupt("MADB session failure")
            raise OSError("MADB session failure")
        finally:
            raise sqlite3.DatabaseError("MADB cache failure")

    factories.madb.__exit__.side_effect = exit_with_nested_failures
    before = logging.root.manager.disable
    assert cli.main(ARGS, **factories.kwargs) == (130 if interrupted else 4)
    output = capsys.readouterr()
    assert not output.out
    for message in (
        "primary contract",
        "NDL session failure",
        "NDL cache failure",
        "MADB session failure",
        "MADB cache failure",
    ):
        assert message in output.err
    assert logging.root.manager.disable == before


def test_argument_error_cannot_inject_terminal_controls(capsys):
    assert cli.main(ARGS + ["--unknown\x1b[31m\u202e"]) == 2
    output = capsys.readouterr()
    assert not output.out and "\x1b" not in output.err and "\u202e" not in output.err
