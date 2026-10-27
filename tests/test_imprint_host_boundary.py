"""Synthetic CBZ observations of installed host APIs, never MADB authority evidence.

Each archive experiment retains its XML and an observation.json under pytest tmp_path.
Expected raw, XML-parsed, and reader values are separate; inputs are never cleaned.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from importlib.metadata import version
from types import SimpleNamespace
from unittest.mock import Mock
from xml.etree import ElementTree as ET

import pytest
import settngs
from comicapi import merge, utils
from comicapi.comicarchive import ComicArchive, load_archive_plugins, load_tag_plugins, tags
from comicapi.genericmetadata import GenericMetadata
from comictaggerlib.cli import CLI
from comictaggerlib.ctsettings import register_commandline_settings, register_file_settings
from comictaggerlib.md import prepare_metadata, read_selected_tags
from comictaggerlib.resulttypes import OnlineMatchResults, Status
from PIL import Image

# Explicit expected observations, not normalization of the test inputs.
# name, raw metadata, XML parser text, reader metadata
VALUES = [
    ("none", None, None, None),
    ("empty", "", None, None),
    ("ascii-space", "   ", "   ", None),
    ("wide-space", "\u3000\u3000", "\u3000\u3000", None),
    ("japanese", "架空文庫", "架空文庫", "架空文庫"),
    ("alphanumeric", "Label A123", "Label A123", "Label A123"),
    ("outer", " \u3000架空文庫\u3000 ", " \u3000架空文庫\u3000 ", "架空文庫"),
    ("inner-space", "架空  文庫", "架空  文庫", "架空  文庫"),
    ("cr", "架空\r文庫", "架空\n文庫", "架空\n文庫"),
    ("lf", "架空\n文庫", "架空\n文庫", "架空\n文庫"),
    ("crlf", "架空\r\n文庫", "架空\n文庫", "架空\n文庫"),
    ("tab", "架空\t文庫", "架空\t文庫", "架空\t文庫"),
    ("newline-tab", "架空\n\t文庫", "架空\n\t文庫", "架空\n\t文庫"),
    ("xml-special", "A<&>\"'文庫", "A<&>\"'文庫", "A<&>\"'文庫"),
    ("non-bmp", "𠮷📚文庫", "𠮷📚文庫", "𠮷📚文庫"),
]
EXISTING = [VALUES[i] for i in (0, 1, 2, 3, 4, 5, 6, 12)]
INCOMING = ("none", "empty", "normal", "same", "different", "outer")


def host_config():
    """Use actual registered defaults, without loading user config or host startup."""
    load_tag_plugins()
    manager = settngs.Manager()
    register_file_settings(manager)
    register_commandline_settings(manager, False)
    return settngs.get_namespace(manager.defaults(), file=True, cmdline=True)[0]


def cbz(tmp_path, name="synthetic"):
    path = tmp_path / f"{name}.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    return path


def metadata(value, **kwargs):
    return GenericMetadata(is_empty=False, series="Synthetic boundary", imprint=value, **kwargs)


def observe(path):
    # Read ZIP bytes directly: host read_raw_tags() reserializes XML and loses CR.
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("ComicInfo.xml")
    try:
        root = ET.fromstring(raw)
        parsed = root.findtext("Imprint")
        present = root.find("Imprint") is not None
        error = None
    except ET.ParseError:
        parsed = present = None
        error = "ParseError"
    return {
        "xml": raw.decode("utf-8"),
        "imprint_element": present,
        "parsed": parsed,
        "parse_error": error,
        "readers": {tag: ComicArchive(path).read_tags(tag).imprint for tag in ("cr", "cix")},
        "has_tags": {tag: ComicArchive(path).has_tags(tag) for tag in ("cr", "cix")},
    }


def record_observation(tmp_path, **data):
    (tmp_path / "observation.json").write_text(
        json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def incoming_value(kind, old):
    return {
        "none": (None, None),
        "empty": ("", None),
        "normal": ("取得文庫", "取得文庫"),
        "same": (old[1], old[3]),
        "different": ("別の文庫", "別の文庫"),
        "outer": (" \u3000取得文庫\u3000 ", "取得文庫"),
    }[kind]


def test_registered_host_defaults_and_versions():
    assert version("comictagger") == "1.6.0b9"
    assert version("comicinfoxml") == "0.5.1"
    config = host_config()
    assert config.Metadata_Options__metadata_merge == merge.Mode.OVERLAY
    assert config.Metadata_Options__tag_merge == merge.Mode.OVERLAY
    assert config.Metadata_Options__metadata_merge_lists is True
    assert config.Auto_Tag__clear_tags is False
    assert config.Auto_Tag__auto_imprint is False
    assert config.Metadata_Options__apply_transform_on_import is False
    assert config.internal__read_tags == config.internal__write_tags == ["cix"]


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("case", VALUES, ids=lambda c: c[0])
def test_raw_writer_parser_reader_and_prepare_save(tmp_path, tag, case):
    _, raw, parsed, recovered = case
    path = cbz(tmp_path)
    md = metadata(raw)
    assert ComicArchive(path).write_tags(md, tag)
    first = observe(path)
    assert md.imprint == raw
    assert first["imprint_element"] is (raw not in (None, ""))
    assert first["parsed"] == parsed
    assert first["readers"] == {"cr": recovered, "cix": recovered}
    assert first["parse_error"] is None
    if raw not in (None, ""):
        # ET escapes markup, but does not escape CR in element text.
        encoded_text = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        assert f"<Imprint>{encoded_text}</Imprint>" in first["xml"]
    saved = ComicArchive(path).read_tags(tag)
    final = prepare_metadata(saved, metadata(None), host_config())
    assert final.imprint == recovered
    assert ComicArchive(path).write_tags(final, tag)
    second = observe(path)
    assert second["parsed"] == recovered
    assert second["readers"] == {"cr": recovered, "cix": recovered}
    record_observation(tmp_path, raw=raw, first=first, merged=final.imprint, final=second)


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("raw", ["A\x00B", "A\x01B", "A\x0bB", "A\x1fB", "A\ufffeB"])
def test_invalid_xml_is_written_successfully_but_read_as_no_tags(tmp_path, tag, raw):
    path = cbz(tmp_path)
    assert ComicArchive(path).write_tags(metadata(raw), tag)
    observed = observe(path)
    assert raw in observed["xml"]
    assert observed["parse_error"] == "ParseError"
    assert observed["has_tags"] == {"cr": False, "cix": False}
    assert observed["readers"] == {"cr": None, "cix": None}
    md, used, error = read_selected_tags([tag], ComicArchive(path))
    assert md.is_empty and used == [] and error is None
    # Even an empty incoming imprint cannot preserve invalid archive XML on resave.
    final = prepare_metadata(md, metadata(None), host_config())
    assert ComicArchive(path).write_tags(final, tag)
    after = observe(path)
    assert after["parse_error"] is None and after["parsed"] is None
    record_observation(tmp_path, raw=raw, first=observed, final=after)


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("clear", [False, True])
@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
@pytest.mark.parametrize("old", EXISTING, ids=lambda c: c[0])
@pytest.mark.parametrize("kind", INCOMING)
def test_archive_prepare_save_matrix(tmp_path, tag, clear, mode, old, kind):
    path = cbz(tmp_path)
    assert ComicArchive(path).write_tags(metadata(old[1]), tag)
    before = observe(path)
    archive_md, used, error = read_selected_tags([tag], ComicArchive(path))
    assert used == [tag] and error is None and archive_md.imprint == old[3]
    raw_new, read_new = incoming_value(kind, old)
    new = metadata(raw_new)
    config = host_config()
    config.Auto_Tag__clear_tags = clear
    config.Metadata_Options__metadata_merge = mode
    old_value = None if clear else old[3]
    use_new = (mode == merge.Mode.ADD_MISSING and old_value is None) or (
        mode == merge.Mode.OVERLAY and raw_new not in (None, "")
    )
    expected_merge = raw_new if use_new else old_value
    expected_saved = read_new if use_new else old_value
    final = prepare_metadata(archive_md, new, config)
    assert final.imprint == expected_merge
    assert archive_md.imprint == old[3] and new.imprint == raw_new
    assert ComicArchive(path).write_tags(final, tag)
    after = observe(path)
    assert after["readers"] == {"cr": expected_saved, "cix": expected_saved}
    record_observation(
        tmp_path,
        archive_raw=old[1],
        before=before,
        archive_metadata=archive_md.imprint,
        incoming=raw_new,
        mode=str(mode),
        clear=clear,
        merged=expected_merge,
        after=after,
    )


@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
@pytest.mark.parametrize("old", EXISTING, ids=lambda c: c[0])
@pytest.mark.parametrize("kind", INCOMING)
def test_overlay_in_memory_does_not_strip_existing_whitespace(mode, old, kind):
    raw_new, _ = incoming_value(kind, old)
    md = metadata(old[1])
    md.overlay(metadata(raw_new), mode)
    if mode == merge.Mode.ADD_MISSING:
        assert md.imprint == (old[1] if old[1] not in (None, "") else raw_new)
    else:
        assert md.imprint == (raw_new if raw_new not in (None, "") else old[1])


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
@pytest.mark.parametrize("clear", [False, True])
@pytest.mark.parametrize("auto", [False, True])
@pytest.mark.parametrize("transform", [False, True])
def test_settings_interaction_with_real_publisher_table(
    tmp_path, monkeypatch, tag, mode, clear, auto, transform
):
    # Host bundled table, not a new plugin dictionary or authority provider.
    monkeypatch.setattr(utils, "publishers", {})
    utils.load_publishers()
    assert utils.get_publisher("vertigo") == ("Vertigo", "DC Comics")
    path = cbz(tmp_path)
    assert ComicArchive(path).write_tags(metadata("既存文庫"), tag)
    config = host_config()
    config.Metadata_Options__metadata_merge = mode
    config.Auto_Tag__clear_tags = clear
    config.Auto_Tag__auto_imprint = auto
    config.Metadata_Options__apply_transform_on_import = transform
    old = ComicArchive(path).read_tags(tag)
    new = metadata("vert", publisher="vertigo", characters={"登場人物"}, notes="根拠")
    config.Metadata_Options__copy_characters_to_tags = True
    config.Metadata_Options__copy_notes_to_comments = True
    final = prepare_metadata(old, new, config)
    expected = "既存文庫" if mode == merge.Mode.ADD_MISSING and not clear else ("Vertigo" if auto else "vert")
    assert final.imprint == expected
    assert final.publisher == ("DC Comics" if auto else "vertigo")
    assert ("登場人物" in final.tags) is transform
    assert (final.description == "根拠") is transform
    assert new.imprint == "vert" and new.publisher == "vertigo"
    assert ComicArchive(path).write_tags(final, tag)
    after = observe(path)
    assert after["readers"] == {"cr": expected, "cix": expected}
    record_observation(tmp_path, incoming=new.imprint, merged=final.imprint, after=after)


@pytest.mark.parametrize(
    "publisher,raw,expected_publisher,expected",
    [
        (None, "DC", None, "DC"),
        ("Unknown Publisher", None, "Unknown Publisher", ""),
        ("vertigo", None, "DC Comics", "Vertigo"),
        ("vertigo", "vert", "DC Comics", "Vertigo"),
        ("vertigo", "DC", "DC Comics", "Vertigo"),
        ("DC Comics", "DC", "DC Comics", ""),
        ("vertigo", "別文庫", "DC Comics", "別文庫"),
        ("vertigo", " Vertigo ", "DC Comics", " Vertigo "),
    ],
)
def test_auto_imprint_can_fill_replace_or_remove_even_add_missing(
    monkeypatch, publisher, raw, expected_publisher, expected
):
    monkeypatch.setattr(utils, "publishers", {})
    utils.load_publishers()
    config = host_config()
    config.Auto_Tag__auto_imprint = True
    config.Metadata_Options__metadata_merge = merge.Mode.ADD_MISSING
    final = prepare_metadata(metadata(raw, publisher=publisher), metadata(None), config)
    assert (final.publisher, final.imprint) == (expected_publisher, expected)


@pytest.mark.parametrize("order", [("cr", "cix"), ("cix", "cr")])
@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
def test_cr_cix_share_one_xml_and_real_cross_readers(tmp_path, order, mode):
    load_tag_plugins()
    assert tags["cr"].file == tags["cix"].file == "ComicInfo.xml"
    path = cbz(tmp_path)
    for tag, raw in zip(order, ("最初", "最後"), strict=True):
        assert ComicArchive(path).write_tags(metadata(raw), tag)
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist().count("ComicInfo.xml") == 1
    final, used, error = read_selected_tags(list(order), ComicArchive(path), mode)
    assert used == list(order) and error is None
    assert final.imprint == "最後"
    assert observe(path)["readers"] == {"cr": "最後", "cix": "最後"}
    record_observation(tmp_path, order=order, mode=str(mode), final=observe(path))


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize(
    "old,new,mode,clear,read_tags,expected",
    [
        ("既存文庫", None, merge.Mode.OVERLAY, False, True, "既存文庫"),
        ("既存文庫", "取得文庫", merge.Mode.OVERLAY, False, True, "取得文庫"),
        ("既存文庫", "取得文庫", merge.Mode.ADD_MISSING, False, True, "既存文庫"),
        ("既存文庫", None, merge.Mode.ADD_MISSING, True, True, None),
        ("   ", "取得文庫", merge.Mode.ADD_MISSING, False, True, "取得文庫"),
        ("既存文庫", None, merge.Mode.ADD_MISSING, False, False, None),
        (None, " 取得文庫 ", merge.Mode.OVERLAY, False, True, "取得文庫"),
    ],
)
def test_real_cli_save_fetch_arguments_and_existing_archive_boundary(
    tmp_path, tag, old, new, mode, clear, read_tags, expected
):
    path = cbz(tmp_path)
    assert ComicArchive(path).write_tags(metadata(old), tag)
    config = host_config()
    config.Runtime_Options__tags_read = [tag] if read_tags else []
    config.Runtime_Options__tags_write = [tag]
    config.Runtime_Options__quiet = True
    config.Auto_Tag__online = True
    config.Auto_Tag__issue_id = "synthetic-id"
    config.Auto_Tag__parse_filename = False
    config.Auto_Tag__clear_tags = clear
    config.Metadata_Options__metadata_merge = mode
    config.Sources__source = "synthetic"
    fake = SimpleNamespace(fetch_comic_data=Mock(return_value=metadata(new)))
    cli = CLI(config, {"synthetic": fake})
    result, matches = cli.save(ComicArchive(path), OnlineMatchResults())
    assert result.status == Status.success and len(matches.good_matches) == 1
    fake.fetch_comic_data.assert_called_once_with(issue_id="synthetic-id", on_rate_limit=None)
    after = observe(path)
    assert after["readers"] == {"cr": expected, "cix": expected}
    record_observation(tmp_path, old=old, incoming=new, merged=result.md.imprint, final=after)


@pytest.mark.gui
def test_actual_gui_apply_form_and_save_offscreen(tmp_path, monkeypatch, talker):
    """Real window methods, synchronous injected fetch result; no GUI search or exe."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from comictaggerlib.ctsettings import ComicTaggerPaths
    from comictaggerlib.main import App
    from comictaggerlib.taggerwindow import TaggerWindow
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    load_archive_plugins()
    load_tag_plugins()
    host = App()
    host.talkers = {"jpbooks": talker}
    paths = ComicTaggerPaths(tmp_path / "config")
    host.initialize_dirs(paths)
    host.register_settings(False)
    config = host.parse_settings(paths, "--config", str(paths.path))
    config[0].Dialog_Flags__show_disclaimer = False
    config[0].Dialog_Flags__notify_plugin_changes = False
    config[0].General__check_for_new_version = False
    handlers = set(logging.getLogger().handlers)
    window = TaggerWindow([], config, host.talkers)
    observations = []
    try:
        # old, incoming, mode, clear, post-prepare, actual saved
        cases = [
            ("既存文庫", None, merge.Mode.OVERLAY, False, "既存文庫", "既存文庫"),
            ("既存文庫", "取得文庫", merge.Mode.OVERLAY, False, "取得文庫", "取得文庫"),
            ("既存文庫", "取得文庫", merge.Mode.ADD_MISSING, False, "既存文庫", "既存文庫"),
            ("既存文庫", None, merge.Mode.OVERLAY, True, None, "既存文庫"),
            ("   ", "取得文庫", merge.Mode.ADD_MISSING, False, "取得文庫", "取得文庫"),
            (None, " 取得文庫 ", merge.Mode.OVERLAY, False, " 取得文庫 ", "取得文庫"),
            (None, "架空\n\t文庫", merge.Mode.OVERLAY, False, "架空\n\t文庫", "架空\n\t文庫"),
        ]
        for tag in ("cr", "cix"):
            window.selected_read_tags = window.selected_write_tags = [tag]
            window.update_tag_tweaks()
            for index, (old, new, mode, clear, merged, saved) in enumerate(cases):
                config[0].Auto_Tag__clear_tags = clear
                config[0].Metadata_Options__metadata_merge = mode
                path = cbz(tmp_path, f"gui-{tag}-{index}")
                assert ComicArchive(path).write_tags(metadata(old), tag)
                window.load_archive(ComicArchive(path))
                window.apply_query_metadata(metadata(new))
                assert window.metadata.imprint == merged
                form = window.leImprint.text()
                window.write_tags()
                final = observe(path)
                assert final["readers"] == {"cr": saved, "cix": saved}
                observations.append(
                    dict(
                        tag=tag,
                        old=old,
                        new=new,
                        clear=clear,
                        mode=str(mode),
                        merged=merged,
                        form=form,
                        final=final,
                    )
                )
        record_observation(tmp_path, gui=observations)
    finally:
        window.hide()
        window.deleteLater()
        app.processEvents()
        for handler in set(logging.getLogger().handlers) - handlers:
            logging.getLogger().removeHandler(handler)
            handler.close()


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize(
    "old,new,mode,clear,auto,expected",
    [
        ("既存文庫", None, merge.Mode.OVERLAY, False, False, "既存文庫"),
        ("既存文庫", "取得文庫", merge.Mode.OVERLAY, False, False, "取得文庫"),
        ("既存文庫", "取得文庫", merge.Mode.ADD_MISSING, False, False, "既存文庫"),
        ("既存文庫", None, merge.Mode.ADD_MISSING, True, False, None),
        (None, " 取得文庫 ", merge.Mode.OVERLAY, False, False, "取得文庫"),
        (None, "vert", merge.Mode.OVERLAY, False, True, "Vertigo"),
    ],
)
def test_real_auto_tag_worker_save_with_mocked_identification(
    tmp_path, monkeypatch, tag, old, new, mode, clear, auto, expected
):
    from comictaggerlib import tag as host_tag
    from comictaggerlib.autotagprogresswindow import AutoTagThread
    from comictaggerlib.ctsettings import ComicTaggerPaths
    from comictaggerlib.issueidentifier import Result as IdentifyResult

    monkeypatch.setattr(utils, "publishers", {})
    utils.load_publishers()
    path = cbz(tmp_path)
    assert ComicArchive(path).write_tags(metadata(old, issue="1"), tag)
    config = host_config()
    config.Runtime_Options__config = ComicTaggerPaths(tmp_path / "config")
    config.internal__read_tags = config.internal__write_tags = [tag]
    config.Auto_Tag__clear_tags = clear
    config.Auto_Tag__auto_imprint = auto
    config.Metadata_Options__metadata_merge = mode
    chosen = SimpleNamespace(issue_id="synthetic-id")
    identify = Mock(return_value=(IdentifyResult.single_good_match, [chosen]))
    monkeypatch.setattr(host_tag, "IssueIdentifier", Mock(return_value=SimpleNamespace(identify=identify)))
    fake = SimpleNamespace(fetch_comic_data=Mock(return_value=metadata(new, publisher="vertigo")))
    worker = AutoTagThread("", [ComicArchive(path)], config, fake)
    result, matches = worker.identify_and_tag_single_archive(ComicArchive(path), OnlineMatchResults())
    assert result.status == Status.success and len(matches.good_matches) == 1
    identify.assert_called_once()
    fake.fetch_comic_data.assert_called_once()
    kwargs = fake.fetch_comic_data.call_args.kwargs
    assert set(kwargs) == {"issue_id", "on_rate_limit"} and kwargs["issue_id"] == "synthetic-id"
    after = observe(path)
    assert after["readers"] == {"cr": expected, "cix": expected}
    record_observation(tmp_path, old=old, incoming=new, merged=result.md.imprint, final=after)
