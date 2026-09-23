"""Series-field search regressions, without contacting NDL Search."""

from unittest.mock import Mock

import pytest
from comicapi.genericmetadata import Credit, GenericMetadata
from comictalker.comictalker import TalkerDataError

from comictagger_jp_talker.models import SearchPage, SearchQuery
from comictagger_jp_talker.sources.ndl import build_cql

SERIES = "こちら葛飾区亀有公園前派出所"


@pytest.mark.parametrize(
    ("series", "title"),
    [
        (SERIES, ""),
        ("", SERIES),
        (SERIES, SERIES + ". 74"),
    ],
)
def test_metadata_uses_series_before_title(talker, record, series, title):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)

    page = talker.search_metadata(GenericMetadata(series=series, title=title))

    assert page.records == [record]
    talker.source.search.assert_called_once()
    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue, query.creator, query.publisher) == (SERIES, "", "", "")
    assert query.mediatype == "books" and query.sort_order == "oldest"


@pytest.mark.parametrize(("volume", "issue"), [(74, None), (None, "74")])
def test_metadata_number_is_a_search_constraint_independent_of_output_mode(talker, record, volume, issue):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)

    for output_mode in ("volume", "issue", "both"):
        talker.volume_output = output_mode
        talker.search_metadata(GenericMetadata(series=SERIES, volume=volume, issue=issue))
        query = talker.source.search.call_args.args[0]
        assert (query.title, query.issue) == (SERIES, "74")


@pytest.mark.parametrize(
    ("issue", "credits", "expected"),
    [
        (None, [Credit("秋本治", "Writer")], [("", "秋本治"), ("", "")]),
        ("74", [], [("74", ""), ("", "")]),
        ("74", [Credit("秋本治", "Writer")], [("74", "秋本治"), ("74", ""), ("", "秋本治"), ("", "")]),
    ],
)
def test_metadata_relaxes_issue_and_creator_only_after_no_results(talker, record, issue, credits, expected):
    talker._source = Mock()
    talker.source.search.side_effect = [SearchPage([], 0) for _ in expected[:-1]] + [SearchPage([record], 1)]
    talker.publisher = "集英社"

    page = talker.search_metadata(GenericMetadata(series=SERIES, issue=issue, credits=credits))

    assert page.records == [record]
    queries = [call.args[0] for call in talker.source.search.call_args_list]
    assert [(q.issue, q.creator) for q in queries] == expected
    assert all(q.title == SERIES and q.publisher == "集英社" and q.mediatype == "books" for q in queries)


def test_metadata_search_trims_whitespace_without_changing_metadata(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    metadata = GenericMetadata(series=f"  {SERIES}  ", title="ignored", issue="  ")

    talker.search_metadata(metadata)

    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue) == (SERIES, "")
    assert metadata.series == f"  {SERIES}  " and metadata.issue == "  "


def test_blank_series_falls_back_to_title(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)

    talker.search_metadata(GenericMetadata(series="  ", title=f"  {SERIES}  "))

    assert talker.source.search.call_args.args[0].title == SERIES


def test_empty_metadata_search_never_reaches_source(talker):
    talker._source = Mock()

    with pytest.raises(TalkerDataError, match="ISBN またはタイトル"):
        talker.search_metadata(GenericMetadata(series="", title="", issue=""))

    talker.source.search.assert_not_called()


def test_issue_only_metadata_keeps_existing_title_field_search(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)

    talker.search_metadata(GenericMetadata(issue="74"))

    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue) == ("", "74")
    assert 'title = "74"' in build_cql(query)


def test_cql_omits_empty_filters_and_preserves_series_unicode():
    query = SearchQuery(title=SERIES, issue="", creator="", publisher="", sort_order="oldest")

    assert build_cql(query) == (
        f'title = "{SERIES}" AND mediatype = "books" AND sortBy=issued_date/sort.ascending'
    )


def test_host_series_search_uses_same_title_without_extra_constraints(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)

    assert talker.search_for_series(SERIES)

    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue, query.creator, query.publisher) == (SERIES, "", "", "")


def test_blank_talker_filters_do_not_narrow_series_search(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    talker.creator = "  "
    talker.publisher = "  "

    assert talker.search_for_series(SERIES)

    query = talker.source.search.call_args.args[0]
    assert (query.title, query.creator, query.publisher) == (SERIES, "", "")


def test_metadata_omits_blank_author_and_publisher_settings(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    talker.publisher = "  "

    talker.search_metadata(GenericMetadata(series=SERIES, credits=[Credit("  ", "Writer")]))

    query = talker.source.search.call_args.args[0]
    assert (query.creator, query.publisher) == ("", "")


def test_explicit_online_material_filter_is_not_relaxed(talker):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([], 0)
    talker.mediatype = "online"

    assert talker.search_for_series(SERIES) == []

    talker.source.search.assert_called_once()
    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue, query.creator, query.publisher, query.mediatype) == (
        SERIES,
        "",
        "",
        "",
        "online",
    )
