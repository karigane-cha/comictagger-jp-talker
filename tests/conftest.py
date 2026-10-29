from __future__ import annotations

import contextlib
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.talker import JapaneseBooksTalker


@pytest.fixture(autouse=True)
def offline(request, monkeypatch):
    if request.node.get_closest_marker("network") and os.getenv("JPBOOKS_RUN_NETWORK_TESTS") == "1":
        return

    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests must not access the network")

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", lambda *args, **kwargs: contextlib.nullcontext())


@pytest.fixture
def xml_bytes():
    return (Path(__file__).parent / "fixtures" / "ndl.xml").read_bytes()


@pytest.fixture
def record(xml_bytes):
    return ndl.parse_sru(xml_bytes).records[0]


@pytest.fixture
def ordered_search_xml():
    """SRU order deliberately disagrees with provider, completeness, ID and date ranks."""
    root = ET.Element(f"{{{ndl.NS['sru']}}}searchRetrieveResponse")
    ET.SubElement(root, f"{{{ndl.NS['sru']}}}numberOfRecords").text = "6"
    records = ET.SubElement(root, f"{{{ndl.NS['sru']}}}records")
    for record_id, national, rich, isbn, year in (
        ("other-z", False, False, "9784885942877", "2000"),
        ("ndl-z", True, False, "9784885942877", "1990"),
        ("ndl-a", True, False, "9784885942877", "2010"),
        ("ndl-rich", True, True, "9784885942877", "1980"),
        ("other-z", False, True, "9784885942877", "2020"),
        ("ndl-other", True, True, "9784101010137", "2005"),
    ):
        node = ET.SubElement(records, f"{{{ndl.NS['sru']}}}record")
        data = ET.SubElement(node, f"{{{ndl.NS['sru']}}}recordData")
        rdf = ET.SubElement(data, f"{{{ndl.NS['rdf']}}}RDF")
        identity = {ndl.RDF_ABOUT: f"https://ndlsearch.ndl.go.jp/books/{record_id}"}
        bib = ET.SubElement(rdf, f"{{{ndl.NS['dcndl']}}}BibResource", identity)
        ET.SubElement(bib, f"{{{ndl.NS['dcterms']}}}title").text = "漫画"
        ET.SubElement(bib, f"{{{ndl.NS['dcterms']}}}issued").text = year
        ET.SubElement(
            bib, f"{{{ndl.NS['dcterms']}}}identifier", {ndl.RDF_DATATYPE: ndl.NS["dcndl"] + "ISBN"}
        ).text = isbn
        if rich:
            for field, value in (("creator", "作者"), ("publisher", "出版社"), ("language", "jpn")):
                ET.SubElement(bib, f"{{{ndl.NS['dcterms']}}}{field}").text = value
        admin = ET.SubElement(rdf, f"{{{ndl.NS['dcndl']}}}BibAdminResource", identity)
        ET.SubElement(admin, f"{{{ndl.NS['dcndl']}}}bibRecordCategory").text = (
            "R100000002" if national else "R100000136"
        )
    return ET.tostring(root, encoding="utf-8")


@pytest.fixture
def source(tmp_path, monkeypatch, xml_bytes):
    source = ndl.NDLSource(tmp_path)
    response = requests.Response()
    response.status_code = 200
    response._content = xml_bytes
    monkeypatch.setattr(source.session, "get", Mock(return_value=response))
    yield source
    source.session.close()
    source.cache.close()


@pytest.fixture
def talker(tmp_path, source):
    talker = JapaneseBooksTalker("1.6.0b9", tmp_path)
    talker._source = source
    return talker
