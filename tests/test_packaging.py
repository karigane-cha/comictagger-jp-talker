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
def get(session, url, **kwargs):
    if url.endswith("/api/bib/external/search"):
        detail = requests.Response()
        detail.status_code = 200
        detail._content = json.dumps({"hit": 1, "list": [{
            "id": "R100000002-Itest001", "items": [{"id": "returned-id", "meta": {
                "k39022": [{"v": "紙"}], "t35200": [{"v": "Paper summary from JSON"}]
            }}]
        }]}).encode()
        return detail
    return response
with patch.object(requests.Session, "get", get):
    candidates = talker.search_for_series("488594287X")
    assert len(candidates) == 1
    assert not candidates[0].aliases
    md = talker.fetch_comic_data(series_id=candidates[0].id, issue_number="74")
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
print("ZIP: Japanese Books loaded and fetched with beta.9")
"""
    env = dict(os.environ, PYTHONUTF8="1")
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-I",
            "-c",
            code,
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
