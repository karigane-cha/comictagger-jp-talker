import copy
import json
import xml.etree.ElementTree as ET
from dataclasses import replace
from unittest.mock import Mock

import pytest
import requests
from comictalker.comictalker import TalkerDataError, TalkerNetworkError

from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources.ndl import NS, NDLSource, parse_sru
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
    assert kwargs == {"params": {"cs": "bib", "f-token": ID}, "timeout": (5, 30)}
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
def test_invalid_json_not_cached(source, no_abstract, payload):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.return_value._content = payload
    with pytest.raises(TalkerDataError):
        source.get(ID)
    assert not source.cache.get_search_results("jpbooks.ndl.summary.v1", ID)


def test_summary_timeout_is_reported(source, no_abstract):
    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.side_effect = requests.Timeout()
    with pytest.raises(TalkerNetworkError) as error:
        source.get(ID)
    assert error.value.sub_code == 4


def test_summary_uses_shared_rate_limiter(source, no_abstract, details, monkeypatch):
    import contextlib

    from comictagger_jp_talker.sources import ndl

    source.session.get.return_value._content = no_abstract
    source.search(SearchQuery(isbn="488594287X"))
    source.session.get.return_value._content = json.dumps(details).encode()
    limiter = Mock(return_value=contextlib.nullcontext())
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", limiter)
    source.get(ID)
    assert limiter.call_count == 1


def test_record_abstract_and_notes_are_separate(xml_bytes):
    record = parse_sru(xml_bytes).records[0]
    assert record.abstracts == ["テスト用あらすじ。漢字・ひらがな・カタカナ。"]
    assert record.descriptions == ["内容注記：フィクション"]
