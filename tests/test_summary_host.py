"""Synthetic Summary recovery through beta.9 merge, real widgets and tag writers."""

import io
import json
import logging
import os
import subprocess
import sys
import zipfile
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
import test_summary
from comicapi import merge
from comicapi.comicarchive import ComicArchive, load_archive_plugins, load_tag_plugins
from comicapi.genericmetadata import GenericMetadata
from comictaggerlib.md import prepare_metadata
from PIL import Image
from test_summary import ID, response

from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.sources.ndl import NDLSource

OLD = "保存済みの要約"
SUMMARY = "紙版の要約・𠮷野"


@pytest.fixture
def no_abstract(xml_bytes):
    return test_summary.no_abstract.__wrapped__(xml_bytes)


@pytest.fixture
def details():
    return test_summary.details.__wrapped__()


def incoming_metadata(talker, no_abstract, details, state):
    assert version("comictagger") == "1.6.0b9"
    source = talker.source
    query = SearchQuery(isbn="488594287X")
    source.session.get.return_value = response(no_abstract)
    source.search(query)
    if state != "missing":
        source.session.get.return_value = response(json.dumps(details).encode())
        assert source.get(ID).abstracts == [SUMMARY]
    if state in ("fallback", "absent"):
        source.session.get.return_value = response(no_abstract)
        source.search(query, refresh=True)
    source.session.get.return_value = (
        response(b'{"hit":0,"list":[]}') if state == "absent" else response(status=429)
    )
    source.session.get.reset_mock()
    md = talker.fetch_comic_data(issue_id=ID)
    assert md.description == (SUMMARY if state in ("cached", "fallback") else None)
    assert source.session.get.call_count == (0 if state == "cached" else 1)
    if state == "fallback":
        assert ID in source._refresh_summaries and ID in source._summary_failures
    return md


def cbz(tmp_path, name, description, tag):
    path = tmp_path / f"{name}.cbz"
    cover = io.BytesIO()
    Image.new("RGB", (16, 24), "white").save(cover, "PNG")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("001.png", cover.getvalue())
    assert ComicArchive(path).write_tags(
        GenericMetadata(is_empty=False, series="Synthetic Summary", description=description), tag
    )
    return path


def expected_description(state, incoming, mode):
    if state == "existing" and mode == merge.Mode.ADD_MISSING:
        return OLD
    return incoming or (OLD if state == "existing" else None)


@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
@pytest.mark.parametrize("state", ["existing", "unsaved_empty", "saved_empty"])
@pytest.mark.parametrize("summary", ["cached", "fallback", "missing", "absent"])
def test_summary_prepare_and_tag_roundtrip(talker, no_abstract, details, tmp_path, tag, mode, state, summary):
    load_archive_plugins()
    load_tag_plugins()
    incoming = incoming_metadata(talker, no_abstract, details, summary)
    saved = None if state == "saved_empty" else OLD
    path = cbz(tmp_path, "summary", saved, tag)
    current = ComicArchive(path).read_tags(tag)
    assert current.description == saved
    if state == "unsaved_empty":
        current.description = None
        assert ComicArchive(path).read_tags(tag).description == OLD
    config = SimpleNamespace(
        Metadata_Options__apply_transform_on_import=False,
        Auto_Tag__clear_tags=False,
        Metadata_Options__metadata_merge=mode,
        Metadata_Options__metadata_merge_lists=False,
        Auto_Tag__auto_imprint=False,
        Metadata_Options__remove_html_tables=False,
    )
    final = prepare_metadata(current, incoming, config)
    expected = expected_description(state, incoming.description, mode)
    assert final.description == expected
    assert ComicArchive(path).write_tags(final, tag)
    assert ComicArchive(path).read_tags(tag).description == expected


def _check_gui_child_result(result, report, expected_name, *, required):
    output = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    if result.returncode != 0:
        pytest.fail(f"GUI child exited with code {result.returncode}\n{output}")
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as exc:
        pytest.fail(f"Missing or invalid GUI child report: {exc}\n{output}")
    suites = list(root.iter("testsuite"))
    if root.tag not in ("testsuites", "testsuite") or len(suites) != 1:
        pytest.fail(f"Unexpected GUI child report structure\n{output}")
    suite = suites[0]
    cases = list(suite.iter("testcase"))
    if len(cases) != 1 or cases[0].get("name") != expected_name:
        pytest.fail(f"Expected exactly the selected GUI child test\n{output}")
    case = cases[0]
    skipped = case.find("skipped")
    try:
        counts = tuple(int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped"))
    except (KeyError, ValueError):
        pytest.fail(f"Invalid GUI child result counts\n{output}")
    if (
        counts != (1, 0, 0, int(skipped is not None))
        or case.find("failure") is not None
        or case.find("error") is not None
    ):
        pytest.fail(f"GUI child did not report a consistent PASS or SKIP\n{output}")
    if skipped is not None:
        reason = skipped.get("message") or skipped.text or "GUI child skipped"
        if required:
            pytest.fail(f"Required GUI child skipped: {reason}\n{output}")
        pytest.skip(reason)


def _run_gui_child(tmp_path, node_name, *, required):
    report = tmp_path / "gui-child-result.xml"
    if report.exists():
        pytest.fail("GUI child report already exists; refusing a stale result")
    code = """
import socket, sys, pytest
def blocked(*args, **kwargs):
    raise AssertionError('GUI integration tests must not access the network')
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = blocked
raise SystemExit(pytest.main(sys.argv[1:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-I",
            "-c",
            code,
            "-q",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(tmp_path / "gui-child"),
            "--junitxml",
            str(report),
            f"{Path(__file__).resolve()}::{node_name}",
        ],
        env={
            **os.environ,
            "JPBOOKS_SUMMARY_GUI_CHILD": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "QT_QPA_PLATFORM": "offscreen",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    _check_gui_child_result(result, report, node_name, required=required)


@pytest.mark.gui
@pytest.mark.parametrize("tag", ["cr", "cix"])
@pytest.mark.parametrize("mode", [merge.Mode.OVERLAY, merge.Mode.ADD_MISSING])
def test_summary_actual_gui_apply_save_reload(
    talker, no_abstract, details, tmp_path, monkeypatch, tag, mode, request
):
    # beta.9's global cover-thread list can outlive a previous QApplication.
    # Give each real GUI test its own process, without changing host behavior.
    if os.environ.get("JPBOOKS_SUMMARY_GUI_CHILD") != "1":
        required = os.environ.get("CI", "").lower() in ("true", "1") or (
            os.environ.get("JPBOOKS_REQUIRE_GUI_TESTS") == "1"
        )
        _run_gui_child(tmp_path, request.node.name, required=required)
        return
    pytest.importorskip("PyQt6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from unittest.mock import Mock

    from comictaggerlib.ctsettings import ComicTaggerPaths
    from comictaggerlib.main import App
    from comictaggerlib.pageloader import PageLoader
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
    config[0].Metadata_Options__apply_transform_on_import = False
    config[0].Auto_Tag__clear_tags = False
    config[0].Auto_Tag__auto_imprint = False
    config[0].Metadata_Options__metadata_merge = mode
    handlers = set(logging.getLogger().handlers)
    window = TaggerWindow([], config, host.talkers)
    sources = []
    try:
        window.selected_read_tags = window.selected_write_tags = [tag]
        window.update_tag_tweaks()
        for summary in ("cached", "fallback", "missing", "absent"):
            source = NDLSource(tmp_path / f"cache-{summary}")
            sources.append(source)
            monkeypatch.setattr(source.session, "get", Mock())
            talker._source = source
            incoming = incoming_metadata(talker, no_abstract, details, summary)
            for state in ("existing", "unsaved_empty", "saved_empty"):
                saved = None if state == "saved_empty" else OLD
                path = cbz(tmp_path, f"gui-{summary}-{state}", saved, tag)
                window.load_archive(ComicArchive(path))
                assert window.teComments.toPlainText() == (saved or "")
                if state == "unsaved_empty":
                    window.teComments.clear()
                    assert ComicArchive(path).read_tags(tag).description == OLD
                window.apply_query_metadata(incoming.copy())
                expected = expected_description(state, incoming.description, mode)
                assert window.metadata.description == expected
                assert window.teComments.toPlainText() == (expected or "")
                window.write_tags()
                assert ComicArchive(path).read_tags(tag).description == expected
                window.load_archive(ComicArchive(path))
                assert window.teComments.toPlainText() == (expected or "")
    finally:
        # The host keeps a global list of cover threads. Finish and reap them
        # before this test's QApplication can destroy their Qt objects.
        for loader in list(PageLoader.instanceList):
            assert loader.wait(5000), "Cover thread did not finish"
        PageLoader.reap_instances()
        app.processEvents()
        window.hide()
        window.deleteLater()
        app.processEvents()
        for source in sources:
            source.session.close()
            source.cache.close()
        for handler in set(logging.getLogger().handlers) - handlers:
            logging.getLogger().removeHandler(handler)
            handler.close()
