"""Keep raw NDL volumes, logical matching and output tags independent."""

from dataclasses import replace
from unittest.mock import Mock

import pytest
import settngs
from comicapi import merge
from comicapi.genericmetadata import GenericMetadata
from comictaggerlib.ctsettings.plugin import register_talker_settings
from comictalker.comictalker import TalkerDataError

from comictagger_jp_talker.mapping import (
    explicit_volume_number,
    resolve_record_number,
    to_metadata,
    to_series,
)
from comictagger_jp_talker.models import SearchPage


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", "1"),
        ("１", "1"),
        ("1巻", "1"),
        ("１巻", "1"),
        ("第1巻", "1"),
        ("第１巻", "1"),
        ("1 (国王誕生の巻)", "1"),
        ("1（国王誕生の巻）", "1"),
        ("1巻 (国王誕生の巻)", "1"),
        ("1巻（国王誕生の巻）", "1"),
        ("第1巻 (国王誕生の巻)", "1"),
        ("第1巻（国王誕生の巻）", "1"),
        ("第１巻（国王誕生の巻）", "1"),
        ("42(越後屋波多利郎江戸日記の巻)", "42"),
        ("42（越後屋波多利郎江戸日記の巻）", "42"),
        ("　 第０１巻　（特装版） \t", "1"),
        ("001 (新装版)", "1"),
        ("999", "999"),
        ("９９９巻（完）", "999"),
        ("0", "0"),
    ],
)
def test_explicit_volume_number(raw, expected):
    assert explicit_volume_number(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "上",
        "下",
        "前編",
        "後編",
        "上巻",
        "下巻",
        "1-2",
        "1.5",
        "1/2",
        "1・2",
        "外伝",
        "特別編",
        "完",
        "別巻",
        "A",
        "12A",
        "2024",
        "２０２４",
        "第2024巻",
        "2024 (新版)",
        "1 (副題）",
        "1（副題)",
        "1 (副題 (特装版))",
        "1 (副題) (特装版)",
        "1 ()",
        "1（）",
        "1 (副題",
        "",
        "　",
        "作品名 1",
    ],
)
def test_explicit_volume_number_rejects_ambiguous_values(raw):
    assert explicit_volume_number(raw) is None


@pytest.mark.parametrize(
    "raw,explicit,value,conflict",
    [
        (["1 (国王誕生の巻)"], "1", "1", False),
        (["1", "1 (国王誕生の巻)", "第１巻（特装版）"], "1", "1", False),
        (["2 (副題)"], "2", None, True),
        (["1", "2"], None, None, True),
        (["1 (副題)", "2（副題）"], None, None, True),
        (["1 (副題)", "上"], None, None, True),
    ],
)
def test_explicit_subtitle_resolution(record, raw, explicit, value, conflict):
    title = "パタリロ! : 選集. 1 (国王誕生の巻)"
    record = replace(record, title=title, volumes=raw.copy())
    resolved = resolve_record_number(record)
    assert (resolved.explicit, resolved.inferred, resolved.value, resolved.conflict) == (
        explicit,
        "1",
        value,
        conflict,
    )
    assert record.title == title and record.volumes == raw
    md = to_metadata(record)
    assert ("巻番号の不一致" in md.notes) is conflict
    assert "NDL 巻次（原データ）: " + " / ".join(raw) in md.notes


@pytest.mark.parametrize("raw", ["2024", "２０２４", "第2024巻", "2024 (新版)"])
def test_four_digit_explicit_values_remain_opaque(record, raw):
    md = to_metadata(replace(record, title="作品名", volumes=[raw]), volume_output="both")
    assert md.volume is None
    assert md.issue == raw  # Preserve the existing non-integer Issue label policy.
    assert "Volume へ整数変換できない" in md.notes


@pytest.mark.parametrize(
    "title,raw,explicit,inferred,value,conflict",
    [
        ("作品名", ["31"], "31", None, "31", False),
        ("作品名. 31", [], None, "31", "31", False),
        ("作品名. 31", ["31"], "31", "31", "31", False),
        ("作品名. 31", ["32"], "32", "31", None, True),
        ("作品名. 31", ["第３１巻"], "31", "31", "31", False),
        ("作品名", ["31", "32"], None, None, None, True),
        ("作品名", ["31", "３１"], "31", None, "31", False),
        ("作品名", [], None, None, None, False),
    ],
)
def test_resolution(record, title, raw, explicit, inferred, value, conflict):
    record = replace(record, title=title, volumes=raw.copy())
    resolved = resolve_record_number(record)
    assert (resolved.explicit, resolved.inferred, resolved.value, resolved.conflict) == (
        explicit,
        inferred,
        value,
        conflict,
    )
    assert record.volumes == raw
    assert resolved.requested is None


@pytest.mark.parametrize(
    "output,expected", [("volume", (2, None)), ("issue", (None, "2")), ("both", (2, "2"))]
)
@pytest.mark.parametrize("raw", ["2", "０２", "第2巻", "第２巻", "2 (副題)", "第２巻（副題）"])
def test_output_modes(record, output, expected, raw):
    record = replace(record, title="作品名", volumes=[raw])
    md = to_metadata(record, volume_output=output)
    assert (md.volume, md.issue) == expected
    assert record.volumes == [raw]
    assert "NDL 巻次（原データ）: " + raw in md.notes


@pytest.mark.parametrize("raw", ["上", "下", "前編", "後編", "外伝", "12.5"])
@pytest.mark.parametrize("output", ["volume", "issue", "both"])
def test_noninteger_numbers(record, raw, output):
    record = replace(record, title="作品名", volumes=[raw])
    assert resolve_record_number(record).value == raw
    md = to_metadata(record, volume_output=output)
    assert md.volume is None
    assert md.issue == (None if output == "volume" else raw)
    assert raw in md.notes and record.volumes == [raw]
    if output != "issue":
        assert "Volume へ整数変換できない" in md.notes


@pytest.mark.parametrize("output", ["volume", "issue", "both"])
@pytest.mark.parametrize("requested", ["", "31", "32"])
def test_conflict_cannot_be_overridden(record, output, requested):
    record = replace(record, title="作品名. 31", volumes=["32"])
    resolved = resolve_record_number(record, requested)
    assert resolved.conflict and resolved.value is None and resolved.source is None
    assert resolved.requested == (requested or None)
    md = to_metadata(record, existing_issue=requested, volume_output=output)
    assert md.volume is None and md.issue is None
    assert "巻番号の不一致" in md.notes
    assert "巻番号の不一致" in to_series(record).description
    assert record.volumes == ["32"]


def test_existing_is_not_source_data(record):
    record = replace(record, title="作品名", volumes=[])
    resolved = resolve_record_number(record, "第２巻")
    assert resolved.value == resolved.requested == "2"
    assert resolved.explicit is resolved.inferred is None and resolved.source == "existing"
    assert resolve_record_number(record).value is None
    with pytest.raises(ValueError):
        to_metadata(record, volume_output="unexpected")


@pytest.mark.parametrize(
    "output,expected", [("volume", (2, None)), ("issue", (None, "2")), ("both", (2, "2"))]
)
@pytest.mark.parametrize("raw", [[], ["2"], ["2 (副題)"], ["2", "第２巻（副題）"]])
def test_talker_matching_is_independent_of_output(talker, record, output, expected, raw):
    record = replace(record, title="作品名. 2", volumes=raw)
    talker.volume_output = output
    talker._source = Mock()
    talker.source.get.return_value = record
    for selector in ({"series_id": record.id}, {"issue_id": record.id}):
        md = talker.fetch_comic_data(**selector, issue_number="第２巻")
        assert (md.volume, md.issue) == expected
        with pytest.raises(TalkerDataError):
            talker.fetch_comic_data(**selector, issue_number="3")
    result = talker.fetch_issues_by_series_issue_num_and_year([record.id], "2", 2025)
    assert len(result) == 1 and (result[0].volume, result[0].issue) == expected
    assert not talker.fetch_issues_by_series_issue_num_and_year([record.id], "3", 2025)
    assert not talker.fetch_issues_by_series_issue_num_and_year([record.id], "2", 2024)
    md = talker.fetch_issues_in_series(record.id)[0]
    assert (md.volume, md.issue) == expected


@pytest.mark.parametrize("output", ["volume", "issue", "both"])
def test_conflicting_candidate_matching(talker, record, output):
    talker.volume_output = output
    talker._source = Mock()
    talker.source.get.return_value = replace(record, title="作品名. 31", volumes=["32"])
    for requested in ("31", "32"):
        with pytest.raises(TalkerDataError, match="巻番号に不一致"):
            talker.fetch_comic_data(series_id=record.id, issue_number=requested)
        assert not talker.fetch_issues_by_series_issue_num_and_year([record.id], requested, None)
    md = talker.fetch_comic_data(issue_id=record.id)
    assert md.volume is md.issue is None and "巻番号の不一致" in md.notes


@pytest.mark.parametrize(
    "volume,issue,expected", [(2, None, "2"), (2, "9", "2"), (None, "3", "3"), (0, "9", "0")]
)
def test_search_metadata_volume_priority(talker, record, volume, issue, expected):
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record], 1)
    talker.search_metadata(GenericMetadata(series="作品名", volume=volume, issue=issue))
    assert talker.source.search.call_args.args[0].issue == expected


def test_output_settings(talker, tmp_path):
    manager = settngs.Manager()
    register_talker_settings(manager, {talker.id: talker})
    setting = manager.definitions["Source jpbooks"].v["jpbooks_volume_output"]
    assert setting.default == "issue" and setting.file
    assert setting.choices == ["volume", "issue", "both"]
    for output in setting.choices:
        config = manager.parse_cmdline(["--jpbooks-volume-output", output])
        path = tmp_path / "settings.json"
        assert manager.save_file(config, path)
        restored, success = manager.parse_file(path)
        assert success and restored.values["Source jpbooks"]["jpbooks_volume_output"] == output
        talker.parse_settings({"jpbooks_volume_output": output})
        assert talker.volume_output == output
    talker.parse_settings({})
    assert talker.volume_output == "issue"
    with pytest.raises(ValueError):
        talker.parse_settings({"jpbooks_volume_output": "invalid"})
    assert not talker.check_status({"jpbooks_volume_output": "invalid"})[1]


@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
def test_host_merge_does_not_clear_issue(record, mode):
    incoming = to_metadata(replace(record, title="作品名", volumes=["2"]), volume_output="volume")
    existing = GenericMetadata(issue="9")
    existing.overlay(incoming, mode=mode)
    assert existing.issue == "9" and existing.volume == 2


def test_request_fallback_only_when_source_number_missing(talker, record):
    talker.volume_output = "volume"
    talker._source = Mock()
    talker.source.get.return_value = replace(record, title="作品名", volumes=[])
    md = talker.fetch_comic_data(series_id=record.id, issue_number="2")
    assert md.volume == 2 and md.issue is None
    assert "既存・要求巻: 2" in md.notes
    # A filter cannot claim that an unnumbered candidate proves the requested number.
    assert not talker.fetch_issues_by_series_issue_num_and_year([record.id], "2", None)
