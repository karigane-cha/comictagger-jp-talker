import inspect
from dataclasses import replace
from unittest.mock import Mock

import pytest
import settngs
from comicapi.genericmetadata import Credit, GenericMetadata
from comictaggerlib.ctsettings.plugin import register_talker_settings
from comictalker.comictalker import ComicTalker, TalkerDataError

from comictagger_jp_talker.models import SearchPage
from comictagger_jp_talker.talker import JapaneseBooksTalker


def test_host_signatures():
    for name in (
        "search_for_series",
        "fetch_comic_data",
        "fetch_series",
        "fetch_issues_in_series",
        "fetch_issues_by_series_issue_num_and_year",
        "check_status",
        "register_settings",
        "parse_settings",
    ):
        expected = inspect.signature(getattr(ComicTalker, name))
        actual = inspect.signature(getattr(JapaneseBooksTalker, name))
        assert list(actual.parameters) == list(expected.parameters)
        for key, param in expected.parameters.items():
            assert actual.parameters[key].kind == param.kind
            assert actual.parameters[key].default == param.default


@pytest.mark.parametrize("term", ["488594287X", "4-88594-287-X", "9784885942877", "ISBN: 488594287X"])
def test_isbn_search(talker, term):
    result = talker.search_for_series(term)
    assert len(result) == 1
    assert 'isbn = "' in talker.source.session.get.call_args.kwargs["params"]["query"]
    assert "mediatype" not in talker.source.session.get.call_args.kwargs["params"]["query"]


@pytest.mark.parametrize("term", ["4-08-852811-5", "9784088528113"])
def test_reported_isbn_no_matches(talker, term):
    from test_ndl import NO_MATCH

    talker.source.session.get.return_value._content = NO_MATCH
    assert talker.search_for_series(term) == []


def test_title_fallback_after_no_match_diagnostic(talker, xml_bytes):
    import requests
    from test_ndl import NO_MATCH

    responses = []
    for content in (NO_MATCH, xml_bytes):
        response = requests.Response()
        response.status_code = 200
        response._content = content
        responses.append(response)
    talker.source.session.get.side_effect = responses
    assert len(talker.search_for_series("漫画 74")) == 1
    queries = [c.kwargs["params"]["query"] for c in talker.source.session.get.call_args_list]
    assert len(queries) == 2
    assert 'title = "74"' in queries[0] and 'title = "74"' not in queries[1]


def test_title_candidates(talker, record):
    talker._source = Mock()
    talker._source.search.return_value = SearchPage(
        [record, replace(record, id="edition2")], 300, truncated=True
    )
    candidates = talker.search_for_series("架空の漫画")
    assert len(candidates) == 2
    assert "300" in candidates[0].description
    assert "ISBN" in candidates[0].description and "Author" in candidates[0].description


def test_default_title_order_and_settings(talker):
    query = talker._query("こちら葛飾区亀有公園前派出所")
    assert query.title == "こちら葛飾区亀有公園前派出所"
    assert query.sort_order == "oldest"
    talker.search_for_series(query.title)
    assert talker.source.session.get.call_args.kwargs["params"]["query"].endswith(
        " AND sortBy=issued_date/sort.ascending"
    )
    talker.parse_settings({"jpbooks_search_order": "newest"})
    assert talker._query("作品 74").sort_order == "newest"
    assert talker._query("作品 74", literal=True).sort_order == "newest"
    assert talker._query("488594287X").sort_order == "title"
    assert talker.check_status({"jpbooks_search_order": "unexpected"})[1] is False


def test_fallback_keeps_search_order(talker):
    talker._source = Mock()
    talker._source.search.return_value = SearchPage([], 0)
    talker.creator = "作者"
    talker.search_for_series("漫画 74")
    assert len(talker.source.search.call_args_list) == 4
    assert all(call.args[0].sort_order == "oldest" for call in talker.source.search.call_args_list)


def test_standard_issue_flow(talker):
    series = talker.search_for_series("漫画")[0]
    assert not series.aliases
    assert "NDL シリーズ表記（原データ）: 架空の漫画" in series.description
    assert talker.fetch_series(series.id).id == series.id
    issues = talker.fetch_issues_in_series(series.id)
    assert len(issues) == 1
    assert issues[0].series == "架空の漫画・髙﨑𠮷野〜旅―（新版）"
    assert talker.fetch_comic_data(issue_id=issues[0].issue_id).series == issues[0].series
    assert talker.fetch_comic_data(issue_id=issues[0].issue_id).gtin == "9784885942877"
    assert talker.fetch_comic_data(series_id=series.id, issue_number="74").issue == "74"
    with pytest.raises(TalkerDataError):
        talker.fetch_comic_data(series_id=series.id, issue_number="75")
    assert talker.fetch_issues_by_series_issue_num_and_year([series.id], "74", 2025)
    assert not talker.fetch_issues_by_series_issue_num_and_year([series.id], "73", 2025)
    assert not talker.fetch_issues_by_series_issue_num_and_year([series.id], "74", 2024)
    assert talker.source.session.get.call_count == 1


@pytest.mark.parametrize("volume_output", ["issue", "volume", "both"])
@pytest.mark.parametrize("raw", [[], ["1 (国王誕生の巻)"], ["1", "第１巻（国王誕生の巻）"]])
def test_subtitle_candidate_fetch(talker, record, volume_output, raw):
    title = "パタリロ! : 選集. 1 (国王誕生の巻)"
    record = replace(record, title=title, volumes=raw.copy())
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    talker.source.get.return_value = record
    talker.volume_output = volume_output
    candidate = talker.search_for_series(title)[0]
    assert talker.source.search.call_args.args[0].title == "パタリロ! : 選集"
    assert talker.source.search.call_args.args[0].issue == "1"
    issue = talker.fetch_issues_in_series(candidate.id)[0]
    md = talker.fetch_comic_data(issue_id=issue.issue_id)
    assert md.series == "パタリロ! : 選集"
    assert md.title == record.title == title
    assert record.volumes == raw
    assert "巻番号の不一致" not in md.notes
    assert md.issue == ("1" if volume_output in ("issue", "both") else None)
    assert md.volume == (1 if volume_output in ("volume", "both") else None)
    assert talker.fetch_issues_by_series_issue_num_and_year([candidate.id], "1", None)
    with pytest.raises(TalkerDataError):
        talker.fetch_comic_data(series_id=candidate.id, issue_number="2")


def test_search_priority_helper(talker, record):
    talker._source = Mock()
    talker._source.search.return_value = SearchPage([record], 1)
    md = GenericMetadata(gtin="9784885942877", series="漫画", issue="74", credits=[Credit("作者", "Writer")])
    talker.search_metadata(md)
    assert talker.source.search.call_args.args[0].isbn == "9784885942877"
    talker.source.search.reset_mock()
    talker.source.search.side_effect = [
        SearchPage([], 0), SearchPage([], 0), SearchPage([], 0), SearchPage([record], 1)
    ]
    md.gtin = None
    talker.search_metadata(md)
    queries = [c.args[0] for c in talker.source.search.call_args_list]
    assert [(q.issue, q.creator) for q in queries] == [
        ("74", "作者"), ("74", ""), ("", "作者"), ("", "")
    ]


def test_literal_and_validation(talker):
    talker.search_for_series("作品 74", literal=True)
    assert 'title = "作品 74"' in talker.source.session.get.call_args.kwargs["params"]["query"]
    for term in ("ISBN: invalid", "9784101010138", ""):
        with pytest.raises(TalkerDataError):
            talker.search_for_series(term)


def test_settings(talker):
    manager = settngs.Manager()
    register_talker_settings(manager, {talker.id: talker})
    definitions = manager.definitions["Source jpbooks"].v
    assert definitions["jpbooks_key"].file is False
    assert definitions["jpbooks_key"].cmdline is False
    assert definitions["jpbooks_url"].file is False
    talker.parse_settings({"jpbooks_mediatype": "online", "jpbooks_maximum_records": 10})
    assert talker.mediatype == "online" and talker.maximum_records == 10
    assert talker.api_key == ""
    for settings in (
        {"jpbooks_key": "key"},
        {"jpbooks_url": "http://evil.test"},
        {"jpbooks_maximum_records": 0},
        {"jpbooks_mediatype": "wrong"},
    ):
        assert talker.check_status(settings)[1] is False


def test_status_uncached(talker, monkeypatch, xml_bytes):
    import requests

    response = requests.Response()
    response.status_code = 200
    response._content = xml_bytes
    get = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "get", get)
    original = talker.mediatype
    assert talker.check_status({"jpbooks_mediatype": "online"})[1]
    assert talker.check_status({})[1]
    assert get.call_count == 2
    assert talker.mediatype == original
