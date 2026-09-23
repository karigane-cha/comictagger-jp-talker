"""Role mappings use actual ComicTagger credits; no HTTP or name guessing."""

from dataclasses import replace

import pytest
from comicapi.genericmetadata import Credit

from comictagger_jp_talker.mapping import map_credits, parse_responsibility, to_metadata


@pytest.mark.parametrize("wrapper", ["{}", "[{}]", "［{}］", "({})", "（{}）"])
@pytest.mark.parametrize(
    "label,roles",
    [
        *[(s, ("Writer",)) for s in ("著", "著者", "作", "文", "原作")],
        *[(s, ("Artist",)) for s in ("漫画", "画", "絵", "作画")],
        *[(s, ("Translator",)) for s in ("訳", "訳者", "翻訳", "監訳")],
        *[(s, ("Editor",)) for s in ("編", "編者", "編集")],
        ("編著", ("Writer", "Editor")),
        ("原作・脚本", ("Writer", "Scripter")),
        *[(s, ("Plotter",)) for s in ("原案", "構成")],
        *[(s, ("Scripter",)) for s in ("脚本", "シナリオ")],
        *[(s, ("Inker",)) for s in ("線画", "ペン入れ")],
        *[(s, ("Colorist",)) for s in ("彩色", "着色", "カラー")],
        ("下絵", ("Penciller",)),
        *[(s, ("Cover Artist",)) for s in ("表紙画", "表紙イラスト", "カバーイラスト", "カバー画", "装画")],
        *[(s, ("Letterer",)) for s in ("レタリング", "写植", "植字")],
        *[
            (s, ("Other",))
            for s in (
                "監修",
                "解説",
                "校閲",
                "企画",
                "写真",
                "撮影",
                "デザイン",
                "装丁",
                "校注",
                "注",
                "注釈",
                "解題",
                "協力",
                "監修協力",
                "編集協力",
                "作画原稿",
                "文字",
                "表紙",
                "カバー",
            )
        ],
    ],
)
def test_all_role_spellings(label, roles, wrapper):
    assert parse_responsibility("山田太郎 " + wrapper.format(label)) == [
        Credit("山田太郎", role) for role in roles
    ]


@pytest.mark.parametrize(
    "statement,person,role",
    [
        ("金城宗幸 原作", "金城宗幸", "Writer"),
        ("ノ村優介 漫画", "ノ村優介", "Artist"),
        ("でむにゃん 原作", "でむにゃん", "Writer"),
        ("炭酸だいすき 作画", "炭酸だいすき", "Artist"),
        ("ねことうふ [著]", "ねことうふ", "Writer"),
        ("ねことうふ ［著］", "ねことうふ", "Writer"),
        ("ねことうふ (著)", "ねことうふ", "Writer"),
        ("ねことうふ（著）", "ねことうふ", "Writer"),
        ("ねことうふ 著", "ねことうふ", "Writer"),
        ("山田太郎（監修）", "山田太郎", "Other"),
        ("種村季弘 解説", "種村季弘", "Other"),
        ("髙﨑𠮷野\U00020000\U000e0100　［ 著 ］ ", "髙﨑𠮷野\U00020000\U000e0100", "Writer"),
    ],
)
def test_reported_names(statement, person, role):
    assert parse_responsibility(statement) == [Credit(person, role)]


@pytest.mark.parametrize("person", ["A・B", "A, B", "A ; B", "Aほか", "John Smith", "金城, 宗幸"])
def test_never_split_people(person):
    assert parse_responsibility(person + " 著") == [Credit(person, "Writer")]
    assert parse_responsibility(person) == [Credit(person, "Other")]
    assert parse_responsibility(person, creator_fallback=True) == [Credit(person, "Writer")]


@pytest.mark.parametrize("suffix", ["[未知役割]", "［未知役割］", "(未知役割)", "（未知役割）", "特殊担当"])
@pytest.mark.parametrize("creator_fallback", [False, True])
def test_explicit_unknown_role_is_other(suffix, creator_fallback):
    assert parse_responsibility("山田太郎 " + suffix, creator_fallback=creator_fallback) == [
        Credit("山田太郎", "Other")
    ]


@pytest.mark.parametrize(
    "value",
    [
        "山田太郎",
        "山田 太郎",
        "山田太郎著",
        "山田太郎 未知語",
        "山田太郎 原作/脚本",
        "山田太郎 原作,脚本",
        "山田太郎 原作;脚本",
        "山田太郎 [著）",
        "山田太郎 [著",
        "山田太郎 [[著]]",
    ],
)
def test_ambiguous_and_malformed_statements_stay_intact(value):
    assert parse_responsibility(value) == [Credit(value, "Other")]


@pytest.mark.parametrize("value", ["", " ", "　"])
def test_empty_credit(value):
    assert parse_responsibility(value) == []


def test_sources_priority_deduplication_and_originals(record):
    responsibilities = ["山田太郎 編著", "山田太郎 [著]", "ねことうふ [著]"]
    contributors = ["山田太郎 編", "山田太郎 監修", "寄与者名", "別人 [未知役割]"]
    record = replace(record, responsibilities=responsibilities.copy(), contributors=contributors.copy())
    md = to_metadata(record)
    assert md.credits == [
        Credit("山田太郎", "Writer"),
        Credit("山田太郎", "Editor"),
        Credit("ねことうふ", "Writer"),
        Credit("山田太郎", "Other"),
        Credit("寄与者名", "Other"),
        Credit("別人", "Other"),
    ]
    assert record.responsibilities == responsibilities and record.contributors == contributors
    assert "責任表示: " + " / ".join(responsibilities) in md.notes
    assert "寄与者原表記: " + " / ".join(contributors) in md.notes


def test_creator_fallback_keeps_authority_names(record):
    creators = ["金城, 宗幸", "炭酸, だいすき", "山田太郎", "別人 [監修]", "人物 [未知役割]"]
    record = replace(record, responsibilities=[], creators=creators.copy(), contributors=["山田太郎 監修"])
    assert map_credits(record) == [
        Credit("金城, 宗幸", "Writer"),
        Credit("炭酸, だいすき", "Writer"),
        Credit("山田太郎", "Writer"),
        Credit("別人", "Other"),
        Credit("人物", "Other"),
        Credit("山田太郎", "Other"),
    ]
    assert record.creators == creators
    assert "著者原表記: " + " / ".join(creators) in to_metadata(record).notes
