import copy
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from comictalker.comiccacher import Series as CachedSeries
from comictalker.comictalker import RLCallBack, TalkerDataError

from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.sources.ndl import NS, SUMMARY_CACHE, SUMMARY_TIMEOUT, NDLSource, parse_sru
from comictagger_jp_talker.sources.ndl_summary import DETAIL_ENDPOINT, parse_summary

ID = "R100000002-Itest001"


def item(medium, text, identifier="returned-item"):
    return {
        "id": identifier,
        "meta": {
            "k39022": [{"v": medium}],
            "t35200": [{"v": text}],
            "k80404": [{"v": "架空の提供元"}],
            "t35000": [{"v": "媒体注記を混ぜない"}],
        },
    }


@pytest.fixture
def details():
    # Synthetic values, same shape as the documented API's observed response.
    return {
        "hit": 1,
        "list": [{"id": ID, "items": [item("デジタル", "電子版の要約"), item("紙", "紙版の要約・𠮷野")]}],
    }


@pytest.fixture
def no_abstract(xml_bytes):
    root = ET.fromstring(xml_bytes)
    bib = root.find(".//dcndl:BibResource/dcterms:abstract/..", NS)
    bib.remove(bib.find("dcterms:abstract", NS))
    return ET.tostring(root, encoding="utf-8")


def test_paper_first_and_provenance(details):
    summary = parse_summary(details, ID)
    assert summary.texts == ["紙版の要約・𠮷野"]
    assert summary.medium == "紙" and summary.provider == "架空の提供元"


def test_digital_fallback_and_never_related_book(details):
    details["list"][0]["items"] = [item("デジタル", "電子版の要約")]
    details["list"][0]["rels"] = [{"id": "different-book", "meta": {"t35200": [{"v": "他巻"}]}}]
    assert parse_summary(details, ID).texts == ["電子版の要約"]


@pytest.mark.parametrize("items", [[], [item("紙", " ")], [item("不明", "不明な媒体")]])
def test_missing_summary(details, items):
    details["list"][0]["items"] = items
    assert parse_summary(details, ID) is None
    assert parse_summary({"hit": 0, "list": []}, ID) is None


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {"list": []},
        {"list": [{"id": "other", "items": []}]},
        {"list": [{"id": ID, "items": None}]},
        {"list": [{"id": ID, "items": [None]}]},
    ],
)
def test_invalid_envelope(data):
    with pytest.raises(TalkerDataError):
        parse_summary(data, ID)


def test_bad_field_and_multiple_matches(details):
    bad = copy.deepcopy(details)
    bad["list"][0]["items"][0]["meta"]["t35200"] = [{"v": 123}]
    with pytest.raises(TalkerDataError):
        parse_summary(bad, ID)
    details["list"] *= 2
    with pytest.raises(TalkerDataError):
        parse_summary(details, ID)


def test_summary_does_not_contain_catalog_notes(record):
    md = to_metadata(record)
    assert md.description == "\n\n".join(record.abstracts)
    assert record.descriptions[0] in md.notes and record.descriptions[0] not in md.description
    assert to_metadata(replace(record, abstracts=[])).description is None


def test_selected_fetch_enriches_and_caches(source, details, no_abstract, tmp_path):
    source.session.get.return_value._content = no_abstract
    page = source.search(SearchQuery(isbn="488594287X"))
    assert not page.records[0].abstracts
    assert source.session.get.call_count == 1  # Search doesn't enrich every candidate.
    source.session.get.return_value._content = json.dumps(details).encode()
    record = source.get(ID)
    args, kwargs = source.session.get.call_args
    assert args == (DETAIL_ENDPOINT,)
    assert kwargs == {"params": {"cs": "bib", "f-token": ID}, "timeout": SUMMARY_TIMEOUT}
    assert SUMMARY_TIMEOUT == (5, 15)
    assert [call.kwargs["timeout"] for call in source.session.get.call_args_list] == [(5, 60), (5, 15)]
    md = to_metadata(record)
    assert md.description == "紙版の要約・𠮷野"
    assert "架空の提供元 / 紙 / returned-item" in md.notes
    assert record.descriptions == ["内容注記：フィクション"]
    assert source.get(ID).abstracts == record.abstracts
    assert source.session.get.call_count == 2
    restarted = NDLSource(tmp_path)
    try:
        assert restarted.get(ID).abstracts == record.abstracts
    finally:
        restarted.session.close()
        restarted.cache.close()
    # Refreshing the SRU search also refreshes the selected record's summary.
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"), refresh=True)
    details["list"][0]["items"] = [item("紙", "更新された要約")]
    source.session.get.return_value._content = json.dumps(details).encode()
    assert source.get(ID).abstracts == ["更新された要約"]
    assert source.session.get.call_count == 4


def test_sru_abstract_needs_no_extra_request(source):
    source.search(SearchQuery(isbn="488594287X"))
    assert source.get(ID).abstracts
    assert source.session.get.call_count == 1


def test_empty_summary_cached(source, no_abstract):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.return_value._content = json.dumps(
        {"hit": 1, "list": [{"id": ID, "items": []}]}
    ).encode()
    assert source.get(ID).abstracts == []
    assert source.get(ID).abstracts == []
    assert source.session.get.call_count == 2


@pytest.mark.parametrize("payload", [b"not JSON", b"\xff", b"{}"])
def test_invalid_json_not_cached(source, no_abstract, payload, caplog):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.return_value._content = payload
    assert source.get(ID).abstracts == []
    assert "Optional NDL summary failed" in caplog.text
    assert not source.cache.get_search_results("jpbooks.ndl.summary.v1", ID)


@pytest.mark.parametrize("error", [requests.Timeout(), requests.ReadTimeout(), requests.ConnectTimeout()])
def test_summary_timeout_retains_base_record(source, no_abstract, monkeypatch, caplog, error):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    original = source.get(ID, summary_mode="none")
    now = [100.0]
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def timeout(*args, **kwargs):
        now[0] += 15.02
        raise error

    source.session.get.side_effect = timeout
    with caplog.at_level(logging.DEBUG, logger=ndl.__name__):
        assert asdict(source.get(ID)) == asdict(original)
        assert asdict(source.get(ID)) == asdict(original)  # Suppressed, with no automatic retry.
    assert asdict(source.get(ID, summary_mode="none")) == asdict(original)
    assert source.session.get.call_count == 2  # Initial SRU and one failed Summary request.
    assert source.session.get.call_args.kwargs["timeout"] == (5, 15)
    assert not source.cache.get_search_results(SUMMARY_CACHE, ID)
    assert source._summary_failures[ID] == now[0] + ndl.SUMMARY_FAILURE_COOLDOWN
    assert caplog.messages[0] == (
        f"NDL Summary request failed: status=None error={type(error).__name__} elapsed=15.02s timeout=(5,15)"
    )
    assert len(caplog.records) == 2
    assert caplog.records[0].levelno == logging.DEBUG
    assert caplog.records[1].levelno == logging.WARNING
    assert "Optional NDL summary failed" in caplog.messages[1]


def test_summary_success_timing(source, no_abstract, details, monkeypatch, caplog):
    source.session.get.return_value._content = no_abstract
    source.get(ID, summary_mode="none")
    source.session.get.return_value._content = json.dumps(details).encode()
    now = [100.0]
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def get(*args, **kwargs):
        now[0] += 1.25
        return source.session.get.return_value

    source.session.get.side_effect = get
    with caplog.at_level(logging.DEBUG, logger=ndl.__name__):
        assert source.get(ID).abstracts == ["紙版の要約・𠮷野"]
        assert source.get(ID).abstracts == ["紙版の要約・𠮷野"]
    assert caplog.messages == ["NDL Summary request completed: status=200 elapsed=1.25s timeout=(5,15)"]
    assert source.session.get.call_count == 2


def response(content=b"", status=200):
    result = requests.Response()
    result.status_code = status
    result._content = content
    return result


def summary_cache_rows(source):
    return [
        tuple(row)
        for table in ("SeriesSearchCache", "Series")
        for row in source.cache.connect().execute(f"SELECT * FROM {table} WHERE source = ?", (SUMMARY_CACHE,))
    ]


@pytest.fixture
def refreshing_summary(source, no_abstract, details, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))
    query = SearchQuery(isbn="488594287X")
    source.session.get.return_value._content = no_abstract
    source.search(query)
    content = json.dumps(details).encode()
    source.session.get.return_value._content = content
    original = source.get(ID)
    assert original.abstracts == ["紙版の要約・𠮷野"]
    # A changed timestamp detects accidental renewal of either cache layer's TTL.
    with source.cache.connect() as db:
        for table in ("SeriesSearchCache", "Series"):
            db.execute(
                f"UPDATE {table} SET timestamp = ? WHERE source = ?",
                (str(datetime.now() - timedelta(days=1)), SUMMARY_CACHE),
            )
    source.session.get.return_value._content = no_abstract
    source.search(query, refresh=True)
    source.session.get.reset_mock()
    return SimpleNamespace(now=now, original=original, content=content)


@pytest.mark.parametrize(
    "failure",
    ["429", "503", "read_timeout", "connect_timeout", "connection", "json", "encoding", "structure", "id"],
)
def test_failed_summary_refresh_returns_valid_cache_and_preserves_pending(
    source, refreshing_summary, failure, monkeypatch
):
    original = refreshing_summary.original
    cached_rows = summary_cache_rows(source)
    write = Mock(wraps=source.cache.add_search_results)
    monkeypatch.setattr(source.cache, "add_search_results", write)
    failures = {
        "read_timeout": requests.ReadTimeout(),
        "connect_timeout": requests.ConnectTimeout(),
        "connection": requests.ConnectionError(),
    }
    payloads = {
        "json": b"not JSON",
        "encoding": b"\xff",
        "structure": b"{}",
        "id": b'{"hit":1,"list":[{"id":"another-book","items":[]}]}',
    }
    if failure in failures:
        source.session.get.side_effect = failures[failure]
    else:
        source.session.get.return_value = response(
            payloads.get(failure, b"failure"), int(failure) if failure.isdigit() else 200
        )
    # Pending refresh doesn't prevent candidate-only reads of the valid old text.
    assert source.get(ID, summary_mode="cache") == original
    source.session.get.assert_not_called()
    assert source.get(ID) == original
    assert source.session.get.call_count == 1
    deadline = source._summary_failures[ID]
    assert deadline == 130.0
    for now in (100.0, 129.999):
        refreshing_summary.now[0] = now
        for mode in ("cache", "fetch"):
            assert asdict(source.get(ID, summary_mode=mode)) == asdict(original)
            assert ID in source._refresh_summaries
            assert source._summary_failures[ID] == deadline
    assert source.session.get.call_count == 1
    write.assert_not_called()
    assert summary_cache_rows(source) == cached_rows


@pytest.mark.parametrize("now", [130.0, 130.001])
@pytest.mark.parametrize("result", ["present", "absent_items", "absent_hit"])
def test_later_explicit_fetch_replaces_fallback_and_clears_pending(
    source, refreshing_summary, details, result, now
):
    source.session.get.side_effect = requests.ReadTimeout()
    assert source.get(ID) == refreshing_summary.original
    refreshing_summary.now[0] = now
    assert source.get(ID, summary_mode="cache") == refreshing_summary.original
    assert source.session.get.call_count == 1 and ID in source._refresh_summaries
    details["list"][0]["items"] = [item("デジタル", "更新された要約", "new-item")]
    payload = (
        details
        if result == "present"
        else {"hit": 1, "list": [{"id": ID, "items": []}]}
        if result == "absent_items"
        else {"hit": 0, "list": []}
    )
    content = json.dumps(payload).encode()
    source.session.get.side_effect = None
    source.session.get.return_value = response(content)
    output = source.get(ID)
    assert output.abstracts == (["更新された要約"] if result == "present" else [])
    assert output.summary_item_id == ("new-item" if result == "present" else "")
    assert to_metadata(output).description == ("更新された要約" if result == "present" else None)
    assert ID not in source._refresh_summaries and ID not in source._summary_failures
    assert source.cache.get_search_results(SUMMARY_CACHE, ID)[0].data.data == content
    assert source.get(ID) == output
    assert source.get(ID, summary_mode="cache") == output
    assert source.session.get.call_count == 2


@pytest.mark.parametrize("mode", ["cache", "fetch"])
@pytest.mark.parametrize(
    "cache", ["miss", "expired", "json", "encoding", "structure", "wrong_id", "bad_item", "absent", "medium"]
)
def test_refresh_does_not_adopt_unusable_old_summary(source, no_abstract, details, cache, mode):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"), refresh=True)
    base = source.get(ID, summary_mode="none")
    payloads = {
        "json": b"not JSON",
        "encoding": b"\xff",
        "structure": b"{}",
        "wrong_id": b'{"hit":1,"list":[{"id":"other-book","items":[]}]}',
        "bad_item": json.dumps({"list": [{"id": ID, "items": [None]}]}).encode(),
        "absent": b'{"hit":0,"list":[]}',
        "medium": json.dumps({"list": [{"id": ID, "items": [item("対象外", "採用禁止")]}]}).encode(),
    }
    if cache != "miss":
        source.cache.add_search_results(
            SUMMARY_CACHE, ID, [CachedSeries(ID, payloads.get(cache, json.dumps(details).encode()))], True
        )
    if cache == "expired":
        with source.cache.connect() as db:
            db.execute(
                "UPDATE SeriesSearchCache SET timestamp = ? WHERE source = ?",
                (str(datetime.now() - timedelta(days=8)), SUMMARY_CACHE),
            )
    source.session.get.reset_mock()
    source.session.get.return_value = response(status=429)
    assert asdict(source.get(ID, summary_mode=mode)) == asdict(base)
    assert source.session.get.call_count == (1 if mode == "fetch" else 0)
    assert ID in source._refresh_summaries
    if mode == "fetch":
        assert source._summary_failures[ID] > 0
        assert source.get(ID) == base and source.session.get.call_count == 1


@pytest.mark.parametrize("mode", ["cache", "fetch"])
@pytest.mark.parametrize(
    "payload",
    [b"not JSON", b"\xff", b"{}", b'{"list":[{"id":"another-book","items":[]}]}'],
)
def test_invalid_cache_without_pending_refresh_never_fetches(source, no_abstract, mode, payload):
    source.session.get.return_value = response(no_abstract)
    source.search(SearchQuery(isbn="488594287X"))
    base = source.get(ID, summary_mode="none")
    source.cache.add_search_results(SUMMARY_CACHE, ID, [CachedSeries(ID, payload)], True)
    source.session.get.reset_mock()
    source.session.get.side_effect = AssertionError("Invalid cache must not trigger HTTP")
    for _ in range(2):
        assert source.get(ID, summary_mode=mode) == base
    source.session.get.assert_not_called()
    assert ID not in source._refresh_summaries and ID not in source._summary_failures
    assert source.cache.get_search_results(SUMMARY_CACHE, ID)[0].data.data == payload


def test_invalid_cache_explicit_refresh_429_is_suppressed_then_recovers(
    source, no_abstract, details, monkeypatch
):
    now = [100.0]
    monkeypatch.setattr(ndl, "time", SimpleNamespace(monotonic=lambda: now[0]))
    source.session.get.return_value = response(no_abstract)
    query = SearchQuery(isbn="488594287X")
    source.search(query)
    base = source.get(ID, summary_mode="none")
    source.cache.add_search_results(SUMMARY_CACHE, ID, [CachedSeries(ID, b"broken")], True)
    source.search(query, refresh=True)
    source.session.get.reset_mock()
    source.session.get.return_value = response(status=429)
    assert source.get(ID) == base
    assert source.session.get.call_count == 1
    for mode in ("cache", "fetch"):
        assert source.get(ID, summary_mode=mode) == base
    assert source.session.get.call_count == 1
    assert ID in source._refresh_summaries and source._summary_failures[ID] == 130.0
    now[0] = 130.0
    source.session.get.return_value = response(json.dumps(details).encode())
    assert source.get(ID).abstracts == ["紙版の要約・𠮷野"]
    assert source.session.get.call_count == 2
    assert ID not in source._refresh_summaries and ID not in source._summary_failures


def test_fallback_expires_during_suppression(source, refreshing_summary):
    source.session.get.return_value = response(status=429)
    assert source.get(ID) == refreshing_summary.original
    # Only this test's temporary DB is modified; production expiration is unchanged.
    with source.cache.connect() as db:
        db.execute(
            "UPDATE SeriesSearchCache SET timestamp = ? WHERE source = ?",
            (str(datetime.now() - timedelta(days=8)), SUMMARY_CACHE),
        )
    for mode in ("cache", "fetch"):
        assert not source.get(ID, summary_mode=mode).abstracts
    assert source.session.get.call_count == 1 and ID in source._refresh_summaries


def test_recreated_plugin_uses_preserved_summary_cache(source, refreshing_summary, tmp_path, monkeypatch):
    from comictagger_jp_talker.talker import JapaneseBooksTalker

    source.session.get.return_value = response(status=429)
    assert source.get(ID) == refreshing_summary.original
    cached_rows = summary_cache_rows(source)
    restarted = JapaneseBooksTalker("1.6.0b9", tmp_path)
    monkeypatch.setattr(restarted.source.session, "get", Mock(side_effect=AssertionError("Unexpected HTTP")))
    try:
        assert restarted.fetch_comic_data(issue_id=ID).description == "紙版の要約・𠮷野"
        restarted.source.session.get.assert_not_called()
        assert summary_cache_rows(restarted.source) == cached_rows
    finally:
        restarted.source.session.close()
        restarted.source.cache.close()


def test_sru_abstract_still_wins_over_pending_fallback(source, refreshing_summary, xml_bytes):
    source.session.get.return_value = response(xml_bytes)
    source.search(SearchQuery(isbn="488594287X"), refresh=True)
    source.session.get.reset_mock()
    expected = source.get(ID, summary_mode="none")
    assert source.get(ID) == expected
    source.session.get.assert_not_called()


def test_summary_uses_shared_rate_limiter(source, no_abstract, details, monkeypatch):
    import contextlib

    from comictagger_jp_talker.sources import ndl

    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.return_value._content = json.dumps(details).encode()
    limiter = Mock(return_value=contextlib.nullcontext())
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    callback = RLCallBack(lambda a, b: None, 1)
    source.get(ID, on_rate_limit=callback)
    limiter.assert_called_once_with("ndlsearch", delay=True, on_rate_limit=callback)
    assert source.session.get.call_args.kwargs["timeout"] == (5, 15)


def test_record_abstract_and_notes_are_separate(xml_bytes):
    record = parse_sru(xml_bytes).records[0]
    assert record.abstracts == ["テスト用あらすじ。漢字・ひらがな・カタカナ。"]
    assert record.descriptions == ["内容注記：フィクション"]
