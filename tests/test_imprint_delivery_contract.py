"""E1 test-only capability experiments; no diagnostic command or save gate is implemented."""

from __future__ import annotations

import inspect
import json
import logging
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from comicapi.genericmetadata import GenericMetadata
from comictalker.comictalker import ComicTalker, RLCallBack
from test_imprint_host_boundary import cbz
from test_linkage import record
from test_linkage_evidence import serve_linkage
from test_madb_acquisition import sources as sources

from comictagger_jp_talker.imprint_candidates import (
    ImprintEligibilityReason,
    ImprintEligibilityState,
    classify_imprint_terms,
    compare_imprint_candidates,
    evaluate_imprint_eligibility,
    extract_imprint_evidence,
)
from comictagger_jp_talker.linkage import acquire_linked_record_evidence
from comictagger_jp_talker.talker import JapaneseBooksTalker


def test_installed_talker_contract_has_no_diagnostic_or_save_target_channel():
    public_methods = {
        name for name, value in vars(ComicTalker).items() if callable(value) and not name.startswith("_")
    }
    assert public_methods == {
        "register_settings",
        "parse_settings",
        "check_status",
        "search_for_series",
        "fetch_comic_data",
        "fetch_series",
        "fetch_issues_in_series",
        "fetch_issues_by_series_issue_num_and_year",
    }
    for cls in (ComicTalker, JapaneseBooksTalker):
        assert tuple(inspect.signature(cls.fetch_comic_data).parameters) == (
            "self",
            "issue_id",
            "series_id",
            "issue_number",
            "on_rate_limit",
        )
    assert set(RLCallBack.__annotations__) == {"callback", "interval"}
    assert "search_metadata" not in public_methods


@pytest.mark.parametrize("warm", [False, True])
def test_evidence_can_be_evaluated_without_retrieval_metadata_or_archive_changes(tmp_path, sources, warm):
    source = sources()
    serve_linkage(source)
    evidence = acquire_linked_record_evidence(record(), source)
    if warm:
        evidence = acquire_linked_record_evidence(record(), source)
    assert source.session.post.call_count == 3
    metadata = GenericMetadata(notes="既存 Notes\n保持", series="既存 Series")
    metadata_before = deepcopy(metadata)
    paths = [cbz(tmp_path, "one"), cbz(tmp_path, "two")]
    archive_bytes = [p.read_bytes() for p in paths]
    before = deepcopy(evidence)
    # The existing pure APIs consume the exact acquired bundle and its own context.
    # No authority fixtures, fake trusted flags, or current-archive assertion.
    results = []
    for book in evidence.acquisition_context.books:
        assert book.included_in_linkage
        assert book.bundle is evidence.bundles[0]
        extraction = extract_imprint_evidence(book.bundle, book.context)
        assert extraction.bundle is book.bundle
        classification = classify_imprint_terms(extraction)
        comparison = compare_imprint_candidates(
            classification, evidence.acquisition_context.ndl_input.to_record()
        )
        decision = evaluate_imprint_eligibility(evidence.linkage, comparison, authority_evidence=())
        assert decision.state != ImprintEligibilityState.ELIGIBLE
        assert ImprintEligibilityReason.SEMANTIC_UNVERIFIED in decision.reasons
        assert decision.authority == ()
        assert {c.origin for c in extraction.candidates} == {"book", "series"}
        results.append(asdict(decision))
    # Serialization here is an experiment, not the proposed production renderer.
    payload = json.dumps(
        {"evidence": asdict(evidence), "evaluations": results, "archive_state": "not_supplied"},
        ensure_ascii=True,
    )
    (tmp_path / "observation.json").write_text(payload + "\n", encoding="utf-8", newline="\n")
    assert json.loads(payload)["archive_state"] == "not_supplied"
    assert evidence == before and metadata == metadata_before
    assert [p.read_bytes() for p in paths] == archive_bytes
    assert source.session.post.call_count == 3
    assert evidence.acquisition_context.books[0].context.acquired_at is None
    if warm:
        assert all(e.origin_fetched_at is None for e in evidence.acquisition_context.events)


@pytest.fixture
def qt_app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app
    while QtWidgets.QApplication.overrideCursor() is not None:
        QtWidgets.QApplication.restoreOverrideCursor()
    app.processEvents()


@pytest.mark.parametrize("complete", [False, True])
def test_actual_preview_fetch_repeats_and_has_no_archive_or_purpose(qt_app, tmp_path, complete):
    from comictaggerlib.issueselectionwindow import IssueSelectionWindow
    from comictaggerlib.taggerwindow import QueryThread

    initial = GenericMetadata(issue_id="same-id", issue="1", year=2024, month=1, title="Synthetic")
    if complete:
        initial._cover_image = SimpleNamespace(URL="")
    returned = GenericMetadata(issue_id="same-id", issue="1", title="Fetched")
    talker = SimpleNamespace(fetch_comic_data=Mock(return_value=returned))
    paths = [cbz(tmp_path, "first"), cbz(tmp_path, "second")]
    original = [p.read_bytes() for p in paths]
    callbacks = []
    for _path in paths:
        # Actual host _fetch method; surrounding view widgets are test doubles.
        # The method receives a row, not the caller's archive.
        view = SimpleNamespace(
            twList=Mock(),
            issue_list={"same-id": initial},
            talker=talker,
            on_ratelimit=Mock(),
            cover_widget=Mock(),
            set_description=Mock(),
            teDescription=Mock(),
            lblIssueLink=Mock(),
        )
        view.twList.item.return_value.data.return_value = "same-id"
        for _ in range(2):
            result = IssueSelectionWindow._fetch(view, 0)
            assert result is (initial if complete else returned)
        assert view.issue_list["same-id"] is initial  # Detail result is not cached back here.
        callbacks.append(view.on_ratelimit)
    assert talker.fetch_comic_data.call_count == (0 if complete else 4)
    for index, call in enumerate(talker.fetch_comic_data.call_args_list):
        assert set(call.kwargs) == {"issue_id", "on_rate_limit"}
        assert call.kwargs["issue_id"] == "same-id"
        assert call.kwargs["on_rate_limit"].callback is callbacks[index // 2]
    worker = QueryThread(talker, "same-id", "series-id", "1")
    worker.run()  # Real final-fetch worker, synchronous; does not write archives.
    kwargs = talker.fetch_comic_data.call_args.kwargs
    assert set(kwargs) == {"issue_id", "series_id", "issue_number", "on_rate_limit"}
    assert [p.read_bytes() for p in paths] == original
    # Different callbacks carry progress only; neither proves an archive identity.
    assert not hasattr(talker, "archive")


def test_real_log_file_and_log_window_can_display_escaped_diagnostics(qt_app, tmp_path):
    from comictaggerlib.applicationlogwindow import ApplicationLogWindow, QTextEditLogger
    from comictaggerlib.log import get_file_handler

    logger = logging.getLogger("test_only.imprint_delivery")
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    formatter = logging.Formatter("%(message)s")
    file_handler = get_file_handler(tmp_path / "ComicTagger.log")
    file_handler.setFormatter(formatter)
    ui_handler = QTextEditLogger(formatter, logging.DEBUG)
    window = ApplicationLogWindow(tmp_path, ui_handler)
    logger.addHandler(file_handler)
    logger.addHandler(ui_handler)
    raw = '<b>架空</b>\n\t"文庫"'
    # QTextEdit.append accepts rich text. Escape markup separately from JSON escaping.
    payload = json.dumps({"mode": "READ_ONLY", "authority": "UNVERIFIED", "raw": raw}, ensure_ascii=True)
    safe_payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    try:
        logger.warning("%s", safe_payload)
        file_handler.flush()
        qt_app.processEvents()
        file_text = (tmp_path / "ComicTagger.log").read_text(encoding="utf-8").strip()
        visible = window.textEdit.toPlainText()
        assert file_text == visible == safe_payload
        assert json.loads(visible)["raw"] == raw
        assert json.loads(visible)["authority"] == "UNVERIFIED"
    finally:
        logger.removeHandler(file_handler)
        logger.removeHandler(ui_handler)
        file_handler.close()
        ui_handler.close()
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        window.hide()
        window.deleteLater()
        qt_app.processEvents()
