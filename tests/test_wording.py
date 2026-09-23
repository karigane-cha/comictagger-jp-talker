"""Authored prose has spacing; literal identifiers and bibliographic examples stay intact."""

import re
from pathlib import Path

import settngs
from comictaggerlib.ctsettings.plugin import register_talker_settings

JAPANESE = r"\u3041-\u3096\u30a1-\u30fa\u30fc\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
JOINED = re.compile(rf"[A-Za-z0-9][{JAPANESE}]|[{JAPANESE}][A-Za-z0-9]")
COMPOUNDS = (
    "チェックディジット",
    "ネットワークテスト",
    "ローカルプラグイン",
    "キャッシュバージョン",
    "キャッシュエントリー",
    "システムフォント",
    "オプトインテスト",
    "サブディレクトリ",
    "タグプラグイン",
    "テキストエディター",
    "バックスラッシュ",
)


def assert_readable(text):
    assert not JOINED.search(text), text
    assert not any(word in text for word in COMPOUNDS), text


def test_markdown_prose_spacing():
    root = Path(__file__).resolve().parents[1]
    for path in [root / "README.md", *(root / "docs").glob("*.md")]:
        text = path.read_text(encoding="utf-8")
        # Commands, API literals, original book names and link targets are data.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`]+`|\]\([^)]*\)", " ", text)
        for line in text.splitlines():
            assert_readable(line)


def test_plugin_ui_wording(talker):
    manager = settngs.Manager()
    register_talker_settings(manager, {talker.id: talker})
    for definition in manager.definitions["Source jpbooks"].v.values():
        for text in (definition.display_name, definition.help):
            if text:
                assert_readable(text)
    for text in (talker.name, talker.about, talker.attribution, talker.check_status({"jpbooks_key": "x"})[0]):
        assert_readable(re.sub(r"<[^>]*>", "", text))
