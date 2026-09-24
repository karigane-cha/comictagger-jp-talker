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
        ("第0巻", "0"),
        ("０", "0"),
        ("第０巻", "0"),
    ],
)
def test_explicit_volume_number(raw, expected):
    assert explicit_volume_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("volume 1", "1"),
        ("Volume 1", "1"),
        ("volume 12", "12"),
        ("Volume 12", "12"),
        ("volume １", "1"),
        ("volume 0", "0"),
        ("Volume 0", "0"),
        ("volume ０", "0"),
        ("vol.1", "1"),
        ("vol. 1", "1"),
        ("Vol.1", "1"),
        ("Vol. 1", "1"),
        ("VOL.1", "1"),
        ("vol.31", "31"),
        ("vol. 31", "31"),
        ("Vol.31", "31"),
        ("vol.0", "0"),
        ("vol. 0", "0"),
    ],
)
def test_english_explicit_volume_number(raw, expected):
    assert explicit_volume_number(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "volume",
        "Volume",
        "volume one",
        "volume A",
        "volume 1.5",
        "volume 1-2",
        "volume 1/2",
        "volume 2024",
        "volume1",
        "vol.",
        "Vol",
        "vol.one",
        "vol.A",
        "vol.1.5",
        "vol.1-2",
        "vol.1/2",
    ],
)
def test_english_explicit_volume_rejects_unsafe_values(raw):
    assert explicit_volume_number(raw) is None


@pytest.mark.parametrize(
    "title,raw,series,number",
    [
        ("My Girl. vol.31", "vol.31", "My Girl", "31"),
        (
            "ご注文はうさぎですか? : アンソロジーコミック. volume 1",
            "volume 1",
            "ご注文はうさぎですか? : アンソロジーコミック",
            "1",
        ),
        ("ご注文はうさぎですか? = Is the order a rabbit? 7", "7", "ご注文はうさぎですか?", "7"),
    ],
)
@pytest.mark.parametrize("mode", ["volume", "issue", "both"])
def test_phase1_series_and_number_regressions(record, title, raw, series, number, mode):
    record = replace(record, title=title, volumes=[raw], series_titles=["出版レーベル"])
    originals = (record.title, record.volumes.copy(), record.series_titles.copy())

    resolved = resolve_record_number(record)
    metadata = to_metadata(record, volume_output=mode)

    assert (resolved.explicit, resolved.inferred, resolved.value, resolved.conflict) == (
        number,
        number,
        number,
        False,
    )
    assert metadata.series == series
    assert metadata.title == title
    assert metadata.volume == (int(number) if mode in ("volume", "both") else None)
    assert metadata.issue == (number if mode in ("issue", "both") else None)
    assert (record.title, record.volumes, record.series_titles) == originals
    assert "NDL 巻次（原データ）: " + raw in metadata.notes
    assert "NDL シリーズ表記（原データ）: 出版レーベル" in metadata.notes
    assert "NDL 巻次を整数として解釈できない" not in metadata.notes
    assert "巻番号の不一致" not in metadata.notes


@pytest.mark.parametrize(
    ("mode", "volume", "issue"),
    [("volume", 1, None), ("issue", None, "1"), ("both", 1, "1")],
)
def test_english_volume_record_keeps_raw_and_outputs_logical_number(record, mode, volume, issue):
    title = "ご注文はうさぎですか? volume 1"
    record = replace(record, title=title, volumes=["volume 1"], series_titles=["出版レーベル"])

    resolved = resolve_record_number(record)
    metadata = to_metadata(record, volume_output=mode)

    assert (resolved.explicit, resolved.inferred, resolved.value, resolved.conflict) == ("1", "1", "1", False)
    assert metadata.title == record.title == title
    assert metadata.series == "ご注文はうさぎですか?"
    assert (metadata.volume, metadata.issue) == (volume, issue)
    assert record.volumes == ["volume 1"]
    assert "NDL 巻次（原データ）: volume 1" in metadata.notes
    assert "NDL シリーズ表記（原データ）: 出版レーベル" in metadata.notes
    assert "巻番号の不一致" not in metadata.notes


@pytest.mark.parametrize("raw", ["volume 1.5", "volume 1-2", "volume 1/2", "volume A", "volume 2024"])
def test_unsafe_english_volume_record_is_unset(record, raw):
    record = replace(record, title="作品名 " + raw, volumes=[raw])
    resolved = resolve_record_number(record)
    metadata = to_metadata(record, volume_output="both")

    assert resolved.value is None
    assert (metadata.volume, metadata.issue) == (None, None)
    assert record.volumes == [raw]
    assert "NDL 巻次（原データ）: " + raw in metadata.notes


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
    assert md.volume is md.issue is None
    assert "NDL 巻次（原データ）: " + raw in md.notes


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


@pytest.mark.parametrize(
    "raw",
    [
        "上", "下", "上巻", "下巻", "前編", "後編", "外伝", "別巻", "番外編",
        "特別編", "完", "1/2", "1-2", "1.5", "12.5",
    ],
)
@pytest.mark.parametrize("output", ["volume", "issue", "both"])
def test_noninteger_numbers(record, raw, output):
    record = replace(record, title="作品名", volumes=[raw])
    resolved = resolve_record_number(record)
    assert resolved.explicit is resolved.inferred is resolved.value is None
    assert not resolved.conflict
    md = to_metadata(record, volume_output=output)
    assert md.volume is md.issue is None
    assert "NDL 巻次（原データ）: " + raw in md.notes
    assert record.volumes == [raw]


@pytest.mark.parametrize("raw", ["上", "1/2"])
def test_unknown_explicit_blocks_unverified_title_and_request_numbers(record, raw):
    record = replace(record, title="作品名. 1", volumes=[raw])
    resolved = resolve_record_number(record, "2")
    assert resolved.explicit is None and resolved.inferred == "1"
    assert resolved.requested == "2" and resolved.value is None
    assert not resolved.conflict
    md = to_metadata(record, existing_issue="2", volume_output="both")
    assert md.volume is md.issue is None
    assert "NDL 巻次（原データ）: " + raw in md.notes
    assert "タイトル推定巻: 1" in md.notes
    assert "巻番号の不一致" not in md.notes


def test_unknown_request_is_not_logical_number(record):
    record = replace(record, title="作品名", volumes=[])
    resolved = resolve_record_number(record, "上")
    assert resolved.requested is resolved.value is None
    assert to_metadata(record, existing_issue="上", volume_output="both").issue is None


@pytest.mark.parametrize("raw", ["0", "第0巻", "０", "第０巻", "volume 0", "Volume 0", "volume ０"])
@pytest.mark.parametrize(
    "output,expected", [("volume", (0, None)), ("issue", (None, "0")), ("both", (0, "0"))]
)
def test_zero_volume_is_a_safe_logical_integer(record, raw, output, expected):
    record = replace(record, title="作品名", volumes=[raw])
    resolved = resolve_record_number(record)
    assert (resolved.explicit, resolved.value, resolved.conflict) == ("0", "0", False)
    md = to_metadata(record, volume_output=output)
    assert (md.volume, md.issue) == expected
    assert "NDL 巻次（原データ）: " + raw in md.notes


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
