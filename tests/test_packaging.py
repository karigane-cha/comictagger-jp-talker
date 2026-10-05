from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from comictalker import get_talkers

from comictagger_jp_talker import __version__


def test_installed_entry_point(tmp_path):
    entries = entry_points(group="comictagger.talker")
    plugin = next(ep for ep in entries if ep.name == "jpbooks")
    assert plugin.load().name == "Japanese Books"
    talkers, _ = get_talkers("1.6.0b9", tmp_path)
    assert talkers["jpbooks"].name == "Japanese Books"


def test_built_zip_in_isolated_host(tmp_path):
    root = Path(__file__).resolve().parents[1]
    artifact = root / "dist" / f"jpbooks_talker-plugin-{__version__}.zip"
    if not artifact.is_file():
        pytest.skip("Build the wheel and local plugin ZIP first")
    # Separate process: evict an editable install, load actual ZIP, then let the host
    # remove its temporary sys.path entries. Exercise fetch AFTER loader cleanup.
    code = """
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
import requests
from comictaggerlib.ctsettings.plugin_finder import find_plugins
from comictalker import get_talkers
artifact, cache, fixture = map(Path, sys.argv[1:])
plugins = find_plugins(artifact.parent)
plugin = next(p for p in plugins.talkers if p.plugin.path == artifact)
assert plugin.obj.name == "Japanese Books"
assert ".zip" in plugin.obj.__init__.__code__.co_filename
assert str(artifact) not in sys.path
talkers, _ = get_talkers("1.6.0b9", cache, [plugin.obj])
talker = talkers["jpbooks"]
assert talker.madb_series_supplement is False
response = requests.Response()
response.status_code = 200
root = ET.fromstring(fixture.read_bytes())
for bib in root.iter("{http://ndl.go.jp/dcndl/terms/}BibResource"):
    for abstract in bib.findall("{http://purl.org/dc/terms/}abstract"):
        bib.remove(abstract)
    if bib.find("{http://purl.org/dc/terms/}title") is not None:
        bib.find("{http://purl.org/dc/terms/}title").text += " (副題)"
        for volume in bib.findall(
            "{http://ndl.go.jp/dcndl/terms/}volume/"
            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/"
            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}value"
        ):
            volume.text += " (副題)"
        ET.SubElement(bib, "{http://purl.org/dc/elements/1.1/}creator").text = "ねことうふ [著]"
        ET.SubElement(bib, "{http://purl.org/dc/elements/1.1/}creator").text = "監修者 [監修]"
response._content = ET.tostring(root)
for item in root.iter("{http://ndl.go.jp/dcndl/terms/}Item"):
    ET.SubElement(item, "{http://purl.org/dc/terms/}format").text = "EPUB"
    ET.SubElement(item, "{http://purl.org/dc/terms/}issued").text = "2026-03-15"
digital_response = ET.tostring(root)
summary_calls = []
summary_status = 200
def get(session, url, **kwargs):
    if url.endswith("/api/bib/external/search"):
        summary_calls.append(kwargs["params"]["f-token"])
        detail = requests.Response()
        detail.status_code = summary_status
        detail.headers["Retry-After"] = "120"
        detail._content = json.dumps({"hit": 1, "list": [{
            "id": "R100000002-Itest001", "items": [{"id": "returned-id", "meta": {
                "k39022": [{"v": "紙"}], "t35200": [{"v": "Paper summary from JSON"}]
            }}]
        }]}).encode()
        return detail
    return response
with patch.object(requests.Session, "get", get), patch.object(
    requests.Session, "post", side_effect=AssertionError("Normal ZIP lookup must not access MADB")
):
    candidates = talker.search_for_series("488594287X")
    assert len(candidates) == 1
    assert not candidates[0].aliases
    assert talker.fetch_series(candidates[0].id).id == candidates[0].id
    assert talker.fetch_issues_in_series(candidates[0].id)
    assert talker.fetch_issues_by_series_issue_num_and_year([candidates[0].id], "74", 2025)
    assert not summary_calls
    # Test optional 429 with a separate cold summary cache inside the built ZIP.
    failure_talker = plugin.obj("1.6.0b9", cache / "summary-429")
    summary_status = 429
    assert failure_talker.fetch_series(candidates[0].id).id == candidates[0].id
    assert not summary_calls
    base = failure_talker.fetch_comic_data(series_id=candidates[0].id)
    assert base.gtin == "9784885942877" and base.title and base.series
    assert base.description is None
    assert len(summary_calls) == 1
    assert failure_talker.fetch_comic_data(series_id=candidates[0].id) == base
    assert len(summary_calls) == 1
    assert not (failure_talker.cache_folder / "jpbooks/latest-error.txt").exists()
    failure_talker.source.session.close()
    failure_talker.source.cache.close()
    summary_calls.clear()
    summary_status = 200
    md = talker.fetch_comic_data(series_id=candidates[0].id, issue_number="74")
    assert len(summary_calls) == 1
    assert md.gtin == "9784885942877"
    assert any(c.person == "ねことうふ" and c.role == "Writer" for c in md.credits)
    assert any(c.person == "監修者" and c.role == "Other" for c in md.credits)
    assert "ねことうふ [著]" in md.notes
    assert md.series == "架空の漫画・髙﨑𠮷野〜旅―（新版）"
    assert md.title == "架空の漫画・髙﨑𠮷野〜旅―（新版）. ７４ (副題)"
    assert "NDL 巻次（原データ）: ７４ (副題)" in md.notes
    assert "巻番号の不一致" not in md.notes
    assert "NDL シリーズ表記（原データ）: 架空の漫画" in md.notes
    assert md.description == "Paper summary from JSON"
    assert talker.fetch_issues_by_series_issue_num_and_year([md.series_id], "74", 2025)
    talker.volume_output = "volume"
    volume_md = talker.fetch_comic_data(series_id=md.series_id, issue_number="74")
    assert volume_md.volume == 74 and volume_md.issue is None
    matches = talker.fetch_issues_by_series_issue_num_and_year([md.series_id], "74", 2025)
    assert len(matches) == 1 and matches[0].volume == 74 and matches[0].issue is None
    response._content = digital_response
    talker.search_for_series("488594287X", refresh_cache=True)
    digital_md = talker.fetch_comic_data(issue_id=md.issue_id)
    assert (digital_md.year, digital_md.month, digital_md.day) == (2026, 3, 15)
    talker.date_source = "bibliographic"
    paper_md = talker.fetch_comic_data(issue_id=md.issue_id)
    assert (paper_md.year, paper_md.month, paper_md.day) == (2025, 11, 19)
    response._content = b'''<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
<diagnostics><diagnostic xmlns="http://www.loc.gov/zing/srw/diagnostic/">
<uri>info:srw/diagnostic/1/1</uri><message>Record does not exist</message>
</diagnostic></diagnostics></searchRetrieveResponse>'''
    assert talker.search_for_series("9784088528113") == []
    from comictalker.comictalker import TalkerDataError
    try:
        talker.search_for_series("ISBN: invalid")
    except TalkerDataError as error:
        assert "Ctrl+C" in str(error)
        assert (cache / "jpbooks/latest-error.txt").is_file()
    else:
        raise AssertionError("Expected invalid ISBN error")
# Exercise the actual ZIP's opt-in path after the host has restored sys.path.
import contextlib
import io
from dataclasses import asdict
from unittest.mock import Mock
adapter_globals = talker.fetch_comic_data.__wrapped__.__globals__
mapper = adapter_globals["to_metadata"]
supplement = adapter_globals["supplement_series"]
assert ".zip" in supplement.__code__.co_filename
record_type = mapper.__globals__["BookRecord"]
madb_type = supplement.__globals__["MADBSource"]
assert ".zip" in madb_type.get_for_series_linkage.__code__.co_filename
limiter = madb_type._request.__globals__["_LIMITER"]
schema = "https://schema.org/"
namespace = "https://mediaarts-db.artmuseums.go.jp/id/"
ndl = record_type(
    "R100000002-Itest001", "", "https://ndlsearch.ndl.go.jp/books/R100000002-Itest001",
    isbns=["9784885942877"], volumes=["1"], publishers=["NDL publisher"],
    responsibilities=["著者 [著]"], abstracts=["NDL summary"], issued=["2025-11-19"],
    languages=["jpn"], subjects=["NDL subject"], series_titles=["NDL imprint"],
)
def term(value, kind="literal", language=None):
    result = {"type": kind, "value": value}
    if language:
        result["xml:lang"] = language
    return result
def resource(identifier, kind, fields):
    fields = [
        ("http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
         term("https://mediaarts-db.artmuseums.go.jp/data/class#" + kind, "uri")),
        (schema + "identifier", term(identifier)), *fields
    ]
    return {"head": {"vars": ["p", "o"]}, "results": {"bindings": [
        {"p": term(p, "uri"), "o": o} for p, o in fields
    ]}}
for direct in (False, True):
    talker.parse_settings({"jpbooks_madb_series_supplement": True})
    calls = []
    def post(session, url, **kwargs):
        calls.append(kwargs["data"]["query"])
        assert url == "https://mediaarts-db.artmuseums.go.jp/sparql"
        query = kwargs["data"]["query"]
        if "SELECT DISTINCT" in query:
            payload = {"head": {"vars": ["book", "identifier", "isbn"]}, "results": {"bindings": [
                {"book": term(namespace + "M1", "uri"), "isbn": term(ndl.isbns[0])}
            ]}}
        elif "/M1>" in query:
            fields = [(schema + "isbn", term(ndl.isbns[0])),
                      (schema + "isPartOf", term(namespace + "C1", "uri")),
                      ("http://purl.org/dc/terms/creator", term(namespace + "C2", "uri")),
                      ("http://purl.org/dc/terms/publisher", term(namespace + "C3", "uri")),
                      (schema + "provider", term("https://mediaarts-db.artmuseums.go.jp/ref/S1", "uri"))]
            if direct:
                fields.append(("https://mediaarts-db.artmuseums.go.jp/data/property#dataUrl", term(ndl.url)))
            payload = resource("M1", "MangaBook", fields)
        else:
            assert "/C1>" in query, "Agent/Holding must not be requested"
            payload = resource("C1", "MangaBookSeries", [
                (schema + "name", term("作品名", language="ja")),
                (schema + "name", term("サクヒンメイ", language="ja-hrkt")),
            ])
        value = requests.Response()
        value.status_code = 200
        value.headers["Content-Type"] = "application/sparql-results+json"
        value.raw = io.BytesIO(json.dumps(payload).encode())
        return value
    # New cache per confidence case so each exercises discovery + Book + Series.
    talker.cache_folder = cache / ("exact" if direct else "strong")
    with patch.object(requests.Session, "request", side_effect=AssertionError("Mock HTTP only")), \
         patch.object(requests.Session, "post", post), \
         patch.object(limiter, "ratelimit", lambda *a, **kw: contextlib.nullcontext()), \
         patch.object(talker.source, "get", Mock(return_value=ndl)):
        baseline = mapper(ndl)
        output = talker.fetch_comic_data(issue_id=ndl.id)
        assert output.series == "作品名"
        assert {k for k, v in asdict(baseline).items() if asdict(output)[k] != v} == {"series", "notes"}
        assert "MADB 照合: " + ("exact" if direct else "strong") in output.notes
        assert len(calls) == 3
        assert not any("/C2>" in q or "/C3>" in q or "/ref/S1>" in q for q in calls)
        assert talker.fetch_comic_data(issue_id=ndl.id) == output
        assert len(calls) == 3
print("ZIP: beta.9 load, default OFF, summary-free candidates, summary 429 fail-open, "
      "exact/strong lightweight supplement, Agent/Holding zero passed")
"""
    # Use a separate isolated process: the host restores module search paths and
    # can discover installed entry points, so a later import there could silently
    # test the editable install. Do not preload optional modules into the host test.
    linkage_code = """
import sys
from unittest.mock import patch
import requests
sys.path.insert(0, sys.argv[1])
with patch.object(requests.Session, "request", side_effect=AssertionError("No import-time network")):
    from comictagger_jp_talker.linkage import LinkageResult, LinkageStatus, RecordMatch, compare_candidates
    from comictagger_jp_talker.provenance import FieldEvidence, SeriesComparison
    from comictagger_jp_talker.models import BookRecord
    assert ".zip" in compare_candidates.__code__.co_filename
    assert compare_candidates(BookRecord("test", "Title"), []).status == LinkageStatus.UNMATCHED
print("ZIP: optional linkage API imported and evaluated without network")
"""
    env = dict(os.environ, PYTHONUTF8="1")
    for snippet in (linkage_code, code):
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-I",
                "-c",
                snippet,
                str(artifact),
                str(tmp_path),
                str(root / "tests/fixtures/ndl.xml"),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
