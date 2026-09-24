"""Frozen Phase 1 output boundary; normal Talker operations never use MADB."""

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from comictagger_jp_talker.sources import madb


@pytest.mark.parametrize("mode", ["issue", "volume", "both"])
def test_phase1_metadata_baseline_and_no_madb_access(talker, monkeypatch, mode):
    # Snapshot generated from unchanged v0.1.12 modules and the existing NDL fixture.
    baseline = json.loads(
        (Path(__file__).parent / "fixtures" / "phase1_metadata.json").read_text(encoding="utf-8")
    )[mode]
    forbidden = Mock(side_effect=AssertionError("NDL operations must not construct MADBSource"))
    monkeypatch.setattr(madb.MADBSource, "__init__", forbidden)
    talker.volume_output = mode
    candidates = talker.search_for_series("488594287X")
    metadata = talker.fetch_comic_data(series_id=candidates[0].id, issue_number="74")
    for field, expected in baseline.items():
        value = getattr(metadata, field)
        if field == "credits":
            value = [asdict(credit) for credit in value]
        elif field == "web_links":
            value = [str(url) for url in value]
        elif isinstance(value, set):
            value = sorted(value)
        assert value == expected, field
    # Status deliberately opens a fresh NDLSource; intercept that Session too.
    monkeypatch.setattr(requests.Session, "get", talker.source.session.get)
    assert talker.check_status({})[1]
    forbidden.assert_not_called()
    assert all(
        call.args[0].startswith("https://ndlsearch.ndl.go.jp/")
        for call in talker.source.session.get.call_args_list
    )
