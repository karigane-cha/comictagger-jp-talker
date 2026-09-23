"""Focused Phase 1 safety checks that span search, source data and host output."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from comictagger_jp_talker.models import SearchPage


def test_title_search_tries_all_requested_constraints_first(talker, record):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    talker.creator = "作者"
    talker.publisher = "出版社"
    talker.mediatype = "booklet"

    assert len(talker.search_for_series("作品名. 2")) == 1
    query = talker.source.search.call_args.args[0]
    assert (query.title, query.issue, query.creator) == ("作品名", "2", "作者")
    assert (query.publisher, query.mediatype) == ("出版社", "booklet")


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_subject_tags_setting_requires_a_boolean(talker, value):
    with pytest.raises(ValueError, match="subject_tags|件名"):
        talker.parse_settings({"jpbooks_subject_tags": value})


@pytest.mark.parametrize(
    "editions",
    [
        ["通常版"],
        ["新装版"],
        ["完全版"],
        ["文庫版"],
        ["愛蔵版"],
        ["特装版"],
        ["改訂版"],
        ["新版"],
    ],
)
def test_edition_candidates_remain_distinct(record, editions):
    from comictagger_jp_talker.mapping import to_metadata, to_series
    from comictagger_jp_talker.sources.ndl import rank_records

    candidate = replace(record, id="other-edition", title="作品名. 1", volumes=["1"], editions=editions)
    original = replace(record, title="作品名. 1", volumes=["1"], editions=[])
    ranked = rank_records([candidate, original])
    assert len(ranked) == 2
    md = to_metadata(candidate)
    assert md.series == "作品名" and md.title == "作品名. 1"
    assert "版: " + editions[0] in md.notes
    assert "Edition: " + editions[0] in to_series(candidate).description


@pytest.mark.parametrize(
    "raw",
    [
        "0", "第0巻", "上", "下", "上巻", "下巻", "前編", "後編", "12.5", "1-2", "1/2",
        "別巻", "外伝", "番外編", "特別編", "完", "公式ファンブック", "短編集", "総集編",
    ],
)
def test_noninteger_and_zero_volume_only_never_invents_a_number(record, raw):
    from comictagger_jp_talker.mapping import explicit_volume_number, resolve_record_number, to_metadata

    record = replace(record, title="作品名", volumes=[raw])
    resolved = resolve_record_number(record)
    assert not resolved.conflict
    assert resolved.inferred is None
    md = to_metadata(record, volume_output="volume")
    assert md.issue is None and "NDL 巻次（原データ）: " + raw in md.notes
    assert md.volume == (0 if explicit_volume_number(raw) == "0" else None)
    assert record.volumes == [raw]


@pytest.mark.parametrize(
    "isbns,preferred,expected",
    [
        (["9784101010137"], "", "9784101010137"),
        (["4101010137"], "", "9784101010137"),
        (["4101010137", "978-4-10-101013-7"], "", "9784101010137"),
        (["4101010137", "9784101010137", "9784885942877"], "", None),
        (["9784101010137", "9784885942877"], "4101010137", "9784101010137"),
        (["9784101010137", "9784885942877"], "9780306406157", None),
        (["123", "9784101010138", "１２３４５６７８９０"], "", None),
        (["123", "9784101010137"], "", "9784101010137"),
    ],
)
def test_gtin_uses_only_one_unambiguous_valid_isbn(record, isbns, preferred, expected):
    from comictagger_jp_talker.mapping import to_metadata

    record = replace(record, isbns=isbns.copy())
    assert to_metadata(record, preferred_isbn=preferred).gtin == expected
    assert record.isbns == isbns


@pytest.mark.parametrize(
    "title,expected_series,expected_number",
    [
        ("作品名. 1", "作品名", "1"),
        ("作品名 1", "作品名", "1"),
        ("作品名 第1巻", "作品名", "1"),
        ("作品名．１", "作品名", "1"),
        ("作品名 1(副題)", "作品名", "1"),
        ("作品名 第１巻（副題）", "作品名", "1"),
        ("作品名 001", "作品名", "1"),
        ("作品名 第001巻", "作品名", "1"),
        ("ブルーロック = BLUELOCK. 31", "ブルーロック = BLUELOCK", "31"),
        ("FX戦士くるみちゃん. 1", "FX戦士くるみちゃん", "1"),
        ("パタリロ! : 選集. 1 (国王誕生の巻)", "パタリロ! : 選集", "1"),
        ("作品名 1/2", "作品名 1/2", None),
        ("作品名 100%", "作品名 100%", None),
        ("作品名 24時間", "作品名 24時間", None),
        ("作品名 第2章", "作品名 第2章", None),
    ],
)
def test_series_and_logical_number_keep_title_and_symbols(record, title, expected_series, expected_number):
    from comictagger_jp_talker.mapping import resolve_record_number, to_metadata

    record = replace(record, title=title, volumes=[], series_titles=["ジャンプコミックス"])
    md = to_metadata(record)
    assert (md.title, md.series, resolve_record_number(record).value) == (
        title,
        expected_series,
        expected_number,
    )
    assert "NDL シリーズ表記（原データ）: ジャンプコミックス" in md.notes


@pytest.mark.parametrize(
    "volumes,expected,conflict",
    [
        (["1"], "1", False),
        (["1 (副題)"], "1", False),
        (["1", "1 (副題)", "第1巻"], "1", False),
        (["2"], None, True),
        (["1", "2"], None, True),
    ],
)
def test_explicit_number_consistency(record, volumes, expected, conflict):
    from comictagger_jp_talker.mapping import resolve_record_number, to_metadata

    record = replace(record, title="作品名. 1 (副題)", volumes=volumes.copy())
    resolved = resolve_record_number(record)
    assert (resolved.value, resolved.inferred, resolved.conflict) == (expected, "1", conflict)
    md = to_metadata(record, volume_output="both")
    assert (md.volume, md.issue) == ((1, "1") if not conflict else (None, None))
    assert ("巻番号の不一致" in md.notes) is conflict
    assert record.volumes == volumes


def test_paper_and_digital_candidates_show_distinguishing_fields(record):
    from comictagger_jp_talker.mapping import to_series
    from comictagger_jp_talker.sources.ndl import rank_records

    paper = replace(
        record,
        id="paper",
        title="作品名. 1",
        editions=["通常版"],
        material_types=["図書 http://ndl.go.jp/ndltype/Book"],
        isbns=["9784101010137"],
    )
    digital = replace(
        paper,
        id="digital",
        editions=["新装版"],
        material_types=["電子資料 http://ndl.go.jp/ndltype/ElectronicResource"],
        isbns=["9784885942877"],
    )
    assert {r.id for r in rank_records([paper, digital])} == {"paper", "digital"}
    for item in (paper, digital):
        details = to_series(item).description
        for label in (
            "Series:", "Author:", "ISBN:", "Publisher:",
            "Bibliographic date:", "Edition:", "Material:", "Provider:",
        ):
            assert label in details
        assert item.editions[0] in details and item.isbns[0] in details
        assert item.material_types[0] in details


def test_publisher_language_subject_and_format_policy(record):
    from comictagger_jp_talker.mapping import to_metadata

    record = replace(
        record,
        publishers=["出版社", "発売元", "出版社"],
        languages=["eng", "jpn"],
        subjects=["漫画", "漫画", "創作", ""],
        ndc=["726.1"],
        classifications=["Y84"],
        editions=["新装版"],
        material_types=["図書 http://ndl.go.jp/ndltype/Book"],
    )
    md = to_metadata(record, subject_tags=True)
    assert md.publisher == "出版社 / 発売元 / 出版社"
    assert md.language == "en"  # Current policy uses only the first source language.
    assert md.tags == {"漫画", "創作"}
    assert "726.1" not in md.tags and "Y84" not in md.tags
    assert record.ndc == ["726.1"] and record.classifications == ["Y84"]
    assert md.format == "新装版 / 図書 http://ndl.go.jp/ndltype/Book"
    assert "版: 新装版" in md.notes and "資料種別: 図書" in md.notes


def test_empty_source_fields_do_not_add_labels(record):
    from comictagger_jp_talker.mapping import to_metadata, to_series

    record = replace(
        record,
        url="",
        isbns=[],
        volumes=[],
        series_titles=[],
        responsibilities=[],
        creators=[],
        editions=[],
        material_types=[],
        providers=[],
        rights=[],
        descriptions=[],
        abstracts=[],
        issued=[],
        dates=[],
    )
    md = to_metadata(record)
    assert md.web_links == [] and md.gtin is None and md.description is None
    for label in ("ISBN:", "版:", "資料種別:", "NDL 巻次", "巻番号の不一致"):
        assert label not in md.notes
    assert "Edition:" not in to_series(record).description


def test_rank_order_is_stable_and_prioritizes_isbn_provider_completeness(record):
    from comictagger_jp_talker.sources.ndl import rank_records

    base = replace(record, isbns=[], providers=[], id="z")
    complete = replace(base, id="a", isbns=["9784101010137"])
    national = replace(base, id="n", providers=["R100000002"])
    exact = replace(base, id="e", isbns=["9784885942877"])
    expected = ["e", "n", "a", "z"]
    assert [r.id for r in rank_records([base, national, complete, exact], "488594287X")] == expected
    assert [r.id for r in rank_records([exact, complete, national, base], "488594287X")] == expected


def test_malformed_cached_search_response_is_refetched(source):
    import hashlib

    from comictalker.comiccacher import Series as CachedSeries

    from comictagger_jp_talker.models import SearchQuery
    from comictagger_jp_talker.sources.ndl import SEARCH_CACHE, build_cql

    query = SearchQuery(title="作品名")
    key = hashlib.sha256(f"{source.maximum_records}:{build_cql(query)}".encode()).hexdigest()
    source.cache.add_search_results(SEARCH_CACHE, key, [CachedSeries(key, b"<invalid")], True)
    page = source.search(query)
    assert page.total == 1
    assert source.session.get.call_count == 1
    assert source.search(query).total == 1
    assert source.session.get.call_count == 1


def test_malformed_cached_record_is_refetched(source, record):
    from comictalker.comiccacher import Series as CachedSeries

    from comictagger_jp_talker.sources.ndl import RECORD_CACHE

    source.cache.add_series_info(RECORD_CACHE, CachedSeries(record.id, b"<invalid"), True)
    recovered = source.get(record.id)
    assert recovered.id == record.id
    assert source.session.get.call_count == 1


@pytest.mark.parametrize(
    "settings",
    [
        {"jpbooks_mediatype": "unknown"},
        {"jpbooks_maximum_records": True},
        {"jpbooks_maximum_records": 0},
        {"jpbooks_maximum_records": 101},
        {"jpbooks_maximum_records": "20"},
        {"jpbooks_search_order": "random"},
        {"jpbooks_volume_output": "number"},
        {"jpbooks_date_source": "issued"},
        {"jpbooks_key": "abc"},
        {"jpbooks_url": "https://example.org/sru"},
    ],
)
def test_invalid_settings_rejected_before_state_change(talker, settings):
    before = (talker.mediatype, talker.maximum_records, talker.volume_output, talker.subject_tags)
    with pytest.raises(ValueError):
        talker.parse_settings(settings)
    assert (talker.mediatype, talker.maximum_records, talker.volume_output, talker.subject_tags) == before


def test_truncated_search_preserves_counts_and_warning(talker, record, caplog):
    talker._source = Mock()
    talker.maximum_records = 2
    talker.source.search.return_value = SearchPage([record], 301, truncated=True)
    callback = Mock()
    candidates = talker.search_for_series("作品名", callback=callback)
    assert len(candidates) == 1
    callback.assert_called_once_with(1, 301)
    assert "301 件のうち最初の 2 件" in candidates[0].description
    assert "301 件のうち最初の 2 件" in caplog.text


def test_empty_title_search_after_fallback_returns_empty_page(talker):
    talker._source = Mock()
    talker.creator = "著者"
    talker.source.search.return_value = SearchPage([], 0)
    assert talker.search_for_series("作品名. 2") == []
    assert talker.source.search.call_count == 4


def test_control_characters_in_summary_are_safe_for_cix(record, tmp_path):
    import io
    import xml.etree.ElementTree as ET
    import zipfile

    from comicapi.comicarchive import ComicArchive
    from PIL import Image

    from comictagger_jp_talker.mapping import to_metadata

    md = to_metadata(replace(record, abstracts=["本文\x00と続き\x0b", "<b>HTML</b>"]))
    assert "\x00" not in md.description and "\x0b" not in md.description
    assert "本文と続き" in md.description
    assert "<b>HTML</b>" in md.description
    path = tmp_path / "summary.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (8, 8)).save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    assert ComicArchive(path).write_tags(md, "cix")
    with zipfile.ZipFile(path) as archive:
        summary = ET.fromstring(archive.read("ComicInfo.xml")).findtext("Summary")
    assert summary == md.description


def test_status_timeout_closes_temporary_source(talker, monkeypatch):
    from comictalker.comictalker import TalkerNetworkError

    temporary = Mock()
    temporary.check_status.side_effect = TalkerNetworkError("NDL Search", 4)
    monkeypatch.setattr("comictagger_jp_talker.talker.NDLSource", Mock(return_value=temporary))
    message, ok = talker.check_status({})
    assert not ok and message
    temporary.session.close.assert_called_once()
    temporary.cache.close.assert_called_once()


def test_parser_deduplicates_identical_publisher_and_keeps_distinct_ones(xml_bytes):
    import xml.etree.ElementTree as ET

    from comictagger_jp_talker.sources.ndl import NS, parse_sru

    root = ET.fromstring(xml_bytes)
    bib = root.find("sru:records/sru:record/sru:recordData/rdf:RDF/dcndl:BibResource", NS)
    for name in ("架空出版", "発売元"):
        ET.SubElement(bib, "{" + NS["dcterms"] + "}publisher").text = name
    parsed = parse_sru(ET.tostring(root)).records[0]
    assert parsed.publishers == ["架空出版", "発売元"]


def test_invalid_digital_date_does_not_claim_a_date_source(record):
    from comictagger_jp_talker.mapping import to_metadata

    record = replace(
        record,
        issued=[],
        dates=[],
        digitized_dates=["not-a-date"],
        content_dates=[],
    )
    md = to_metadata(record)
    assert (md.year, md.month, md.day) == (None, None, None)
    assert "日付取得元: none" not in md.notes
    assert "日付取得元: digital" not in md.notes


@pytest.mark.parametrize(
    "role,expected_roles",
    [
        ("著者", {"Writer"}),
        ("編", {"Editor"}),
        ("編著", {"Writer", "Editor"}),
        ("監修", {"Other"}),
        ("未定義役割", {"Other"}),
    ],
)
def test_structured_creator_role_is_not_lost_without_responsibility(xml_bytes, role, expected_roles):
    import xml.etree.ElementTree as ET

    from comictagger_jp_talker.mapping import to_metadata
    from comictagger_jp_talker.sources.ndl import NS, parse_sru

    root = ET.fromstring(xml_bytes)
    bib = root.find("sru:records/sru:record/sru:recordData/rdf:RDF/dcndl:BibResource", NS)
    for statement in bib.findall("dc:creator", NS):
        bib.remove(statement)
    agent = bib.find("dcterms:creator/foaf:Agent", NS)
    ET.SubElement(agent, "{" + NS["dcndl"] + "}role").text = role
    record = parse_sru(ET.tostring(root)).records[0]
    md = to_metadata(record)
    actual = {credit.role for credit in md.credits if credit.person == "架空, 太郎, 1900-2000"}
    assert actual == expected_roles
    assert role in md.notes


def test_structured_creator_role_does_not_change_an_unroled_coauthor(record):
    from comicapi.genericmetadata import Credit

    from comictagger_jp_talker.mapping import to_metadata

    record = replace(
        record,
        responsibilities=[],
        creators=["A", "B"],
        creator_roles=[("A", "監修")],
        contributors=[],
    )
    assert to_metadata(record).credits == [Credit("A", "Other"), Credit("B", "Writer")]


def test_format_can_match_a_kavita_special_keyword(record):
    from comictagger_jp_talker.mapping import to_metadata

    record = replace(record, editions=["Special"], material_types=[])
    assert to_metadata(record).format == "Special"


def test_jstage_abstract_is_not_copied_to_metadata_or_candidate(record):
    from comictagger_jp_talker.mapping import to_metadata, to_series

    abstract = "J-STAGE 提供の抄録"
    record = replace(record, providers=["R000000016"], abstracts=[abstract])
    assert to_metadata(record).description is None
    assert abstract not in to_series(record).description
    assert record.abstracts == [abstract]
