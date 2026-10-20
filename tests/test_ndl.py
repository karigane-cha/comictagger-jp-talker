from __future__ import annotations

import contextlib
import logging
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from comictalker.comictalker import RLCallBack, TalkerDataError, TalkerNetworkError

from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.sources.ndl import (
    ENDPOINT,
    RECORD_CACHE,
    SRU_TIMEOUT,
    NDLSource,
    build_cql,
    cql_quote,
    ndl_record_url,
    parse_sru,
    rank_records,
)

EMPTY = b'<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/"><numberOfRecords>0</numberOfRecords></searchRetrieveResponse>'
DIAGNOSTIC = b"""<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
<diagnostics><diagnostic xmlns="http://www.loc.gov/zing/srw/diagnostic/">
<uri>info:srw/diagnostic/1/10</uri><message>Bad query</message></diagnostic></diagnostics>
</searchRetrieveResponse>"""
NO_MATCH = DIAGNOSTIC.replace(b"diagnostic/1/10", b"diagnostic/1/1").replace(
    b"Bad query", b"Record does not exist"
)


@pytest.mark.parametrize("message", [b"Record does not exist", b"Record does not exit"])
@pytest.mark.parametrize("count", [b"", b"<numberOfRecords>0</numberOfRecords>"])
def test_no_match_diagnostic(message, count):
    data = NO_MATCH.replace(b"Record does not exist", message).replace(
        b"<diagnostics>", count + b"<diagnostics>"
    )
    page = parse_sru(data)
    assert page.total == 0 and page.records == []


@pytest.mark.parametrize(
    "data",
    [
        NO_MATCH.replace(b"Record does not exist", b"System error"),
        NO_MATCH.replace(b"diagnostic/1/1", b"diagnostic/1/10"),
        NO_MATCH.replace(b"<diagnostics>", b"<numberOfRecords>1</numberOfRecords><diagnostics>"),
        NO_MATCH.replace(b"<diagnostics>", b"<numberOfRecords>bad</numberOfRecords><diagnostics>"),
        NO_MATCH.replace(b"<diagnostics>", b"<records><record/></records><diagnostics>"),
        NO_MATCH.replace(
            b"</diagnostics>",
            b'<diagnostic xmlns="http://www.loc.gov/zing/srw/diagnostic/">'
            b"<uri>info:srw/diagnostic/1/1</uri><message>System error</message></diagnostic></diagnostics>",
        ),
    ],
)
def test_other_or_conflicting_diagnostics_still_raise(data):
    with pytest.raises(TalkerDataError, match="SRU diagnostics"):
        parse_sru(data)


def test_no_match_diagnostic_cached(source):
    source.session.get.return_value._content = NO_MATCH
    for _ in range(2):
        assert source.search(SearchQuery(isbn="9784088528113", mediatype="")).records == []
    assert source.session.get.call_count == 1


def test_cql():
    assert build_cql(SearchQuery(isbn="4-88594-287-X", mediatype="")) == 'isbn = "488594287X"'
    assert build_cql(SearchQuery(title="3月のライオン", creator="羽海野", publisher="白泉社")) == (
        'title = "3月のライオン" AND creator = "羽海野" AND publisher = "白泉社" AND mediatype = "books"'
    )
    assert 'title = "74"' in build_cql(SearchQuery(title="キングダム", issue="74"))
    assert 'from = "2024" AND until = "2025"' in build_cql(
        SearchQuery(title="漫画", from_date="2024", until_date="2025")
    )
    assert cql_quote('a" OR title="*?^\\') == '"a\\" OR title=\\"\\*\\?\\^\\\\"'
    with pytest.raises(TalkerDataError):
        build_cql(SearchQuery(isbn="invalid"))
    with pytest.raises(TalkerDataError):
        build_cql(SearchQuery())


@pytest.mark.parametrize(
    "order,suffix",
    [
        ("title", ""),
        ("oldest", " AND sortBy=issued_date/sort.ascending"),
        ("newest", " AND sortBy=issued_date/sort.descending"),
    ],
)
def test_title_sort_query(order, suffix):
    assert build_cql(SearchQuery(title="漫画", sort_order=order)) == (
        'title = "漫画" AND mediatype = "books"' + suffix
    )
    assert "sortBy" not in build_cql(SearchQuery(isbn="488594287X", title="漫画", sort_order=order))
    assert "sortBy" not in build_cql(SearchQuery(itemno="returned-id", title="漫画", sort_order=order))


def test_sort_query_injection_rejected():
    with pytest.raises(TalkerDataError):
        build_cql(SearchQuery(title="漫画", sort_order='oldest OR title="*"'))


def test_search_order_has_separate_cache(source):
    source.search(SearchQuery(title="漫画", sort_order="title"))
    source.search(SearchQuery(title="漫画", sort_order="oldest"))
    assert source.session.get.call_count == 2
    source.search(SearchQuery(title="漫画", sort_order="oldest"))
    assert source.session.get.call_count == 2


@pytest.mark.parametrize("value", ["\ud800", "\x00", "abc\n"])
def test_invalid_search_unicode(value):
    with pytest.raises(TalkerDataError, match="サロゲート"):
        cql_quote(value)


def test_namespace_and_real_response_shape(xml_bytes):
    page = parse_sru(xml_bytes)
    assert page.total == 1 and len(page.records) == 1 and not page.truncated
    record = page.records[0]
    assert record.title == "架空の漫画・髙﨑𠮷野〜旅―（新版）. ７４"
    assert record.publishers == ["架空出版"]
    assert record.subjects == ["漫画"]
    assert len(record.ndc) == 2 and len(record.classifications) == 1
    assert record.isbns == ["4-88594-287-X"]
    assert record.providers == ["R100000002"]
    assert "BibResource" in record.raw_xml
    # Namespace aliases may change. Namespace URIs, not prefix strings, define meaning.
    assert (
        parse_sru(xml_bytes.replace(b"dcterms:", b"t:").replace(b"xmlns:dcterms", b"xmlns:t")).records[0]
        == record
    )


def test_wrong_namespace_not_accepted(xml_bytes):
    with pytest.raises(TalkerDataError):
        parse_sru(xml_bytes.replace(b"http://purl.org/dc/terms/", b"https://unrelated.example/terms/"))


def test_empty():
    assert parse_sru(EMPTY).records == []


@pytest.mark.parametrize(
    "data,description",
    [
        (DIAGNOSTIC, "SRU diagnostics"),
        (b"", "Invalid XML"),
        (b"<broken", "Invalid XML"),
        (b"<html/>", "Unsupported metadata"),
        (EMPTY.replace(b">0<", b">bad<"), "Malformed response"),
    ],
)
def test_bad_response(data, description):
    with pytest.raises(TalkerDataError, match=description):
        parse_sru(data)


def test_malformed_and_unsupported(xml_bytes):
    with pytest.raises(TalkerDataError, match="Malformed record"):
        parse_sru(xml_bytes.replace(b"dcterms:title", b"dcterms:other"))
    with pytest.raises(TalkerDataError, match="Unsupported metadata"):
        parse_sru(xml_bytes.replace(b"rdf:RDF", b"rdf:Other"))


def test_mixed_valid_and_bad_records(xml_bytes):
    data = xml_bytes.replace(b"</records>", b"<record><recordData/></record></records>").replace(
        b"<numberOfRecords>1", b"<numberOfRecords>2"
    )
    page = parse_sru(data)
    assert len(page.records) == 1 and len(page.warnings) == 1
    assert not page.truncated


@pytest.mark.parametrize(
    "url",
    [
        "http://ndlsearch.ndl.go.jp/books/R1-I1",
        "https://example.com/books/R1-I1",
        "https://ndlsearch.ndl.go.jp.evil.test/books/R1-I1",
        "https://ndlsearch.ndl.go.jp/books/a?x=y",
        "https://ndlsearch.ndl.go.jp/books/a/b",
    ],
)
def test_no_invented_url(url):
    assert ndl_record_url(url) is None


def test_url():
    assert ndl_record_url("https://ndlsearch.ndl.go.jp/books/R100000002-I123#material") == (
        "R100000002-I123",
        "https://ndlsearch.ndl.go.jp/books/R100000002-I123",
    )


def test_http_and_cache(source, tmp_path):
    page = source.search(SearchQuery(isbn="488594287X", mediatype=""))
    args, kwargs = source.session.get.call_args
    assert args == (ENDPOINT,)
    assert kwargs["timeout"] == SRU_TIMEOUT == (5, 60)
    assert kwargs["params"]["recordSchema"] == "dcndl_v3"
    assert kwargs["params"]["recordPacking"] == "xml"
    assert kwargs["params"]["version"] == "1.2"
    assert "488594287X" in kwargs["params"]["query"]
    source.search(SearchQuery(isbn="488594287X", mediatype=""))
    assert source.session.get.call_count == 1
    assert source.get(page.records[0].id).title == page.records[0].title
    restarted = NDLSource(tmp_path)
    try:
        assert restarted.get(page.records[0].id).id == page.records[0].id
        assert restarted.search(SearchQuery(isbn="488594287X", mediatype="")).total == 1
    finally:
        restarted.cache.close()
        restarted.session.close()
    source.search(SearchQuery(isbn="488594287X", mediatype=""), refresh=True)
    assert source.session.get.call_count == 2


def test_empty_cached(source):
    source.session.get.return_value._content = EMPTY
    source.search(SearchQuery(title="存在しない"))
    source.search(SearchQuery(title="存在しない"))
    assert source.session.get.call_count == 1


@pytest.mark.parametrize(
    "error,code,label",
    [
        (requests.Timeout(), 4, "timed out"),
        (requests.ReadTimeout(), 4, "timed out"),
        (requests.ConnectTimeout(), 4, "timed out"),
        (requests.ConnectionError(), 1, "Connection error"),
        (requests.RequestException(), 0, "Request error"),
    ],
)
def test_network_errors(source, monkeypatch, error, code, label):
    cache_write = Mock(wraps=source.cache.add_search_results)
    monkeypatch.setattr(source.cache, "add_search_results", cache_write)
    source.session.get.side_effect = error
    with pytest.raises(TalkerNetworkError, match=label) as caught:
        source.search(SearchQuery(title="漫画"))
    assert caught.value.sub_code == code
    assert caught.value.__cause__ is error
    assert source.session.get.call_count == 1
    cache_write.assert_not_called()


@pytest.mark.parametrize("status,subcode", [(500, 0), (429, 3), (403, 0)])
def test_http_error(source, monkeypatch, caplog, status, subcode):
    clock = Mock(side_effect=[100.0, 102.43])
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=clock))
    cache_write = Mock(wraps=source.cache.add_search_results)
    monkeypatch.setattr(source.cache, "add_search_results", cache_write)
    source.session.get.return_value.status_code = status
    with (
        caplog.at_level(logging.DEBUG, logger=ndl.__name__),
        pytest.raises(TalkerNetworkError, match=f"HTTP error: {status}") as caught,
    ):
        source.search(SearchQuery(title="漫画"))
    assert caught.value.sub_code == subcode
    assert isinstance(caught.value.__cause__, requests.HTTPError)
    assert source.session.get.call_count == 1
    cache_write.assert_not_called()
    assert (
        f"NDL SRU request failed: status={status} error=HTTPError elapsed=2.43s timeout=(5,60)"
        in caplog.messages
    )


def test_check_status_uses_sru_timeout_without_search_cache(source):
    source.search(SearchQuery(isbn="488594287X", mediatype=""))
    source.check_status()
    source.check_status()
    assert source.session.get.call_count == 3
    assert all(call.args == (ENDPOINT,) for call in source.session.get.call_args_list)
    assert all(call.kwargs["timeout"] == (5, 60) for call in source.session.get.call_args_list)


def test_request_timing_excludes_limiter_waits(source, monkeypatch, caplog):
    now = [100.0]
    clock = Mock(side_effect=lambda: now[0])
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=clock))

    @contextlib.contextmanager
    def limiter(*args, **kwargs):
        now[0] += 20
        yield
        now[0] += 10

    def get(*args, **kwargs):
        now[0] += 2.43
        return source.session.get.return_value

    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    source.session.get.side_effect = get
    query = SearchQuery(title="private-query")
    with caplog.at_level(logging.DEBUG, logger=ndl.__name__):
        source.search(query)
        source.search(query)  # Cache hits produce neither HTTP requests nor timing logs.
    messages = [r for r in caplog.records if r.name == ndl.__name__]
    assert len(messages) == 1
    assert messages[0].levelno == logging.DEBUG
    assert messages[0].getMessage() == ("NDL SRU request completed: status=200 elapsed=2.43s timeout=(5,60)")
    assert "private-query" not in caplog.text
    assert clock.call_count == 2
    assert source.session.get.call_count == 1


@pytest.mark.parametrize(
    "error,subcode,status",
    [
        (requests.ReadTimeout("private-error"), 4, None),
        (requests.ConnectTimeout("private-error"), 4, None),
        (requests.ConnectionError("private-error"), 1, None),
        (requests.RequestException("private-error"), 0, None),
        (requests.HTTPError("private-error"), 0, None),
        (requests.HTTPError("private-error", response=requests.Response()), 0, 500),
        (requests.HTTPError("private-error", response=requests.Response()), 3, 429),
    ],
)
def test_failed_request_diagnostics_preserve_exception(source, monkeypatch, caplog, error, subcode, status):
    if error.response is not None:
        error.response.status_code = status
    clock = Mock(side_effect=[100.0, 160.04])
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=clock))
    source.session.get.side_effect = error
    with caplog.at_level(logging.DEBUG, logger=ndl.__name__), pytest.raises(TalkerNetworkError) as caught:
        source.search(SearchQuery(title="private-query"))
    assert caught.value.sub_code == subcode
    assert caught.value.__cause__ is error
    assert clock.call_count == 2
    assert source.session.get.call_count == 1  # No automatic retry, including on 429.
    assert caplog.messages == [
        f"NDL SRU request failed: status={status} error={type(error).__name__} elapsed=60.04s timeout=(5,60)"
    ]
    assert "private-query" not in caplog.text and "private-error" not in caplog.text


@pytest.mark.parametrize("failure", ["timeout", "http"])
def test_failed_refresh_keeps_successful_search_and_record_cache(source, failure):
    query = SearchQuery(title="漫画")
    original = source.search(query)
    original_record = source.get(original.records[0].id, summary_mode="none")
    cached_xml = source.cache.get_series_info(original_record.id, RECORD_CACHE).data.data
    if failure == "timeout":
        source.session.get.side_effect = requests.ReadTimeout()
    else:
        source.session.get.return_value.status_code = 500
    with pytest.raises(TalkerNetworkError):
        source.search(query, refresh=True)
    assert source.search(query) == original
    assert source.get(original_record.id, summary_mode="none") == original_record
    assert source.cache.get_series_info(original_record.id, RECORD_CACHE).data.data == cached_xml
    assert source.session.get.call_count == 2


def test_rate_limit_callback_passed(source, monkeypatch):
    from comictagger_jp_talker.sources import ndl

    limiter = Mock(return_value=contextlib.nullcontext())
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    callback = RLCallBack(lambda a, b: None, 1)
    source.search(SearchQuery(title="漫画"), on_rate_limit=callback)
    assert limiter.call_args.kwargs == {"delay": True, "on_rate_limit": callback}
    source.search(SearchQuery(title="漫画"), on_rate_limit=callback)
    assert limiter.call_count == 1  # Cache hits never enter the network limiter.


def test_ranking_and_editions(record):
    other = replace(record, id="other", providers=["R100000136"])
    different = replace(record, id="another-isbn", isbns=["9784101010137"])
    digital = replace(other, id="digital", material_types=["電子資料"])
    ranked = rank_records([other, different, digital, record, record], "488594287X")
    assert ranked[0].id == record.id
    assert len(ranked) == 4  # Same ISBN and electronic records remain independently selectable.
    assert ranked[-1].id == "another-isbn"


def test_get_unknown_id_does_not_choose_first(source):
    with pytest.raises(TalkerDataError, match="見つかりません"):
        source.get("different-id")
