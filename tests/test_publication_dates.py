"""Synthetic per-item dates; keep paper/digital sources and their identities apart."""

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from unittest.mock import Mock

import pytest
import settngs
from comicapi.comicarchive import ComicArchive
from comictaggerlib.ctsettings.plugin import register_talker_settings
from comictalker.comiccacher import Series as CachedSeries
from PIL import Image

from comictagger_jp_talker.mapping import (
    is_digital_record,
    publication_date,
    resolve_publication_date,
    to_metadata,
    to_series,
)
from comictagger_jp_talker.models import ContentDates, SearchPage
from comictagger_jp_talker.sources.ndl import NS, RDF_ABOUT, RDF_RESOURCE, parse_sru


@pytest.fixture
def dated_record(record):
    return replace(
        record,
        issued=["2020-04-10"],
        dates=[],
        content_dates=[ContentDates(uri=record.url + "#item", issued=["2020-05-01"], formats=["EPUB"])],
    )


@pytest.mark.parametrize(
    "mode,digital,has_date,expected,source",
    [
        ("auto", False, True, (2020, 4, 10), "bibliographic"),
        ("auto", True, True, (2020, 5, 1), "digital"),
        ("auto", True, False, (2020, 4, 10), "bibliographic"),
        ("digital", False, True, (2020, 5, 1), "digital"),
        ("bibliographic", True, True, (2020, 4, 10), "bibliographic"),
        ("digital", True, False, (2020, 4, 10), "bibliographic"),
    ],
)
def test_mode_selection(dated_record, mode, digital, has_date, expected, source):
    item = dated_record.content_dates[0]
    if not digital:
        item.uri = "https://ndlsearch.ndl.go.jp/books/related-ebook#item"
    if not has_date:
        item.issued = []
    assert is_digital_record(dated_record) is digital
    resolved = resolve_publication_date(dated_record, source_mode=mode)
    assert resolved.value == expected and resolved.source == source
    md = to_metadata(dated_record, date_source=mode)
    assert (md.year, md.month, md.day) == expected
    assert publication_date(dated_record) == (2020, 4, 10)
    assert dated_record.issued == ["2020-04-10"]


@pytest.mark.parametrize(
    "issued,dates,expected,raw",
    [
        (["2022"], ["2022-03-15"], (2022, 3, 15), "2022-03-15"),
        (["2022"], ["2021-03-15"], (2022, None, None), "2022"),
        (["2022-03"], ["2022-04-15"], (2022, 3, None), "2022-03"),
        (["2022-03-15"], ["2022-03-16"], (2022, 3, 15), "2022-03-15"),
        ([], ["2020-05"], (2020, 5, None), "2020-05"),
        (["invalid", "2023-02-29"], ["2024.2.29"], (2024, 2, 29), "2024.2.29"),
        (["2022-00", "2022-13", "0000", "2022-01-00"], [], (2020, 4, 10), "2020-04-10"),
        ([], ["2022年3月15日", "2022-03-15T12:00:00", "2022-03/2023-03"], (2020, 4, 10), "2020-04-10"),
    ],
)
def test_precision_validation_and_provenance(dated_record, issued, dates, expected, raw):
    item = dated_record.content_dates[0]
    item.issued, item.dates = issued.copy(), dates.copy()
    result = resolve_publication_date(dated_record)
    assert result.value == expected and result.raw_value == raw
    assert item.issued == issued and item.dates == dates


def test_no_precision_from_paper(dated_record):
    dated_record.content_dates[0].issued = ["2020"]
    assert resolve_publication_date(dated_record).value == (2020, None, None)


@pytest.mark.parametrize("level", ["bib", "item"])
def test_v2_digitized_fallback_and_available_not_publication(dated_record, level):
    item = dated_record.content_dates[0]
    item.issued = []
    item.available = ["2030-01-01"]
    dated_record.available_dates = ["2031-01-01"]
    if level == "bib":
        dated_record.digitized_dates = ["2021-03-15"]
    else:
        item.digitized = ["2021-03-15"]
    result = resolve_publication_date(dated_record)
    assert result.value == (2021, 3, 15) and result.field == "dcndl:dateDigitized"
    item.issued = ["2022-02-03"]
    assert resolve_publication_date(dated_record).value == (2022, 2, 3)
    item.issued = item.digitized = dated_record.digitized_dates = []
    assert resolve_publication_date(dated_record).value == (2020, 4, 10)


@pytest.mark.parametrize(
    "types,formats,descriptions,expected",
    [
        (["図書 http://ndl.go.jp/ndltype/Book"], [], [], False),
        (["オンライン資料 http://ndl.go.jp/ndltype/OnlineResource"], [], [], True),
        (["http://ndl.go.jp/ndltype/OnlineJournal"], [], [], True),
        (["電子資料 http://ndl.go.jp/ndltype/ElectronicResource"], [], [], True),
        (["http://ndl.go.jp/ndltype/Document"], [], [], True),
        (["digital book", "http://example.org/OnlineResource"], [], [], False),
        (["http://ndl.go.jp/ndltype/OnlineResourceExtra"], [], [], False),
        ([], ["EPUB"], [], True),
        ([], ["application/pdf"], [], True),
        ([], [], ["電子書籍"], True),
        ([], [], ["電子書籍についての紙の本"], False),
    ],
)
def test_exact_digital_evidence(record, types, formats, descriptions, expected):
    record = replace(record, material_types=types, formats=formats, descriptions=descriptions)
    assert is_digital_record(record) is expected


def test_multiple_editions_are_not_combined(dated_record):
    original = dated_record.content_dates[0]
    other = replace(original, uri="https://ndlsearch.ndl.go.jp/books/other#item", issued=["2021-06-01"])
    dated_record.content_dates.append(other)
    # The selected record's own Item wins over an unrelated edition.
    assert resolve_publication_date(dated_record).value == (2020, 5, 1)
    original.uri = "https://ndlsearch.ndl.go.jp/books/another#item"
    result = resolve_publication_date(dated_record, source_mode="digital")
    assert result.value == (2020, 4, 10) and result.warning
    assert "デジタル資料間" in to_metadata(dated_record, date_source="digital").notes
    other.issued = original.issued.copy()
    assert resolve_publication_date(dated_record, source_mode="digital").value == (2020, 5, 1)
    original.issued = ["2020"]
    assert resolve_publication_date(dated_record, source_mode="digital").source == "bibliographic"


def test_own_undated_content_does_not_borrow_another_edition(dated_record):
    original = dated_record.content_dates[0]
    original.issued = []
    dated_record.content_dates.append(
        replace(original, uri="https://ndlsearch.ndl.go.jp/books/another#item", dates=["2024-01-01"])
    )
    assert resolve_publication_date(dated_record).value == (2020, 4, 10)


def test_no_valid_dates_returns_none(dated_record):
    dated_record.issued = ["invalid"]
    dated_record.content_dates[0].issued = ["2024-02-30"]
    resolved = resolve_publication_date(dated_record)
    assert resolved.value == (None, None, None) and resolved.source == "none"


def test_notes_and_candidates(dated_record):
    dated_record.content_dates[0].issued = ["2022-03-15"]
    md = to_metadata(dated_record)
    assert "書誌上の日付: 2020-04-10" in md.notes
    assert "デジタル版の日付: 2022-03-15" in md.notes
    assert dated_record.content_dates[0].uri in md.notes
    assert to_series(dated_record).start_year == 2022
    assert to_series(dated_record, date_source="bibliographic").start_year == 2020
    dated_record.content_dates[0].issued = dated_record.issued.copy()
    assert "デジタル版の日付" not in to_metadata(dated_record).notes
    with pytest.raises(ValueError):
        to_metadata(dated_record, date_source="invalid")


@pytest.fixture
def digital_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)
    rdf = root.find("sru:records/sru:record/sru:recordData/rdf:RDF", NS)
    bib = rdf.find("dcndl:BibResource", NS)
    bib.find("dcterms:issued", NS).text = "2020"
    bib.find("dcterms:date", NS).text = "2020.4.10"
    uri = "https://ndlsearch.ndl.go.jp/books/ebook-example#item"
    ET.SubElement(bib, "{" + NS["dcndl"] + "}record", {RDF_RESOURCE: uri})
    item = ET.SubElement(rdf, "{" + NS["dcndl"] + "}Item", {RDF_ABOUT: uri})
    for name, value in [
        ("issued", "2021"),
        ("date", "2021-03-15"),
        ("available", "2022-01-01"),
        ("format", "EPUB"),
    ]:
        ET.SubElement(item, "{" + NS["dcterms"] + "}" + name).text = value
    # Neither a foreign namespace nor an unlinked Item may influence the date.
    ET.SubElement(item, "{http://example.org/}issued").text = "2099-01-01"
    unlinked = ET.SubElement(rdf, "{" + NS["dcndl"] + "}Item", {RDF_ABOUT: "https://example.org/unlinked"})
    ET.SubElement(unlinked, "{" + NS["dcterms"] + "}date").text = "2098-01-01"
    return ET.tostring(root)


def test_namespace_parser_keeps_item_dates_separate(digital_xml):
    record = parse_sru(digital_xml).records[0]
    assert record.issued == ["2020"] and record.dates == ["2020.4.10"]
    assert len(record.content_dates) == 2  # Own paper holdings plus the explicitly linked ebook.
    item = record.content_dates[1]
    assert item.issued == ["2021"] and item.dates == ["2021-03-15"]
    assert item.available == ["2022-01-01"] and item.formats == ["EPUB"]
    assert publication_date(record) == (2020, 4, 10)
    assert not is_digital_record(record)
    assert resolve_publication_date(record, source_mode="digital").value == (2021, 3, 15)
    assert "2098-01-01" in record.raw_xml


def test_v2_fields_remain_raw(xml_bytes):
    root = ET.fromstring(xml_bytes)
    bib = root.find(".//dcndl:BibResource", NS)
    ET.SubElement(bib, "{" + NS["dcndl"] + "}dateDigitized").text = "2026.2"
    ET.SubElement(bib, "{" + NS["dcterms"] + "}available").text = "2026-03"
    record = parse_sru(ET.tostring(root)).records[0]
    assert record.digitized_dates == ["2026.2"] and record.available_dates == ["2026-03"]
    assert resolve_publication_date(record).value == (2026, 2, None)
    assert publication_date(record) == (2025, 11, 19)


@pytest.mark.parametrize("mode,year", [("auto", 2021), ("digital", 2021), ("bibliographic", 2020)])
def test_all_talker_paths(talker, dated_record, mode, year):
    dated_record.content_dates[0].issued = ["2021-03-15"]
    talker.date_source = mode
    talker._source = Mock()
    talker.source.get.return_value = dated_record
    talker.source.search.return_value = SearchPage([dated_record], 1)
    assert talker.search_for_series("作品")[0].start_year == year
    assert talker.fetch_series(dated_record.id).start_year == year
    assert talker.fetch_comic_data(issue_id=dated_record.id).year == year
    assert talker.fetch_issues_in_series(dated_record.id)[0].year == year
    assert talker.fetch_issues_by_series_issue_num_and_year([dated_record.id], "74", year)
    assert not talker.fetch_issues_by_series_issue_num_and_year([dated_record.id], "74", 2019)
    assert talker.source.search.call_args.args[0].sort_order == "oldest"


def test_settings_persist(talker, tmp_path):
    manager = settngs.Manager()
    register_talker_settings(manager, {talker.id: talker})
    setting = manager.definitions["Source jpbooks"].v["jpbooks_date_source"]
    assert setting.default == "auto" and setting.file
    for mode in ["auto", "bibliographic", "digital"]:
        config = manager.parse_cmdline(["--jpbooks-date-source", mode])
        path = tmp_path / "settings.json"
        assert manager.save_file(config, path)
        restored, success = manager.parse_file(path)
        assert success and restored.values["Source jpbooks"]["jpbooks_date_source"] == mode
        talker.parse_settings({"jpbooks_date_source": mode})
        assert talker.date_source == mode
    talker.parse_settings({})
    assert talker.date_source == "auto"
    with pytest.raises(ValueError):
        talker.parse_settings({"jpbooks_date_source": "unexpected"})


def test_v3_schema_does_not_reuse_v2_record_cache(source, digital_xml, record):
    source.cache.add_series_info("jpbooks.ndl.record", CachedSeries(record.id, record.raw_xml.encode()), True)
    source.session.get.return_value._content = digital_xml
    fetched = source.get(record.id)
    assert source.session.get.call_count == 1
    assert source.session.get.call_args.kwargs["params"]["recordSchema"] == "dcndl_v3"
    assert resolve_publication_date(fetched, source_mode="digital").value == (2021, 3, 15)
    source.get(record.id)
    assert source.session.get.call_count == 1


@pytest.mark.parametrize(
    "mode,expected", [("auto", (2021, 3, 15)), ("digital", (2021, 3, 15)), ("bibliographic", (2020, 4, 10))]
)
def test_cix_date_roundtrip(tmp_path, dated_record, mode, expected):
    pytest.importorskip("comicinfoxml")
    dated_record.content_dates[0].issued = ["2021-03-15"]
    md = to_metadata(dated_record, date_source=mode)
    path = tmp_path / "dates.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    assert ComicArchive(path).write_tags(md, "cix")
    restored = ComicArchive(path).read_tags("cix")
    assert (restored.year, restored.month, restored.day) == expected
    assert "書誌上の日付: 2020-04-10" in restored.notes
