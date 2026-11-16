"""GUI child results must never turn missing verification into a parent PASS."""

import subprocess
from unittest.mock import Mock
from xml.etree import ElementTree as ET

import pytest
import test_summary_host as host

NODE = "test_summary_actual_gui_apply_save_reload[overlay-cr]"


def write_report(path, outcome="pass", name=NODE):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="1", failures="0", errors="0", skipped="0")
    case = ET.SubElement(suite, "testcase", name=name)
    if outcome != "pass":
        ET.SubElement(case, outcome, message="Qt unavailable" if outcome == "skipped" else "child failed")
        suite.set({"skipped": "skipped", "failure": "failures", "error": "errors"}[outcome], "1")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return root


def result(code=0):
    return subprocess.CompletedProcess(["python"], code, stdout="child stdout", stderr="child stderr")


def test_child_pass_requires_valid_selected_result(tmp_path):
    report = tmp_path / "result.xml"
    write_report(report)
    assert host._check_gui_child_result(result(), report, NODE, required=True) is None


@pytest.mark.parametrize("required", [False, True])
def test_child_skip_is_propagated_or_required_failure(tmp_path, required):
    report = tmp_path / "result.xml"
    write_report(report, "skipped")
    expected = pytest.fail.Exception if required else pytest.skip.Exception
    with pytest.raises(expected, match="Qt unavailable"):
        host._check_gui_child_result(result(), report, NODE, required=required)


@pytest.mark.parametrize("code", [1, 2, -11, 3221225477])
def test_child_failure_exception_or_crash_cannot_pass(tmp_path, code):
    report = tmp_path / "result.xml"
    write_report(report)  # Even a PASS notification cannot override unsuccessful exit.
    with pytest.raises(pytest.fail.Exception, match=f"exited with code {code}"):
        host._check_gui_child_result(result(code), report, NODE, required=False)


@pytest.mark.parametrize("outcome", ["failure", "error"])
def test_failure_report_cannot_pass_even_with_zero_exit(tmp_path, outcome):
    report = tmp_path / "result.xml"
    write_report(report, outcome)
    with pytest.raises(pytest.fail.Exception, match="consistent PASS or SKIP"):
        host._check_gui_child_result(result(), report, NODE, required=False)


@pytest.mark.parametrize(
    "problem", ["missing", "malformed", "wrong_name", "empty", "multiple", "counts", "invalid_counts", "root"]
)
def test_missing_or_invalid_notification_cannot_pass(tmp_path, problem):
    report = tmp_path / "result.xml"
    if problem == "malformed":
        report.write_text("<broken", encoding="utf-8")
    elif problem != "missing":
        root = write_report(report, name="different-test" if problem == "wrong_name" else NODE)
        suite = root.find("testsuite")
        if problem == "empty":
            suite.remove(suite.find("testcase"))
        elif problem == "multiple":
            ET.SubElement(suite, "testcase", name=NODE)
        elif problem == "counts":
            suite.set("tests", "2")
        elif problem == "invalid_counts":
            suite.set("errors", "unknown")
        elif problem == "root":
            root.tag = "unexpected"
        ET.ElementTree(root).write(report, encoding="utf-8")
    with pytest.raises(pytest.fail.Exception):
        host._check_gui_child_result(result(), report, NODE, required=False)


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("python", 60), OSError("launch failed")])
def test_child_launch_and_timeout_errors_escape(tmp_path, monkeypatch, error):
    launch = Mock(side_effect=error)
    monkeypatch.setattr(host.subprocess, "run", launch)
    with pytest.raises(type(error)):
        host._run_gui_child(tmp_path, NODE, required=False)
    launch.assert_called_once()


def test_existing_notification_is_never_reused(tmp_path, monkeypatch):
    write_report(tmp_path / "gui-child-result.xml")
    launch = Mock()
    monkeypatch.setattr(host.subprocess, "run", launch)
    with pytest.raises(pytest.fail.Exception, match="stale result"):
        host._run_gui_child(tmp_path, NODE, required=False)
    launch.assert_not_called()


def test_child_launch_checks_report_and_uses_offscreen_isolation(tmp_path, monkeypatch):
    def run(command, **kwargs):
        assert "-I" in command
        assert kwargs["env"]["QT_QPA_PLATFORM"] == "offscreen"
        assert kwargs["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        assert kwargs["encoding"] == "utf-8" and kwargs["timeout"] == 60
        report = command[command.index("--junitxml") + 1]
        write_report(report)
        return result()

    launch = Mock(side_effect=run)
    monkeypatch.setattr(host.subprocess, "run", launch)
    host._run_gui_child(tmp_path, NODE, required=True)
    launch.assert_called_once()
