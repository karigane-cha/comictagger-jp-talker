"""Offline observations, privacy, and host logging without changing acquisition policy."""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from comictalker.comictalker import TalkerDataError, TalkerNetworkError
from comictalker.vendor.pyrate_limiter import Limiter, RequestRate

from comictagger_jp_talker import http_diagnostics as diag
from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.talker import JapaneseBooksTalker

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
DATE = "Thu, 29 Oct 2026 08:00:00 GMT"
ID = "R100000002-Itest001"
EMPTY = (
    b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">'
    b"<numberOfRecords>0</numberOfRecords></searchRetrieveResponse>"
)


def response(content=b"", status=200, **headers):
    result = requests.Response()
    result.status_code = status
    result._content = content
    result.headers.update(headers)
    return result


def events(caplog, name):
    return [record.ndl for record in caplog.records if getattr(record, "ndl_event", None) == name]


@pytest.fixture
def detail(monkeypatch, caplog):
    monkeypatch.setattr(diag, "_ENABLED", True)
    caplog.set_level(logging.DEBUG, logger=diag.__name__)


@pytest.fixture
def no_abstract(xml_bytes):
    root = ET.fromstring(xml_bytes)
    for bib in root.findall(".//dcndl:BibResource", ndl.NS):
        for node in bib.findall("dcterms:abstract", ndl.NS):
            bib.remove(node)
    return ET.tostring(root)


@pytest.mark.parametrize("value", [None, "", "0", "true", "yes", " 1", "1 ", "1"])
def test_environment_is_exact_and_fixed_at_import(tmp_path, value):
    environment = os.environ.copy()
    environment.pop("JPBOOKS_HTTP_DIAGNOSTICS", None)
    if value is not None:
        environment["JPBOOKS_HTTP_DIAGNOSTICS"] = value
    code = """
import logging, os, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import requests
root = logging.getLogger()
root.setLevel(logging.WARNING)
other = logging.getLogger('another_plugin')
before = (root.level, other.level, tuple(root.handlers))
with patch.object(requests.Session, 'request', side_effect=AssertionError('Offline only')):
    from comictagger_jp_talker import http_diagnostics as d
assert d.enabled() is (sys.argv[2] == 'True')
assert d._RUN_ID is None
assert before == (root.level, other.level, tuple(root.handlers))
assert d.logger.level == (logging.DEBUG if d.enabled() else logging.NOTSET)
os.environ['JPBOOKS_HTTP_DIAGNOSTICS'] = '0' if d.enabled() else '1'
assert d.enabled() is (sys.argv[2] == 'True')
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code, str(ROOT), str(value == "1")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_disabled_success_has_no_extra_observations(source, monkeypatch, caplog):
    monkeypatch.setattr(diag, "_ENABLED", False)
    for name in ("_new_id", "utc_now", "source_fields", "response_headers", "result_fields"):
        monkeypatch.setattr(diag, name, Mock(side_effect=AssertionError(name)))
    clock = Mock(side_effect=[100.0, 102.43])
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=clock))
    with caplog.at_level(logging.DEBUG, logger=ndl.__name__):
        source.search(SearchQuery(title="private-query"))
        source.search(SearchQuery(title="private-query"))
    assert clock.call_count == 2
    assert source.session.get.call_count == 1
    assert caplog.messages == ["NDL SRU request completed: status=200 elapsed=2.43s timeout=(5,60)"]


@pytest.mark.parametrize(
    "value,kind,seconds",
    [
        (None, "absent", None),
        ("0", "delta", 0),
        ("000120", "delta", 120),
        (DATE, "http_date", 0),
        ("Thu, 29 Oct 2026 08:02:00 GMT", "http_date", 120),
        ("Thu, 29 Oct 2026 07:59:00 GMT", "http_date", 0),
        ("nonsense-secret", "invalid", None),
        ("-1", "invalid", None),
        ("1.5", "invalid", None),
        ("１２３", "invalid", None),
        ("120\r\nsecret", "invalid", None),
        ("\x7f", "invalid", None),
        ("9" * 129, "oversized", None),
        ("9" * 128, "excessive", None),
        ("2147483648", "excessive", None),
        ("2147483647", "delta", 2147483647),
        ("Fri, 31 Dec 9999 23:59:59 GMT", "excessive", None),
        (123, "invalid", None),
        (object(), "invalid", None),
    ],
)
def test_retry_after_classification(value, kind, seconds):
    fields = diag.parse_retry_after(value, NOW)
    assert fields["retry_after_kind"] == kind
    assert fields.get("retry_after_seconds") == seconds
    if kind == "http_date":
        assert fields["retry_after_past"] is ("07:59" in value)
    assert "secret" not in diag.format_fields(fields)


@pytest.mark.parametrize(
    "value,state",
    [
        (None, "absent"),
        (DATE, "valid"),
        ("invalid-secret", "invalid"),
        ("x" * 129, "oversized"),
        ("\n", "invalid"),
        (123, "invalid"),
        (object(), "invalid"),
    ],
)
def test_response_date_classification(value, state):
    fields = diag.response_headers(response(**{"Date": value}), NOW)
    assert fields["response_date_state"] == state
    if state == "valid":
        assert fields["response_date_utc"] == NOW.isoformat()
        assert fields["response_clock_delta_seconds"] == 0


def test_falsy_response_case_insensitive_and_allowlist():
    failure = response(status=429, **{"rEtRy-AfTeR": "120", "dAtE": DATE, "Set-Cookie": "secret"})
    assert not failure
    fields = diag.response_headers(failure, NOW)
    assert fields["retry_after_seconds"] == 120
    assert fields["response_date_utc"] == NOW.isoformat()
    assert "secret" not in diag.format_fields(fields)
    headers = Mock()
    headers.get.side_effect = ["120", DATE]
    diag.response_headers(SimpleNamespace(headers=headers), NOW)
    assert [call.args for call in headers.get.call_args_list] == [("Retry-After",), ("Date",)]
    headers.items.assert_not_called()


def test_header_accessor_failure_is_contained():
    headers = Mock()
    headers.get.side_effect = ValueError("private-header-error")
    fields = diag.response_headers(SimpleNamespace(headers=headers), NOW)
    assert fields == {"retry_after_kind": "invalid", "response_date_state": "invalid"}
    assert "private" not in diag.format_fields(fields)


def test_429_then_200_are_independent_operations(detail, talker, xml_bytes, caplog):
    failure = response(status=429, **{"Retry-After": "120", "Date": DATE})
    talker.source.session.get.side_effect = [failure, response(xml_bytes)]
    write = Mock(wraps=talker.source.cache.add_search_results)
    talker.source.cache.add_search_results = write
    with pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series("private-query")
    assert caught.value.sub_code == 3
    assert caught.value.__cause__.response is failure
    assert write.call_count == 0
    report = (talker.cache_folder / "jpbooks/latest-error.txt").read_bytes()
    assert talker.search_for_series("private-query")
    assert talker.source.session.get.call_count == 2
    assert write.call_count == 1
    starts = events(caplog, "operation started")
    assert len(starts) == 2 and starts[0]["correlation_id"] != starts[1]["correlation_id"]
    failed = events(caplog, "SRU request failed")[0]
    success = events(caplog, "SRU request completed")[0]
    assert failed["request_id"] != success["request_id"]
    assert failed["status"] == 429 and success["status"] == 200
    assert failed["retry_after_seconds"] == 120
    assert failed["session_id"] == success["session_id"]
    assert [event["outcome"] for event in events(caplog, "operation completed")] == [
        "network_error",
        "success",
    ]
    assert [event["http_calls"] for event in events(caplog, "operation completed")] == [1, 1]
    assert (talker.cache_folder / "jpbooks/latest-error.txt").read_bytes() == report
    assert diag._CURRENT.get() is None


def test_failed_refresh_then_hit_has_no_http_success(detail, talker, caplog):
    talker.search_for_series("private-query")
    caplog.clear()
    talker.source.session.get.return_value = response(status=429)
    with pytest.raises(TalkerNetworkError):
        talker.search_for_series("private-query", refresh_cache=True)
    assert talker.search_for_series("private-query")
    assert talker.source.session.get.call_count == 2
    assert len(events(caplog, "SRU request failed")) == 1
    assert not events(caplog, "SRU request completed")
    assert [event["http_calls"] for event in events(caplog, "operation completed")] == [1, 0]
    assert [event["cache"] for event in events(caplog, "cache resolved")] == ["REFRESH", "HIT"]


@pytest.mark.parametrize("status,code", [(429, 3), (403, 0), (500, 0)])
def test_http_failure_preserves_contract(detail, talker, status, code, caplog):
    failure = response(status=status)
    talker.source.session.get.return_value = failure
    with pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series("private-query")
    assert caught.value.sub_code == code
    assert isinstance(caught.value.__cause__, requests.HTTPError)
    assert caught.value.__cause__.response is failure
    assert talker.source.session.get.call_count == 1
    event = events(caplog, "SRU request failed")[0]
    assert event["status"] == status and event["retry_after_kind"] == "absent"
    assert not events(caplog, "SRU request completed")


@pytest.mark.parametrize(
    "error,code",
    [
        (requests.ReadTimeout(), 4),
        (requests.ConnectTimeout(), 4),
        (requests.ConnectionError(), 1),
        (requests.RequestException(), 0),
    ],
)
def test_transport_failure_preserves_contract(detail, talker, error, code, caplog):
    talker.source.session.get.side_effect = error
    with pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series("private-query")
    assert caught.value.sub_code == code and caught.value.__cause__ is error
    event = events(caplog, "SRU request failed")[0]
    assert event["status"] is None and event["error"] == type(error).__name__
    assert talker.source.session.get.call_count == 1
    assert diag._CURRENT.get() is None


def test_consecutive_429_do_not_retry_or_cache(detail, talker, caplog):
    talker.source.session.get.return_value = response(status=429)
    for _ in range(2):
        with pytest.raises(TalkerNetworkError):
            talker.search_for_series("private-query")
    assert talker.source.session.get.call_count == 2
    assert len(events(caplog, "SRU request failed")) == 2
    assert all(event["http_calls"] == 1 for event in events(caplog, "operation completed"))


@pytest.mark.parametrize("count", [2, 4])
def test_relaxation_ids_and_order(detail, talker, xml_bytes, caplog, count):
    talker.creator = "private-author" if count == 4 else ""
    talker.source.session.get.side_effect = [response(EMPTY) for _ in range(count - 1)] + [
        response(xml_bytes)
    ]
    assert talker.search_for_series("private-title 4")
    requests_started = events(caplog, "SRU request started")
    expected = (
        ["initial", "relaxed_creator", "relaxed_issue", "relaxed_both"]
        if count == 4
        else ["initial", "relaxed_issue"]
    )
    assert [event["query_stage"] for event in requests_started] == expected
    assert len({event["correlation_id"] for event in requests_started}) == 1
    assert len({event["request_id"] for event in requests_started}) == count
    assert [event["http_call_no"] for event in requests_started] == list(range(1, count + 1))
    assert talker.source.session.get.call_count == count
    queries = [call.kwargs["params"]["query"] for call in talker.source.session.get.call_args_list]
    assert 'title = "4"' in queries[0] and 'title = "4"' not in queries[-1]
    assert all('mediatype = "books"' in query for query in queries)


def test_relaxation_stops_on_429(detail, talker, caplog):
    talker.creator = "private-author"
    talker.source.session.get.side_effect = [response(EMPTY), response(status=429)]
    with pytest.raises(TalkerNetworkError):
        talker.search_for_series("private-title 4")
    assert talker.source.session.get.call_count == 2
    assert events(caplog, "operation completed")[0]["http_calls"] == 2


def test_200_parse_failure_is_not_operation_success(detail, talker, caplog):
    talker.source.session.get.return_value = response(b"<broken")
    write = Mock(wraps=talker.source.cache.add_search_results)
    talker.source.cache.add_search_results = write
    with pytest.raises(TalkerDataError):
        talker.search_for_series("private-query")
    assert events(caplog, "SRU request completed")[0]["status"] == 200
    assert events(caplog, "operation completed")[0]["outcome"] == "data_error"
    write.assert_not_called()
    assert diag._CURRENT.get() is None


def test_invalid_search_and_record_caches(detail, source, monkeypatch, caplog):
    cached = SimpleNamespace(data=SimpleNamespace(data=b"<broken"))
    monkeypatch.setattr(source.cache, "get_search_results", Mock(return_value=[cached]))
    source.search(SearchQuery(title="private-query"))
    assert events(caplog, "SRU request started")[-1]["cache"] == "INVALID"
    monkeypatch.setattr(source.cache, "get_series_info", Mock(return_value=cached))
    source.get(ID, summary_mode="none")
    decisions = events(caplog, "cache resolved")
    assert any(event["layer"] == "record" and event["cache"] == "INVALID" for event in decisions)
    assert events(caplog, "SRU request started")[-1]["cache"] == "REFRESH"


def test_status_bypasses_cache_and_next_search_is_independent(detail, talker, monkeypatch, xml_bytes, caplog):
    transport = Mock(return_value=response(xml_bytes))
    monkeypatch.setattr(requests.Session, "get", transport)
    source_before = talker.source
    assert talker.check_status({})[1]
    assert talker.search_for_series("private-query")
    assert transport.call_count == 1 and source_before.session.get.call_count == 1
    requests_started = events(caplog, "SRU request started")
    assert requests_started[0]["cache"] == "BYPASS"
    assert requests_started[0]["operation"] == "check_status"
    assert requests_started[0]["session_id"] != requests_started[1]["session_id"]
    assert requests_started[0]["correlation_id"] != requests_started[1]["correlation_id"]


def test_status_failure_marks_returned_failure(detail, talker, monkeypatch, caplog):
    monkeypatch.setattr(requests.Session, "get", Mock(return_value=response(status=429)))
    assert not talker.check_status({})[1]
    assert events(caplog, "operation completed")[0]["outcome"] == "network_error"
    assert diag._CURRENT.get() is None


def test_summary_and_record_cache_and_suppression(detail, source, no_abstract, caplog):
    source.session.get.side_effect = [response(no_abstract), response(b'{"hit":0,"list":[]}')]
    source.get(ID)
    source.get(ID)
    assert source.session.get.call_count == 2
    assert len(events(caplog, "Summary request completed")) == 1
    assert any(
        event["api"] == "Summary" and event["cache"] == "HIT" for event in events(caplog, "cache resolved")
    )
    assert any(
        event["layer"] == "record" and event["cache"] == "HIT" for event in events(caplog, "cache resolved")
    )
    caplog.clear()
    source.session.get.side_effect = [response(no_abstract), response(status=429, **{"Retry-After": "120"})]
    source.search(SearchQuery(title="refresh"), refresh=True)
    source.get(ID)
    source.get(ID)
    assert len(events(caplog, "Summary request failed")) == 1
    assert any(event["reason"] == "failure_suppressed" for event in events(caplog, "cache resolved"))
    assert not (source.cache_folder.parent / "jpbooks/latest-error.txt").exists()


def test_waits_exclude_http_duration(detail, source, monkeypatch, caplog):
    now = [0.0]
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))

    @contextlib.contextmanager
    def lock():
        now[0] += 3
        yield

    @contextlib.contextmanager
    def limiter(*args, **kwargs):
        now[0] += 7
        yield
        now[0] += 11

    def get(*args, **kwargs):
        now[0] += 2.5
        return source.session.get.return_value

    monkeypatch.setattr(ndl, "_LOCK", lock())
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    source.session.get.side_effect = get
    source.search(SearchQuery(title="private-query"))
    assert events(caplog, "lock acquired")[0]["lock_wait_ms"] == 3000
    result = events(caplog, "SRU request completed")[0]
    assert result["limiter_wait_ms"] == 7000
    assert result["elapsed"] == 2.5


def test_real_shared_limiter_after_429_has_no_new_cooldown(detail, source, tmp_path, monkeypatch, caplog):
    from comictalker.vendor.pyrate_limiter import limit_context_decorator

    now = [100.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = Limiter(RequestRate(1, 2), time_function=lambda: now[0])
    monkeypatch.setattr(ndl, "_LIMITER", limiter)
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(limit_context_decorator, "sleep", sleep)

    def get(*args, **kwargs):
        now[0] += 0.25
        return response(status=429, **{"Retry-After": "120"})

    source.session.get.side_effect = get
    with pytest.raises(TalkerNetworkError):
        source.search(SearchQuery(title="private-query"))
    other = ndl.NDLSource(tmp_path / "other")
    try:
        other.session.get = Mock(return_value=response(EMPTY))
        other.search(SearchQuery(title="different-query"))
    finally:
        other.cache.close()
        other.session.close()
    assert sleeps == [1.75]
    assert events(caplog, "SRU request completed")[0]["limiter_wait_ms"] == 1750
    assert not hasattr(source, "_sru_cooldown")


def test_sru_summary_share_operation_and_limiter(detail, talker, no_abstract, monkeypatch, caplog):
    limiter = Mock(return_value=contextlib.nullcontext())
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    talker.source.session.get.side_effect = [response(no_abstract), response(b'{"hit":0,"list":[]}')]
    talker.fetch_comic_data(issue_id=ID)
    starts = events(caplog, "SRU request started") + events(caplog, "Summary request started")
    assert len(starts) == 2
    assert starts[0]["correlation_id"] == starts[1]["correlation_id"]
    assert [event["http_call_no"] for event in starts] == [1, 2]
    assert all(call.args == ("ndlsearch",) for call in limiter.call_args_list)
    assert [call.kwargs["timeout"] for call in talker.source.session.get.call_args_list] == [(5, 60), (5, 15)]


def test_public_nested_call_is_independent_and_source_delegation_joins(detail, talker, caplog):
    with diag.operation_scope("get", "outer"):
        outer = diag._CURRENT.get()
        talker.search_for_series("private-query")
        assert diag._CURRENT.get() is outer
        talker.source.get(ID, summary_mode="none")
        assert diag._CURRENT.get() is outer
    starts = events(caplog, "operation started")
    assert len(starts) == 2 and starts[0]["correlation_id"] != starts[1]["correlation_id"]
    assert diag._CURRENT.get() is None


def test_parallel_talkers_serialize_transport_and_isolate_ids(detail, tmp_path, xml_bytes, caplog):
    entered = threading.Event()
    release = threading.Event()
    barrier = threading.Barrier(3)
    active = [0, 0]
    guard = threading.Lock()

    def get(*args, **kwargs):
        with guard:
            active[0] += 1
            active[1] = max(active)
        entered.set()
        assert release.wait(10)
        with guard:
            active[0] -= 1
        return response(xml_bytes)

    def worker(index):
        barrier.wait(10)
        talker = JapaneseBooksTalker("1.6.0b9", tmp_path / str(index))
        source = talker.source
        source.session.get = Mock(side_effect=get)
        try:
            assert talker.search_for_series("private-query")
            assert diag._CURRENT.get() is None
        finally:
            source.cache.close()
            source.session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        barrier.wait(10)
        try:
            assert entered.wait(10)
        finally:
            release.set()
        for future in futures:
            future.result(timeout=15)
    starts = events(caplog, "SRU request started")
    for field in ("correlation_id", "request_id", "source_id", "session_id", "operation_seq"):
        assert len({event[field] for event in starts}) == 2
    assert active[1] == 1


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("kind", ["http", "timeout", "header_accessor"])
def test_public_failure_is_private_but_cause_is_intact(talker, monkeypatch, caplog, enabled, kind):
    monkeypatch.setattr(diag, "_ENABLED", enabled)
    caplog.set_level(logging.DEBUG, logger=diag.__name__)
    secrets = [
        "PRIVATE_SEARCH",
        "9784885942877",
        "PRIVATE_COOKIE",
        "PRIVATE_AUTH",
        "PRIVATE_TOKEN",
        "PRIVATE_REASON",
        r"C:\Users\PRIVATE_USER",
    ]
    secret_text = " ".join(secrets)
    failure = response(status=429, **{"Retry-After": "bad\n" + secret_text, "Date": "bad"})
    failure.url = "https://example.invalid/?query=" + secret_text
    failure.reason = secret_text
    failure.headers["Cookie"] = secrets[2]
    failure.headers["Authorization"] = secrets[3]
    failure.headers["Set-Cookie"] = secrets[4]
    if kind == "timeout":
        error = requests.ReadTimeout(secret_text)
        error.__cause__ = OSError(secret_text)
        talker.source.session.get.side_effect = error
    else:
        if kind == "header_accessor":
            failure.headers = Mock()
            failure.headers.get.side_effect = ValueError(secret_text)
        talker.source.session.get.return_value = failure
    with pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series(secret_text)
    report = (talker.cache_folder / "jpbooks/latest-error.txt").read_text(encoding="utf-8")
    for secret in secrets:
        assert secret not in report and secret not in caplog.text
    assert "https://" not in report
    assert "function=" in report and "sub_code=" in report
    assert "Ctrl+C" in str(caught.value)
    if kind == "timeout":
        assert caught.value.__cause__ is error
    else:
        assert caught.value.__cause__.response is failure
    assert talker.source.session.get.call_count == 1


def test_failure_report_replacement_and_write_failure(detail, talker, monkeypatch, caplog):
    talker.source.session.get.return_value = response(status=429)
    for _ in range(2):
        with pytest.raises(TalkerNetworkError):
            talker.search_for_series("private-query")
    path = talker.cache_folder / "jpbooks/latest-error.txt"
    report = path.read_text(encoding="utf-8")
    failures = events(caplog, "SRU request failed")
    assert failures[-1]["request_id"] in report and failures[0]["request_id"] not in report
    monkeypatch.setattr(Path, "write_text", Mock(side_effect=OSError("PRIVATE_PATH")))
    with pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series("private-query")
    assert caught.value.sub_code == 3 and isinstance(caught.value.__cause__, requests.HTTPError)
    assert "PRIVATE_PATH" not in caplog.text


def test_actual_beta9_logging_reaches_existing_file_without_new_handlers(tmp_path):
    code = """
import logging, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import requests
from comictaggerlib.log import setup_logging
setup_logging(0, Path(sys.argv[2]))
root = logging.getLogger()
before = (root.level, tuple(root.handlers), logging.getLogger('comictalker').level,
          logging.getLogger('another_plugin').level)
with patch.object(requests.Session, 'request', side_effect=AssertionError('Offline only')):
    from comictagger_jp_talker import http_diagnostics as d
    with d.operation_scope('search', 'offline_probe'):
        pass
after = (root.level, tuple(root.handlers), logging.getLogger('comictalker').level,
         logging.getLogger('another_plugin').level)
assert before == after and root.level == logging.WARNING
for handler in root.handlers:
    handler.flush()
text = (Path(sys.argv[2]) / 'ComicTagger.log').read_text(encoding='utf-8')
assert text.count('NDL diagnostics enabled:') == 1
assert text.count('NDL operation started:') == 1
assert text.count('NDL operation completed:') == 1
print('beta.9 existing file handler: DEBUG delivered, no new handlers, root WARNING')
"""
    environment = {**os.environ, "JPBOOKS_HTTP_DIAGNOSTICS": "1"}
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code, str(ROOT), str(tmp_path)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
