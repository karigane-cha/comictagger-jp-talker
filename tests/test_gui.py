"""Exercise real beta.9 widgets offscreen, without a custom GUI."""

import logging
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.mark.gui
@pytest.mark.skipif(os.name != "nt", reason="Windows QMessageBox Ctrl+C behavior")
def test_standard_error_dialog_copies_details(talker):
    pytest.importorskip("PyQt6")
    from comictaggerlib.seriesselectionwindow import SearchThread
    from comictaggerlib.ui import qtutils
    from PyQt6 import QtCore, QtGui, QtTest, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/meiryo.ttc"
    if font.is_file():
        QtGui.QFontDatabase.addApplicationFont(str(font))
        app.setFont(QtGui.QFont("Meiryo", 9))
    parent = QtWidgets.QWidget()
    thread = SearchThread(talker, "ISBN: invalid", False, False, 90)
    thread.run()
    assert thread.ct_error
    error = thread.error_e
    qtutils.critical(parent, f"{error.source} {error.code_name} Error", str(error))
    app.processEvents()
    box = parent.findChild(QtWidgets.QMessageBox)
    try:
        assert box is not None
        app.clipboard().clear()
        QtTest.QTest.keyClick(box, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
        copied = app.clipboard().text()
        assert str(error) in copied
        assert "Ctrl+C" in copied and "latest-error.txt" in copied
        assert "ISBN: invalid" in copied
        capture = os.getenv("JPBOOKS_GUI_CAPTURE_DIR")
        if capture:
            folder = Path(capture)
            folder.mkdir(parents=True, exist_ok=True)
            box.grab().save(str(folder / "comictagger-copyable-error.png"))
    finally:
        parent.close()
        parent.deleteLater()
        app.processEvents()


@pytest.mark.gui
@pytest.mark.parametrize("output", ["volume", "issue", "both"])
def test_standard_gui_source_and_selection(talker, tmp_path, monkeypatch, output):
    pytest.importorskip("PyQt6")
    from comicapi.comicarchive import load_archive_plugins, load_tag_plugins
    from comictaggerlib.ctsettings import ComicTaggerPaths
    from comictaggerlib.main import App
    from comictaggerlib.seriesselectionwindow import SearchThread, SeriesSelectionWindow
    from comictaggerlib.taggerwindow import TaggerWindow
    from PyQt6 import QtCore, QtGui, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Offscreen Qt on isolated Windows may not discover the system font registry.
    # Load installed fonts for QA captures only; the plugin never changes host fonts.
    if os.name == "nt":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "meiryo.ttc"):
            if (fonts / name).is_file():
                QtGui.QFontDatabase.addApplicationFont(str(fonts / name))
        app.setFont(QtGui.QFont("Meiryo", 9))
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
    # parse_settings resets the source; restore the mocked HTTP source for this test.
    from unittest.mock import Mock

    import requests

    from comictagger_jp_talker.sources.ndl import NDLSource

    payload = (Path(__file__).parent / "fixtures" / "ndl.xml").read_bytes()
    payload = payload.replace(b"<numberOfRecords>1", b"<numberOfRecords>2")
    start = payload.index(b"<record>")
    end = payload.index(b"</record>") + len(b"</record>")
    duplicate = payload[start:end].replace(b"Itest001", b"Itest002")
    payload = payload.replace(b"</records>", duplicate + b"</records>")
    response = requests.Response()
    response.status_code = 200
    response._content = payload
    source = NDLSource(tmp_path / "gui-cache")
    monkeypatch.setattr(source.session, "get", Mock(return_value=response))
    talker._source = source
    talker.volume_output = output
    original_handlers = set(logging.getLogger().handlers)
    window = TaggerWindow([], config, host.talkers)
    selection = None
    try:
        index = window.cbx_sources.findData("jpbooks")
        assert index >= 0 and window.cbx_sources.itemText(index) == "Japanese Books"
        # Unsupported write fields and invalid values are separate red indicators.
        window.selected_write_tags = ["cr"]
        window.update_tag_tweaks()
        assert window.leGtin.isReadOnly()
        window.selected_write_tags = ["cix"]
        window.update_tag_tweaks()
        assert not window.leGtin.isReadOnly()
        window.leGtin.setText("9784885942877")
        assert window.leGtin.styleSheet() == ""
        window.leGtin.setText("invalid")
        assert "salmon" in window.leGtin.styleSheet()
        window.leGtin.clear()
        selection = SeriesSelectionWindow(window, config[0], talker, series_name="漫画")
        thread = SearchThread(talker, "漫画", False, False, 90)
        thread.run()  # synchronous execution of the real host worker with mocked HTTP
        selection.search_thread = thread
        selection.search_complete()
        assert selection.twList.rowCount() == 2
        assert selection.result() == 0  # not accepted automatically
        assert "ISBN" in selection.teDescription.toPlainText()
        selected = selection.twList.item(0, 0).data(QtCore.Qt.ItemDataRole.UserRole)
        issues = talker.fetch_issues_in_series(selected)
        selection.selector.query_finished(issues)
        assert selection.selector.twList.rowCount() == 1
        assert selection.selector.twList.item(0, 0).text() == ("" if output == "volume" else "74")
        selection.selector.twList.selectRow(0)
        assert selection.selector.issue_id == selected
        md = talker.fetch_comic_data(issue_id=selection.selector.issue_id)
        assert md.volume == (None if output == "issue" else 74)
        assert md.issue == (None if output == "volume" else "74")
        capture = os.getenv("JPBOOKS_GUI_CAPTURE_DIR")
        if capture:
            folder = Path(capture)
            folder.mkdir(parents=True, exist_ok=True)
            window.cbx_sources.setCurrentIndex(index)
            window.grab().save(str(folder / "comictagger-jpbooks.png"))
            selection.grab().save(str(folder / "comictagger-candidates.png"))
    finally:
        if selection:
            selection.selector.hide()
            selection.hide()
        for handler in set(logging.getLogger().handlers) - original_handlers:
            logging.getLogger().removeHandler(handler)
            handler.close()
        window.hide()
        window.deleteLater()
        app.processEvents()
        source.cache.close()
        source.session.close()
