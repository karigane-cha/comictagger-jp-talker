"""One live SRU request per test, only when explicitly enabled."""

import os

import pytest
from comicapi.genericmetadata import GenericMetadata

from comictagger_jp_talker.isbn import isbn13
from comictagger_jp_talker.mapping import (
    explicit_volume_number,
    infer_volume,
    is_digital_record,
    resolve_publication_date,
    resolve_record_number,
    to_metadata,
)
from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources.ndl import NDLSource
from comictagger_jp_talker.talker import JapaneseBooksTalker


@pytest.mark.network
@pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in NDL network test")
def test_one_real_ndl_request(tmp_path):
    source = NDLSource(tmp_path, maximum_records=10)
    try:
        page = source.search(SearchQuery(isbn="9784885942877", mediatype=""), refresh=True)
        assert page.records
        assert all("9784885942877" in {isbn13(v) for v in r.isbns} for r in page.records)
        assert to_metadata(page.records[0]).title
    finally:
        source.session.close()
        source.cache.close()


@pytest.mark.network
@pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in NDL network test")
def test_real_paper_and_related_digital_dates(tmp_path):
    source = NDLSource(tmp_path, maximum_records=1)
    try:
        page = source.search(SearchQuery(itemno="R100000002-I029046058", mediatype=""), refresh=True)
        record = page.records[0]
        assert record.id == "R100000002-I029046058"
        assert not is_digital_record(record)  # A linked ebook does not change this paper identity.
        assert resolve_publication_date(record).value == (2018, 7, None)
        digital = resolve_publication_date(record, source_mode="digital")
        assert digital.value == (2018, 6, 27)
        assert digital.source_uri.endswith("R100000137-I75806750000002020618#item")
    finally:
        source.session.close()
        source.cache.close()


@pytest.mark.network
@pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in NDL network test")
def test_real_series_only_metadata_search(tmp_path):
    series = "こちら葛飾区亀有公園前派出所"
    talker = JapaneseBooksTalker("1.6.0b9", tmp_path)
    talker.maximum_records = 10
    try:
        page = talker.search_metadata(GenericMetadata(series=series))
        assert page.records
        assert page.total > 0 and len(page.records) <= talker.maximum_records
        assert any(infer_volume(record.title)[0].startswith(series) for record in page.records)
        candidates = talker.search_for_series(series)
        assert candidates and any(candidate.name.startswith(series) for candidate in candidates)
    finally:
        if talker._source is not None:
            talker.source.session.close()
            talker.source.cache.close()


@pytest.mark.network
@pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in NDL network test")
def test_real_dotted_volume_delimiter_is_not_part_of_series(tmp_path):
    source = NDLSource(tmp_path, maximum_records=1)
    try:
        page = source.search(SearchQuery(itemno="R100000002-I000001355589", mediatype=""), refresh=True)
        assert page.records
        record = page.records[0]
        series = "こちら葛飾区亀有公園前派出所"
        assert record.title == series + ". 第1巻"
        assert record.volumes == ["第1巻"]
        assert record.series_titles == ["ジャンプ・コミックス"]
        assert infer_volume(record.title) == (series, "1")
        metadata = to_metadata(record)
        assert metadata.title == record.title
        assert metadata.series == series
        assert metadata.issue == "1"
    finally:
        source.session.close()
        source.cache.close()


@pytest.mark.network
@pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in NDL network test")
def test_real_english_volume_marker_is_not_part_of_series(tmp_path):
    source = NDLSource(tmp_path, maximum_records=1)
    try:
        page = source.search(SearchQuery(itemno="R100000002-I023440575", mediatype=""), refresh=True)
        assert page.records
        record = page.records[0]
        series = "ご注文はうさぎですか?"
        assert record.title == series + " volume 1"
        assert record.volumes == ["volume 1"]
        assert record.series_titles == ["Manga time KR comics. Kirara menu ; 619"]
        assert infer_volume(record.title) == (series, "1")
        assert explicit_volume_number(record.volumes[0]) == "1"
        resolved = resolve_record_number(record)
        assert (resolved.explicit, resolved.inferred, resolved.value, resolved.conflict) == (
            "1",
            "1",
            "1",
            False,
        )
        metadata = to_metadata(record, volume_output="both")
        assert metadata.title == record.title
        assert metadata.series == series
        assert (metadata.volume, metadata.issue) == (1, "1")
        assert "NDL 巻次（原データ）: volume 1" in metadata.notes
        assert "巻番号の不一致" not in metadata.notes
    finally:
        source.session.close()
        source.cache.close()
