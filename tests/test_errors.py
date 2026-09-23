import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from comictalker.comictalker import TalkerDataError, TalkerNetworkError

from comictagger_jp_talker.errors import report_error
from comictagger_jp_talker.models import SearchPage


def test_error_log_and_hint(talker, caplog):
    talker._source = Mock()
    talker._source.search.side_effect = TalkerNetworkError("NDL Search", 4, "Timeout")
    with caplog.at_level(logging.ERROR), pytest.raises(TalkerNetworkError) as caught:
        talker.search_for_series("髙﨑𠮷野〜旅")
    assert caught.value.sub_code == 4
    assert "Ctrl+C" in str(caught.value)
    path = talker.cache_folder / "jpbooks/latest-error.txt"
    assert str(path.resolve()) in str(caught.value)
    report = path.read_text(encoding="utf-8")
    assert "髙﨑𠮷野〜旅" in report
    assert "search_for_series" in report and "Traceback" in report
    assert "Timeout" in report and "https://ndlsearch.ndl.go.jp/api/sru" in report
    assert report.strip() in caplog.text
    # Nested public methods must not duplicate hints or overwrite the report.
    report_error(caught.value, talker.cache_folder, "outer method")
    assert str(caught.value).count("Ctrl+C") == 1
    assert path.read_text(encoding="utf-8") == report


def test_report_write_failure_preserves_original(talker, monkeypatch):
    monkeypatch.setattr(Path, "write_text", Mock(side_effect=PermissionError("read only")))
    with pytest.raises(TalkerDataError) as caught:
        talker.search_for_series("ISBN: invalid")
    assert "ISBN" in str(caught.value) and "Ctrl+C" in str(caught.value)
    assert "ComicTagger のログ画面" in str(caught.value)


def test_latest_report_replaced_and_lone_surrogate_safe(talker):
    report_error(ValueError("old"), talker.cache_folder, "old operation")
    report_error(ValueError("new\ud800"), talker.cache_folder, "new operation")
    report = (talker.cache_folder / "jpbooks/latest-error.txt").read_text(encoding="utf-8")
    assert "old operation" not in report
    assert "new\\ud800" in report


def test_zero_results_do_not_create_error_log(talker):
    talker._source = Mock()
    talker._source.search.return_value = SearchPage([], 0)
    assert talker.search_for_series("9784088528113") == []
    assert not (talker.cache_folder / "jpbooks/latest-error.txt").exists()
