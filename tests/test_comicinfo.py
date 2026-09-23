"""Round trips through the installed ComicTagger archives and tag writers."""

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace

import pytest
from comicapi.comicarchive import ComicArchive
from comictaggerlib.md import read_selected_tags
from PIL import Image

from comictagger_jp_talker.mapping import to_metadata


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("output", ["volume", "issue", "both"])
@pytest.mark.parametrize("subtitle", [False, True])
def test_cbz_comicinfo_roundtrip(tmp_path, record, tag, output, subtitle):
    if subtitle:
        record = replace(record, title=record.title + " (副題)", volumes=["７４ (副題)"])
    if tag == "cix":
        pytest.importorskip("comicinfoxml")
    path = tmp_path / f"日本語-{tag}.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    # Test data setup only. Production uses no CBZ reader/writer of its own.
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    md = to_metadata(record, volume_output=output)
    assert md.series == "架空の漫画・髙﨑𠮷野〜旅―（新版）"
    archive = ComicArchive(path)
    assert archive.write_tags(md, tag)
    recovered = ComicArchive(path).read_tags(tag)
    assert recovered.title == md.title
    assert recovered.series == md.series and recovered.issue == md.issue
    assert recovered.volume == md.volume
    if subtitle:
        assert "NDL 巻次（原データ）: ７４ (副題)" in recovered.notes
        assert "巻番号の不一致" not in recovered.notes
    assert recovered.publisher == md.publisher
    assert (recovered.year, recovered.month, recovered.day) == (2025, 11, 19)
    assert recovered.language == "ja"
    assert recovered.description == md.description
    assert any(c.person == "架空太郎" and c.role.casefold() == "writer" for c in recovered.credits)
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("ComicInfo.xml"))
    assert root.findtext("LanguageISO") == "ja"
    assert root.findtext("Title") == md.title
    assert root.findtext("Series") == md.series
    assert root.findtext("Publisher") == md.publisher
    assert root.findtext("Year") == "2025"
    assert root.findtext("Month") == "11"
    assert root.findtext("Day") == "19"
    assert root.findtext("Summary") == md.description
    assert root.findtext("Web") == record.url
    assert md.format is None and root.find("Format") is None
    assert root.findtext("PageCount") == "1"  # Host counts the archive page.
    assert root.findtext("Number") == (None if output == "volume" else "74")
    assert root.findtext("Volume") == (None if output == "issue" else "74")
    assert "ISBN: 4-88594-287-X" in root.findtext("Notes")
    assert "NDL シリーズ表記（原データ）: 架空の漫画" in root.findtext("Notes")
    if tag == "cix":
        assert recovered.gtin == "9784885942877"
        assert root.findtext("GTIN") == "9784885942877"
        assert root.findtext("Writer") == "架空太郎"
        assert root.findtext("Penciller") == "架空花子"
        assert root.findtext("Inker") == "架空花子"
        assert root.findtext("Translator") == "翻訳次郎"
        # The GUI re-reads the selected READ tags immediately after saving.
        # CIX writes GTIN correctly, but selecting CR to read hides it in the form.
        from_cr, used, error = read_selected_tags(["cr"], ComicArchive(path))
        assert error is None and used == ["cr"]
        assert from_cr.gtin is None
        from_cix, used, error = read_selected_tags(["cix"], ComicArchive(path))
        assert error is None and used == ["cix"]
        assert from_cix.gtin == md.gtin
        # A CR read doesn't delete the saved GTIN: distinguish display from data loss.
        with zipfile.ZipFile(path) as saved:
            assert ET.fromstring(saved.read("ComicInfo.xml")).findtext("GTIN") == md.gtin
    else:
        assert recovered.gtin is None  # beta.9's legacy CR writer has no GTIN mapping.
        assert root.find("GTIN") is None


@pytest.mark.parametrize("raw", ["上", "1/2"])
@pytest.mark.parametrize(
    "edition,material", [("Special", "Book"), ("新装版", "図書 http://ndl.go.jp/ndltype/Book")]
)
def test_opaque_volume_and_ndl_format_sources_do_not_write_cix_tags(
    tmp_path, record, raw, edition, material
):
    record = replace(record, title="作品名", volumes=[raw], editions=[edition], material_types=[material])
    path = tmp_path / "safe.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    md = to_metadata(record, volume_output="both")
    assert md.volume is md.issue is md.format is None
    assert ComicArchive(path).write_tags(md, "cix")
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("ComicInfo.xml"))
    assert root.find("Number") is root.find("Volume") is root.find("Format") is None
    notes = root.findtext("Notes")
    assert "NDL 巻次（原データ）: " + raw in notes
    assert "版: " + edition in notes and "資料種別: " + material in notes


@pytest.mark.xfail(
    strict=True,
    reason="ComicTagger 1.6.0b9 CIX writer omits integer Volume 0 via a truthiness check",
)
def test_zero_volume_is_written_as_zero_in_cix(tmp_path, record):
    record = replace(record, title="作品名", volumes=["第０巻"])
    path = tmp_path / "zero.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    md = to_metadata(record, volume_output="both")
    assert (md.volume, md.issue, md.format) == (0, "0", None)
    assert ComicArchive(path).write_tags(md, "cix")
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("ComicInfo.xml"))
    assert root.findtext("Number") == "0"
    assert root.findtext("Volume") == "0"


def test_zero_issue_is_written_as_zero_in_cix(tmp_path, record):
    record = replace(record, title="作品名", volumes=["第０巻"])
    path = tmp_path / "zero-issue.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    md = to_metadata(record)  # Default Issue only mode.
    assert (md.volume, md.issue) == (None, "0")
    assert ComicArchive(path).write_tags(md, "cix")
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("ComicInfo.xml"))
    assert root.findtext("Number") == "0"
    assert root.find("Volume") is None


def test_cix_role_storage_limits_and_source_notes(tmp_path, record):
    pytest.importorskip("comicinfoxml")
    record = replace(
        record,
        responsibilities=[
            "著者 [著]",
            "漫画家 漫画",
            "原案者 原案",
            "脚本家 脚本",
            "線画家 線画",
            "彩色者 彩色",
            "表紙作家 表紙画",
            "下絵作家 下絵",
            "写植者 写植",
            "編集者 編",
            "翻訳者 監訳",
            "監修者 監修",
            "山田太郎 編著",
        ],
        contributors=["寄与者 [未知役割]"],
    )
    path = tmp_path / "roles.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    md = to_metadata(record)
    assert ComicArchive(path).write_tags(md, "cix")
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("ComicInfo.xml"))
    # Host 1.6.0b9 / comicinfoxml 0.5.1 coalesce roles; do not change derived credits to match.
    expected = {
        "Writer": {"著者", "原案者", "脚本家", "山田太郎"},
        "Penciller": {"漫画家", "下絵作家"},
        "Inker": {"漫画家", "線画家"},
        "Colorist": {"彩色者"},
        "CoverArtist": {"表紙作家"},
        "Letterer": {"写植者"},
        "Editor": {"編集者", "山田太郎"},
        "Translator": {"翻訳者"},
    }
    for tag, names in expected.items():
        assert set(root.findtext(tag).split(",")) == names
    assert root.find("Other") is None
    assert root.find("Plotter") is None and root.find("Scripter") is None
    restored = ComicArchive(path).read_tags("cix")
    assert "責任表示: " + " / ".join(record.responsibilities) in restored.notes
    assert "寄与者原表記: 寄与者 [未知役割]" in restored.notes
    assert any(c.role == "Plotter" for c in md.credits)
    assert any(c.person == "監修者" and c.role == "Other" for c in md.credits)
