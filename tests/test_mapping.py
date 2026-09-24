from dataclasses import replace

import pytest
from comicapi.genericmetadata import Credit, GenericMetadata, MetadataOrigin

from comictagger_jp_talker.mapping import (
    infer_volume,
    language_code,
    parse_responsibility,
    publication_date,
    resolve_record_number,
    to_metadata,
    to_series,
)


@pytest.mark.parametrize(
    "title,series,number",
    [
        ("キングダム. 74", "キングダム", "74"),
        ("キングダム 74", "キングダム", "74"),
        ("キングダム 第７４巻", "キングダム", "74"),
        ("キングダム第74巻", "キングダム", "74"),
        ("キングダム．７４", "キングダム", "74"),
        ("20世紀少年 2", "20世紀少年", "2"),
        ("3月のライオン １７", "3月のライオン", "17"),
        ("20世紀少年", "20世紀少年", None),
        ("3月のライオン", "3月のライオン", None),
        ("7SEEDS", "7SEEDS", None),
        ("86―エイティシックス―", "86―エイティシックス―", None),
        ("1984", "1984", None),
        ("東京 2024", "東京 2024", None),
        ("作品 1.5", "作品 1.5", None),
        ("作品 1-2", "作品 1-2", None),
        ("作品74", "作品74", None),
        ("作品 （74）", "作品 （74）", None),
        ("", "", None),
    ],
)
def test_volume(title, series, number):
    assert infer_volume(title) == (series, number)


@pytest.mark.parametrize(
    ("title", "series", "number"),
    [
        ("こちら葛飾区亀有公園前派出所. 1", "こちら葛飾区亀有公園前派出所", "1"),
        ("こちら葛飾区亀有公園前派出所. 第1巻", "こちら葛飾区亀有公園前派出所", "1"),
        ("作品名．1", "作品名", "1"),
        ("作品名. 1", "作品名", "1"),
        ("作品名． 1", "作品名", "1"),
        ("作品名． 第１巻", "作品名", "1"),
        ("パタリロ! : 選集. 1 (国王誕生の巻)", "パタリロ! : 選集", "1"),
        ("パタリロ! : 選集 42(越後屋波多利郎江戸日記の巻)", "パタリロ! : 選集", "42"),
        ("作品名 12（副題）", "作品名", "12"),
        ("作品名! 1", "作品名!", "1"),
        ("作品名? 1", "作品名?", "1"),
        ("作品名 : 新シリーズ. 1", "作品名 : 新シリーズ", "1"),
        ("作品名・新章. 1", "作品名・新章", "1"),
        ("作品名.", "作品名.", None),
        ("作品名．", "作品名．", None),
        ("作品名!", "作品名!", None),
        ("作品名?", "作品名?", None),
        ("作品名 第1巻", "作品名", "1"),
        ("作品名 第１巻", "作品名", "1"),
        ("作品名 第12巻 (副題)", "作品名", "12"),
        ("作品名．１２", "作品名", "12"),
        ("20世紀少年", "20世紀少年", None),
        ("作品名2024", "作品名2024", None),
        ("作品名 2024年版", "作品名 2024年版", None),
        ("作品名 1.5", "作品名 1.5", None),
        ("作品名 1-2", "作品名 1-2", None),
        ("作品名 1/2", "作品名 1/2", None),
        ("作品名 (完全版)", "作品名 (完全版)", None),
        ("作品名（新装版）", "作品名（新装版）", None),
    ],
)
def test_volume_delimiter_is_removed_only_with_a_recognized_number(title, series, number):
    assert infer_volume(title) == (series, number)


@pytest.mark.parametrize(
    ("title", "series", "number"),
    [
        ("ご注文はうさぎですか? volume 1", "ご注文はうさぎですか?", "1"),
        ("作品名 Volume 2", "作品名", "2"),
        ("作品名 volume 12", "作品名", "12"),
        ("作品名 Volume 12", "作品名", "12"),
        ("作品名 volume １", "作品名", "1"),
        ("作品名 volume 0", "作品名", "0"),
        ("作品名 Volume 0", "作品名", "0"),
        ("作品名 volume ０", "作品名", "0"),
        ("作品名! volume 1", "作品名!", "1"),
        ("作品名? volume 1", "作品名?", "1"),
        ("作品名 : 新章 volume 1", "作品名 : 新章", "1"),
        ("作品名：新章 volume 1", "作品名：新章", "1"),
        ("作品名・新章 volume 1", "作品名・新章", "1"),
        ("作品名&新章 volume 1", "作品名&新章", "1"),
        ("作品名＆新章 volume 1", "作品名＆新章", "1"),
        ("作品名-新章 volume 1", "作品名-新章", "1"),
        ("作品名～新章 volume 1", "作品名～新章", "1"),
        ("作品名〜新章 volume 1", "作品名〜新章", "1"),
        ("作品名 volume", "作品名 volume", None),
        ("作品名 Volume", "作品名 Volume", None),
        ("作品名 volume one", "作品名 volume one", None),
        ("作品名 volume A", "作品名 volume A", None),
        ("作品名 volume 1.5", "作品名 volume 1.5", None),
        ("作品名 volume 1-2", "作品名 volume 1-2", None),
        ("作品名 volume 1/2", "作品名 volume 1/2", None),
        ("作品名 volume 2024", "作品名 volume 2024", None),
        ("作品名volume1", "作品名volume1", None),
    ],
)
def test_english_volume_marker_only_with_safe_integer(title, series, number):
    assert infer_volume(title) == (series, number)


@pytest.mark.parametrize(
    "title,series,number",
    [
        ("My Girl. vol.31", "My Girl", "31"),
        ("My Girl. vol. 31", "My Girl", "31"),
        ("My Girl. Vol.31", "My Girl", "31"),
        ("My Girl. Vol. 31", "My Girl", "31"),
        ("My Girl. VOL.1", "My Girl", "1"),
        ("作品名 vol.1", "作品名", "1"),
        ("作品名! vol.1", "作品名!", "1"),
        ("作品名 : 新章 vol.1", "作品名 : 新章", "1"),
        ("作品名．volume 2", "作品名", "2"),
        ("作品名. Volume 12", "作品名", "12"),
        ("作品名． Volume 1", "作品名", "1"),
        (
            "ご注文はうさぎですか? : アンソロジーコミック. volume 1",
            "ご注文はうさぎですか? : アンソロジーコミック",
            "1",
        ),
        ("ご注文はうさぎですか? = Is the order a rabbit? 7", "ご注文はうさぎですか?", "7"),
        ("作品名 = English title 12", "作品名", "12"),
        ("A = B 1", "A = B", "1"),
        ("作品名 = 新装版 1", "作品名 = 新装版", "1"),
        ("作品名=English 1", "作品名=English", "1"),
    ],
)
def test_marked_volume_and_safe_parallel_title(title, series, number):
    assert infer_volume(title) == (series, number)


@pytest.mark.parametrize(
    "title",
    [
        "My Girl.",
        "作品名.",
        "作品名．",
        "作品名!",
        "作品名?",
        "A = B",
        "作品名 = 新装版",
        "作品名 volume",
        "作品名 vol.",
        "作品名 Vol",
        "作品名 vol.one",
        "作品名 vol.A",
        "作品名 vol.1.5",
        "作品名 vol.1-2",
        "作品名 vol.1/2",
    ],
)
def test_marker_and_punctuation_without_safe_volume_stay_raw(title):
    assert infer_volume(title) == (title, None)


def test_vol_marker_does_not_match_inside_a_word():
    assert infer_volume("evolve 1") == ("evolve", "1")


def test_ndl_dotted_number_keeps_original_title_volume_and_imprint(record):
    record = replace(
        record,
        title="こちら葛飾区亀有公園前派出所. 第1巻",
        volumes=["第1巻"],
        series_titles=["ジャンプ・コミックス"],
    )

    resolved = resolve_record_number(record)
    metadata = to_metadata(record)

    assert resolved.explicit == resolved.inferred == resolved.value == "1"
    assert not resolved.conflict
    assert metadata.title == record.title
    assert metadata.series == "こちら葛飾区亀有公園前派出所"
    assert metadata.issue == "1"
    assert record.volumes == ["第1巻"]
    assert "NDL 巻次（原データ）: 第1巻" in metadata.notes
    assert "NDL シリーズ表記（原データ）: ジャンプ・コミックス" in metadata.notes


@pytest.mark.parametrize(
    "title,series,number",
    [
        ("パタリロ! : 選集. 1 (国王誕生の巻)", "パタリロ! : 選集", "1"),
        ("パタリロ! : 選集 42(越後屋波多利郎江戸日記の巻)", "パタリロ! : 選集", "42"),
        ("パタリロ! : 選集 46 (平安大江戸絵巻の巻)", "パタリロ! : 選集", "46"),
        ("作品名. 1 (副題)", "作品名", "1"),
        ("作品名．1（副題）", "作品名", "1"),
        ("作品名 1 (副題)", "作品名", "1"),
        ("作品名 1（副題）", "作品名", "1"),
        ("作品名 第1巻 (副題)", "作品名", "1"),
        ("作品名 第1巻（副題）", "作品名", "1"),
        ("作品名 42(副題)", "作品名", "42"),
        ("作品名 42（副題）", "作品名", "42"),
        ("作品名 12（副題）", "作品名", "12"),
        ("作品名 第12巻 (副題)", "作品名", "12"),
        ("作品名．１２　（新装版）", "作品名", "12"),
        ("作品名. 12", "作品名", "12"),
        ("作品名 12", "作品名", "12"),
        ("作品名 第12巻", "作品名", "12"),
        ("作品名．１２", "作品名", "12"),
    ],
)
def test_volume_with_optional_subtitle(title, series, number):
    assert infer_volume(title) == (series, number)


@pytest.mark.parametrize(
    "title",
    [
        "20世紀少年 : 本格科学冒険漫画",
        "作品名 (完全版)",
        "作品名（新装版）",
        "作品名 2024年版",
        "作品名 1.5",
        "作品名 1-2",
        "作品名 2024 (新版)",
        "作品名2024",
        "作品名 1.5 (副題)",
        "作品名 １．５（副題）",
        "作品名 1-2 (副題)",
        "作品名1 (副題)",
        "作品名 1 (副題 (完全版))",
        "作品名 1（副題（完全版））",
        "作品名 1 (副題) (特装版)",
        "作品名 1（副題）（特装版）",
        "作品名 1 (副題）",
        "作品名 1（副題)",
        "作品名 1 (副題",
        "作品名 1 ()",
        "作品名 1（）",
    ],
)
def test_ambiguous_subtitles_are_not_volumes(title):
    assert infer_volume(title) == (title, None)


def test_series_symbols_are_preserved():
    series = "作品!?:：・&＆-～〜髙﨑𠮷"
    assert infer_volume(series + ". １（特装版）") == (series, "1")


@pytest.mark.parametrize("output", ["volume", "issue", "both"])
@pytest.mark.parametrize("raw", [[], ["１"], ["2"]])
def test_subtitle_metadata_keeps_originals(record, output, raw):
    title = "パタリロ! : 選集. 1 (国王誕生の巻)"
    record = replace(record, title=title, volumes=raw.copy(), series_titles=["出版レーベル"])
    resolved = resolve_record_number(record)
    assert resolved.inferred == "1"
    assert resolved.conflict is (raw == ["2"])
    md = to_metadata(record, volume_output=output)
    assert md.series == "パタリロ! : 選集"
    assert md.title == record.title == title
    assert record.volumes == raw and record.series_titles == ["出版レーベル"]
    assert md.volume == (1 if output != "issue" and not resolved.conflict else None)
    assert md.issue == ("1" if output != "volume" and not resolved.conflict else None)
    assert to_metadata(record, existing_series="既存作品名").series == "既存作品名"
    candidate = to_series(record)
    assert candidate.name == title
    assert "Series: パタリロ! : 選集<br>" in candidate.description
    assert not candidate.aliases


@pytest.mark.parametrize(
    "text,role",
    [
        ("作家 著", "Writer"),
        ("作家 原作", "Writer"),
        ("画家 作画", "Artist"),
        ("翻訳家（訳）", "Translator"),
        ("編集者 編", "Editor"),
        ("役割不明", "Other"),
    ],
)
def test_roles(text, role):
    credits = parse_responsibility(text)
    assert isinstance(credits[0], Credit)
    assert credits[0].role == role


def test_mapping(record):
    md = to_metadata(record)
    assert isinstance(md, GenericMetadata)
    assert md.data_origin == MetadataOrigin("jpbooks", "Japanese Books")
    assert md.series == "架空の漫画・髙﨑𠮷野〜旅―（新版）"
    assert md.issue == "74" and md.volume is None and md.issue_count is None
    assert md.publisher == "架空出版"
    assert md.gtin == "9784885942877"
    assert (md.year, md.month, md.day) == (2025, 11, 19)
    assert md.language == "ja"
    assert "テスト用あらすじ" in md.description and "所蔵" not in md.description
    assert md.credits == [
        Credit("架空太郎", "Writer"),
        Credit("架空花子", "Artist"),
        Credit("翻訳次郎", "Translator"),
    ]
    assert md.web_links[0].url == record.url
    assert "ISBN: 4-88594-287-X" in md.notes
    assert not md.tags and not md.genres
    assert to_metadata(record, subject_tags=True).tags == {"漫画"}


def test_priorities(record):
    assert to_metadata(record, existing_series="既存", existing_issue="3").series == "既存"
    record = replace(record, series_titles=[], volumes=[])
    md = to_metadata(record, existing_series="既存", existing_issue="3")
    assert md.series == "既存" and md.issue == "3"
    md = to_metadata(record)
    assert md.series == "架空の漫画・髙﨑𠮷野〜旅―（新版）" and md.issue == "74"
    assert md.title == record.title


@pytest.mark.parametrize(
    "series_titles",
    [[], ["ジャンプコミックス"], ["講談社コミックス"], ["雑誌名", "出版叢書", "別レーベル"]],
)
@pytest.mark.parametrize("title,expected", [("作品. 74", "作品"), ("20世紀少年", "20世紀少年")])
def test_bibliographic_series_is_not_work_identity(record, series_titles, title, expected):
    record = replace(record, title=title, series_titles=series_titles.copy())
    md = to_metadata(record)
    candidate = to_series(record)
    assert md.series == expected
    assert to_metadata(record, existing_series="既存の作品名").series == "既存の作品名"
    assert md.title == candidate.name == title
    assert not candidate.aliases
    assert record.series_titles == series_titles
    if series_titles:
        raw_note = "NDL シリーズ表記（原データ）: " + " / ".join(series_titles)
        assert raw_note in md.notes
        assert raw_note in candidate.description
    else:
        assert "NDL シリーズ表記" not in md.notes + candidate.description


def test_raw_series_detail_is_html_escaped(record):
    record = replace(record, series_titles=["叢書 <特装版> & 別冊"])
    assert "叢書 <特装版> & 別冊" in to_metadata(record).notes
    assert "叢書 &lt;特装版&gt; &amp; 別冊" in to_series(record).description
    assert not to_series(record).aliases


@pytest.mark.parametrize(
    "codes,expected",
    [
        (["jpn"], "ja"),
        (["ja"], "ja"),
        (["eng"], "en"),
        (["ger"], "de"),
        (["zzz"], None),
        (["mul"], None),
        ([], None),
    ],
)
def test_language(codes, expected):
    assert language_code(codes) == expected


@pytest.mark.parametrize(
    "issued,dates,expected",
    [
        (["2024-02-29"], [], (2024, 2, 29)),
        (["2023-02-29"], [], (None, None, None)),
        (["2025-13"], [], (None, None, None)),
        (["2025"], ["2026.1.1"], (2025, None, None)),
        (["2025-02"], ["2025.3.1"], (2025, 2, None)),
        (["昭和60年"], [], (None, None, None)),
    ],
)
def test_dates(record, issued, dates, expected):
    assert publication_date(replace(record, issued=issued, dates=dates)) == expected


def test_unicode_preserved(record):
    text = "漢字ひらがなカタカナ１２３・〜―（）髙﨑𠮷\U00020000\U000e0100 は\u3099 e\u0301"
    assert to_metadata(replace(record, title=text)).title == text
    # Python surrogate code units can be held without mutation; invalid XML cannot serialize them.
    assert to_metadata(replace(record, title="文字\ud842\udfb7")).title == "文字\ud842\udfb7"


def test_ambiguous_isbns_not_arbitrarily_chosen(record):
    record.isbns += ["9784101010137"]
    assert to_metadata(record).gtin is None
    assert to_metadata(record, preferred_isbn="9784101010137").gtin == "9784101010137"


def test_tags_bounded(record):
    record.subjects = [f"件名{i}" for i in range(50)]
    assert len(to_metadata(record, subject_tags=True).tags) == 10


@pytest.mark.parametrize("invalid", ["2025-00", "2025-01-00", "2025.0.1", "0000-01-01"])
def test_zero_date_components_rejected(record, invalid):
    assert publication_date(replace(record, issued=[invalid], dates=[])) == (None, None, None)
