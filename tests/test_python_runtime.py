"""Security baseline boundaries and CI installation ordering."""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/verify-python-runtime.py"
RUNTIME = runpy.run_path(str(SCRIPT))
RuntimeVersion = RUNTIME["RuntimeVersion"]
verify_runtime = RUNTIME["verify_runtime"]


@pytest.mark.parametrize(
    ("version", "expected", "accepted"),
    [
        ((3, 12, 15, "final", 0), (3, 12), False),
        ((3, 12, 16, "final", 0), (3, 12), True),
        ((3, 12, 17, "final", 0), (3, 12), True),
        ((3, 13, 17, "final", 0), (3, 13), False),
        ((3, 13, 18, "final", 0), (3, 13), True),
        ((3, 13, 19, "final", 0), (3, 13), True),
        ((3, 12, 16, "final", 0), (3, 13), False),
        ((3, 14, 10, "final", 0), (3, 13), False),
        ((3, 13, 18, "candidate", 1), (3, 13), False),
        ((3, 14, 9, "final", 0), (3, 14), False),
        ((3, 14, 10, "final", 0), (3, 14), True),
        ((3, 14, 11, "final", 0), (3, 14), True),
        ((3, 15, 1, "final", 0), (3, 15), False),
        ((3, 15, 2, "final", 0), (3, 15), True),
        ((3, 10, 22, "final", 0), (3, 12), False),
        ((3, 11, 18, "final", 0), (3, 12), False),
        ((3, 13, 18, "final", 0), (3, 12), False),
        ((3, 14, 10, "alpha", 1), (3, 14), False),
        ((3, 14, 10, "beta", 1), (3, 14), False),
        ((3, 14, 10, "candidate", 1), (3, 14), False),
        ((3, 14, 10, "final", 0), (3, 12), False),
        ((3, 16, 0, "final", 0), (3, 16), False),
        ((4, 14, 10, "final", 0), (3, 14), False),
    ],
)
def test_runtime_security_boundaries(version, expected, accepted):
    if accepted:
        verify_runtime(RuntimeVersion(*version), expected)
    else:
        with pytest.raises(ValueError):
            verify_runtime(RuntimeVersion(*version), expected)


def test_real_interpreter_rejected_for_another_series():
    expected = "3.14" if sys.version_info[:2] != (3, 14) else "3.12"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), expected], capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0
    assert str(sys.version_info.major) + "." + str(sys.version_info.minor) in result.stdout
    assert "is required" in result.stderr


def test_ci_matrix_and_windows_build_series():
    workflow = yaml.safe_load((ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"))
    test_job = workflow["jobs"]["test"]
    assert test_job["runs-on"] == "${{ matrix.os }}"
    assert test_job["strategy"]["matrix"] == {
        "include": [
            {"os": "ubuntu-24.04", "python-version": "3.12"},
            {"os": "ubuntu-24.04", "python-version": "3.13"},
            {"os": "windows-latest", "python-version": "3.14"},
        ]
    }
    setup = next(
        step for step in test_job["steps"] if step.get("uses", "").startswith("actions/setup-python@")
    )
    verify = next(step for step in test_job["steps"] if step.get("name") == "Verify Python security baseline")
    assert setup["with"]["python-version"] == "${{ matrix.python-version }}"
    assert verify["run"] == "python .github/scripts/verify-python-runtime.py '${{ matrix.python-version }}'"

    release = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    for job in (workflow["jobs"]["build"], release["jobs"]["release"]):
        setup = next(
            step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-python@")
        )
        verify = next(step for step in job["steps"] if step.get("name") == "Verify Python security baseline")
        assert job["runs-on"] == "windows-latest"
        assert setup["with"]["python-version"] == "3.14"
        assert verify["run"] == "python .github/scripts/verify-python-runtime.py 3.14"


@pytest.mark.parametrize(
    ("workflow", "job"), [("test.yml", "test"), ("test.yml", "build"), ("release.yml", "release")]
)
def test_workflow_verifies_runtime_before_installation(workflow, job):
    data = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8"))
    steps = data["jobs"][job]["steps"]
    setup = next(
        i for i, step in enumerate(steps) if step.get("uses", "").startswith("actions/setup-python@")
    )
    verify = next(i for i, step in enumerate(steps) if step.get("name") == "Verify Python security baseline")
    bootstrap = next(i for i, step in enumerate(steps) if step.get("name") == "Bootstrap secure pip")
    assert setup + 1 == verify < bootstrap
    assert steps[setup]["with"]["check-latest"] is True
    assert steps[verify]["run"].startswith("python .github/scripts/verify-python-runtime.py ")
    assert "if" not in steps[verify] and "continue-on-error" not in steps[verify]
    assert "if" not in steps[bootstrap] and "continue-on-error" not in steps[bootstrap]
    assert not any("pip install" in step.get("run", "") for step in steps[:bootstrap])
