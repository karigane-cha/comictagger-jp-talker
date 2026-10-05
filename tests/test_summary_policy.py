"""Optional-summary request budgets and failure boundaries, with synthetic HTTP only."""

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests
import test_summary
from comictalker.comictalker import TalkerDataError, TalkerNetworkError
from test_summary import ID

from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.sources.ndl_summary import DETAIL_ENDPOINT

REPORTED_ID = "R100000002-I025375656"


@pytest.fixture
def no_abstract(xml_bytes):
    return test_summary.no_abstract.__wrapped__(xml_bytes)


@pytest.fixture
def details():
    return test_summary.details.__wrapped__()


def response(content, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = content
    return result


def invoke(talker, path, identifier=ID):
    if path == "search":
        return talker.search_for_series("488594287X")
    if path == "series":
        return talker.fetch_series(identifier)
    if path == "issues":
        return talker.fetch_issues_in_series(identifier)
    if path == "number_year":
        return talker.fetch_issues_by_series_issue_num_and_year([identifier], "74", 2025)
    return talker.fetch_comic_data(issue_id="", series_id=identifier, issue_number="")


@pytest.mark.parametrize("path", ["search", "series", "issues", "number_year", "comic"])
@pytest.mark.parametrize("cache", ["cold", "SRU", "summary"])
def test_host_request_budgets(talker, no_abstract, details, path, cache):
    def get(url, **kwargs):
        return response(json.dumps(details).encode() if url == DETAIL_ENDPOINT else no_abstract)

    transport = talker.source.session.get = Mock(side_effect=get)
    if cache != "cold":
        talker.search_for_series("488594287X")
    if cache == "summary":
        talker.source.get(ID)
    transport.reset_mock()
    invoke(talker, path)
    urls = [call.args[0] for call in transport.call_args_list]
    assert urls.count(ndl.ENDPOINT) == (1 if cache == "cold" else 0)
    assert urls.count(DETAIL_ENDPOINT) == (1 if path == "comic" and cache != "summary" else 0)


@pytest.mark.parametrize("status", [200, 429])
@pytest.mark.parametrize("warm_sru", [False, True])
def test_reported_record_standard_flow(talker, no_abstract, details, status, warm_sru, caplog):
    xml = no_abstract.replace(ID.encode(), REPORTED_ID.encode())
    details["list"][0]["id"] = REPORTED_ID

    def get(url, **kwargs):
        result = response(json.dumps(details).encode(), status) if url == DETAIL_ENDPOINT else response(xml)
        result.headers["Retry-After"] = "120"
        return result

    transport = talker.source.session.get = Mock(side_effect=get)
    if warm_sru:
        talker.search_for_series("488594287X")
    transport.reset_mock()
    assert invoke(talker, "series", REPORTED_ID).id == REPORTED_ID
    assert all(call.args[0] != DETAIL_ENDPOINT for call in transport.call_args_list)
    base = to_metadata(talker.source.get(REPORTED_ID, summary_mode="none"))
    output = invoke(talker, "comic", REPORTED_ID)
    assert output.issue_id == REPORTED_ID
    if status == 429:
        assert asdict(output) == asdict(base)
        assert "status=429 Retry-After=120" in caplog.text
        assert not talker.source.cache.get_search_results(ndl.SUMMARY_CACHE, REPORTED_ID)
    else:
        assert output.description == "紙版の要約・𠮷野"
    assert invoke(talker, "comic", REPORTED_ID) == output
    assert sum(call.args[0] == DETAIL_ENDPOINT for call in transport.call_args_list) == 1
    assert not (talker.cache_folder / "jpbooks/latest-error.txt").exists()


@pytest.mark.parametrize("path", ["series", "issues", "number_year"])
def test_candidates_skip_summary_and_madb_even_when_enabled(talker, no_abstract, path, monkeypatch):
    from comicapi.genericmetadata import GenericMetadata

    # Simulate missing output Series without weakening the required SRU title parser.
    talker.source.session.get.return_value._content = no_abstract
    monkeypatch.setattr("comictagger_jp_talker.talker.to_metadata", Mock(return_value=GenericMetadata()))
    talker.madb_series_supplement = True
    monkeypatch.setattr(requests.Session, "post", Mock(side_effect=AssertionError("Candidate MADB request")))
    invoke(talker, path)
    assert all(call.args[0] != DETAIL_ENDPOINT for call in talker.source.session.get.call_args_list)


@pytest.mark.parametrize(
    "failure", ["429", "503", "timeout", "connection", "transport", "json", "envelope", "wrong_id", "item"]
)
def test_optional_failures_preserve_every_metadata_field(talker, no_abstract, failure, caplog):
    talker.source.session.get.return_value._content = no_abstract
    base = to_metadata(talker.source.get(ID, summary_mode="none"))
    errors = {
        "timeout": requests.Timeout("timeout"),
        "connection": requests.ConnectionError("connection"),
        "transport": requests.RequestException("transport"),
    }
    payloads = {
        "json": b"not JSON",
        "envelope": b"{}",
        "wrong_id": json.dumps({"hit": 1, "list": [{"id": "wrong", "items": []}]}).encode(),
        "item": json.dumps({"hit": 1, "list": [{"id": ID, "items": [None]}]}).encode(),
    }
    talker.source.session.get.reset_mock()
    if failure in errors:
        talker.source.session.get.side_effect = errors[failure]
    else:
        talker.source.session.get.return_value = response(
            payloads.get(failure, b"failure"), int(failure) if failure.isdigit() else 200
        )
    output = talker.fetch_comic_data(issue_id=ID)
    assert asdict(output) == asdict(base)
    assert talker.source.session.get.call_count == 1
    assert not talker.source.cache.get_search_results(ndl.SUMMARY_CACHE, ID)
    assert (
        "Optional NDL summary failed" in caplog.text and ID in caplog.text and DETAIL_ENDPOINT in caplog.text
    )
    assert not (talker.cache_folder / "jpbooks/latest-error.txt").exists()


@pytest.mark.parametrize("error", [AttributeError("bug"), TypeError("bug"), AssertionError("bug")])
def test_internal_parser_errors_are_not_hidden(source, no_abstract, monkeypatch, error):
    source.session.get.return_value._content = no_abstract
    source.get(ID, summary_mode="none")
    source.session.get.return_value = response(b'{"hit": 0, "list": []}')
    monkeypatch.setattr(ndl, "parse_summary", Mock(side_effect=error))
    with pytest.raises(type(error)):
        source.get(ID)


@pytest.mark.parametrize("failure", ["429", "timeout", "xml"])
def test_required_sru_failures_remain_fatal(talker, failure):
    if failure == "timeout":
        talker.source.session.get.side_effect = requests.Timeout()
    else:
        talker.source.session.get.return_value = response(b"invalid XML", 429 if failure == "429" else 200)
    with pytest.raises(TalkerDataError if failure == "xml" else TalkerNetworkError):
        talker.fetch_comic_data(issue_id=ID)
    assert talker.source.session.get.call_count == 1
    assert talker.source.session.get.call_args.args[0] == ndl.ENDPOINT


@pytest.mark.parametrize("header", ["120", "date", "invalid", "9999999999999999999999999999999999999" * 100])
def test_bounded_suppression_honors_retry_after_and_expires(source, no_abstract, monkeypatch, header):
    source.session.get.return_value._content = no_abstract
    source.get(ID, summary_mode="none")
    now = [100.0]
    monkeypatch.setattr(ndl.time, "monotonic", lambda: now[0])
    failure = response(b"failure", 429)
    failure.headers["Retry-After"] = (
        format_datetime(datetime.now(timezone.utc) + timedelta(seconds=120), usegmt=True)
        if header == "date"
        else header
    )
    source.session.get.return_value = failure
    source.session.get.reset_mock()
    source.get(ID)
    source.get(ID)
    assert source.session.get.call_count == 1
    deadline = source._summary_failures[ID]
    assert deadline >= 219 if header in ("date", "120") else deadline == 130
    now[0] = deadline + 1
    source.get(ID)  # A later explicit fetch, never an automatic retry.
    assert source.session.get.call_count == 2
    for index in range(ndl.MAX_SUMMARY_FAILURES + 10):
        source._suppress_summary(str(index), None)
    assert len(source._summary_failures) == ndl.MAX_SUMMARY_FAILURES


def test_failure_suppression_is_not_persistent(source, no_abstract, tmp_path):
    source.session.get.return_value._content = no_abstract
    source.get(ID, summary_mode="none")
    source.session.get.return_value = response(b"failure", 429)
    source.get(ID)
    restarted = ndl.NDLSource(tmp_path)
    try:
        restarted.session.get = Mock(return_value=response(b'{"hit": 0, "list": []}'))
        assert restarted.get(ID).abstracts == []
        assert restarted.session.get.call_count == 1
    finally:
        restarted.session.close()
        restarted.cache.close()


@pytest.mark.parametrize("mode", ["none", "cache"])
def test_explicit_summary_policy_and_invalid_mode(source, no_abstract, mode):
    source.session.get.return_value._content = no_abstract
    source.get(ID, summary_mode=mode)
    assert source.session.get.call_count == 1
    with pytest.raises(ValueError, match="summary mode"):
        source.get(ID, summary_mode="invalid")
