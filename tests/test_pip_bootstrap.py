"""Exercise CI pip recovery without changing the interpreter's packages."""

from __future__ import annotations

import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / ".github/scripts/bootstrap-pip.ps1"
VERIFY = ROOT / ".github/scripts/verify-python-security.py"
WHEEL_HASH = "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"


@pytest.fixture
def bootstrap(tmp_path):
    powershell = shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)
    if not powershell:
        pytest.skip("PowerShell is needed to exercise the CI bootstrap script")

    # Each invocation is a real native process, but it only records the requested
    # operation and returns a controlled status instead of changing any packages.
    fake = tmp_path / "fake_python.py"
    fake.write_text(
        """\
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
log = Path(os.environ["PIP_BOOTSTRAP_TEST_LOG"])
history = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
if args == ["--version"]:
    operation = "version"
elif args and args[0].endswith("verify-python-security.py"):
    operation = "verify"
elif args[:2] == ["-m", "pip"]:
    operation = "install"
else:
    raise SystemExit(64)
with log.open("a") as output:
    output.write(json.dumps({"operation": operation, "args": args}) + "\\n")
config = json.loads(os.environ["PIP_BOOTSTRAP_TEST_CONFIG"])
index = sum(item["operation"] == operation for item in history)
status = config[operation][index]
if status == "crash":
    os._exit(73)
if status:
    print(f"simulated {operation} failure", file=sys.stderr)
raise SystemExit(status)
""",
        encoding="utf-8",
    )
    if os.name == "nt":
        launcher = tmp_path / "python.cmd"
        launcher.write_text(f'@echo off\n"{sys.executable}" "{fake}" %*\nexit /b %errorlevel%\n')
    else:
        launcher = tmp_path / "python"
        launcher.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(fake))} "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o755)

    # Match the GitHub Actions pwsh wrapper, including its final exit-code check.
    driver = tmp_path / "run_bootstrap.ps1"
    driver.write_text(
        """\
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$global:LASTEXITCODE = 0
& $env:PIP_BOOTSTRAP_TEST_SCRIPT
if (Test-Path -LiteralPath variable:\\LASTEXITCODE) { exit $LASTEXITCODE }
""",
        encoding="utf-8",
    )

    def run(*, version=(0,), verify=(0,), install=(), missing_python=False):
        log = tmp_path / "calls.jsonl"
        env = os.environ.copy()
        env["PATH"] = str(tmp_path / "missing") if missing_python else str(tmp_path)
        env["PIP_BOOTSTRAP_TEST_LOG"] = str(log)
        env["PIP_BOOTSTRAP_TEST_SCRIPT"] = str(BOOTSTRAP)
        env["PIP_BOOTSTRAP_TEST_CONFIG"] = json.dumps(
            {"version": version, "verify": verify, "install": install}
        )
        command = [powershell, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            command += ["-ExecutionPolicy", "Bypass"]
        command += ["-File", str(driver)]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        for call in calls:
            if call["operation"] == "verify":
                assert len(call["args"]) == 1 and Path(call["args"][0]) == VERIFY
        return result, calls

    return run


def operations(calls):
    return [call["operation"] for call in calls]


def test_secure_pip_skips_reinstallation(bootstrap):
    result, calls = bootstrap()
    assert result.returncode == 0, result.stderr
    assert operations(calls) == ["version", "verify"]


@pytest.mark.parametrize("initial_status", [1, 2, "crash"])
def test_failed_check_recovers_and_rechecks(bootstrap, initial_status):
    result, calls = bootstrap(verify=(initial_status, 0), install=(0,))
    assert result.returncode == 0, result.stderr
    assert operations(calls) == ["version", "verify", "install", "verify"]
    args = calls[2]["args"]
    assert args[:2] == ["-m", "pip"]
    assert "--force-reinstall" in args and "--no-deps" in args
    assert args[-1].startswith("pip @ https://files.pythonhosted.org/")
    assert args[-1].endswith(f"/pip-26.2.2-py3-none-any.whl#sha256={WHEEL_HASH}")


def test_failed_recovery_fails_without_claiming_success(bootstrap):
    result, calls = bootstrap(verify=(1,), install=(23,))
    assert result.returncode != 0
    assert operations(calls) == ["version", "verify", "install"]
    assert "Failed to install the hash-verified pip wheel" in result.stderr


@pytest.mark.parametrize("final_status", [1, 2, "crash"])
def test_failed_recheck_fails_even_after_successful_install(bootstrap, final_status):
    result, calls = bootstrap(verify=(1, final_status), install=(0,))
    assert result.returncode != 0
    assert operations(calls) == ["version", "verify", "install", "verify"]
    assert "Python packaging security verification failed" in result.stderr


def test_failed_python_version_command_stops_before_recovery(bootstrap):
    result, calls = bootstrap(version=(19,))
    assert result.returncode != 0
    assert operations(calls) == ["version"]
    assert "Failed to determine Python version" in result.stderr


def test_missing_python_command_cannot_reuse_a_successful_exit_code(bootstrap):
    result, calls = bootstrap(missing_python=True)
    assert result.returncode != 0
    assert calls == []


@pytest.mark.parametrize(
    ("pip_version", "bundled_certifi", "standalone_certifi", "failure"),
    [
        ("26.2.2", "2026.10.19", None, None),
        ("27.0", "2027.1.1", None, None),
        ("26.2.1", "2026.10.19", None, "Unsafe pip:"),
        ("26.2.2", "2026.10.18", None, "Unsafe pip bundled certifi:"),
        ("26.2.2", "2026.10.19", "2026.10.19", None),
        ("26.2.2", "2026.10.19", "2026.10.18", "Unsafe standalone certifi:"),
    ],
)
def test_python_security_verifier_boundaries(
    monkeypatch, pip_version, bundled_certifi, standalone_certifi, failure
):
    main = runpy.run_path(str(VERIFY))["main"]
    versions = {"pip": pip_version}
    if standalone_certifi is not None:
        versions["certifi"] = standalone_certifi
    monkeypatch.setitem(main.__globals__, "version", versions.__getitem__)
    monkeypatch.setattr(main.__globals__["certifi"], "__version__", bundled_certifi)
    args = [str(VERIFY)] + (["--require-certifi"] if standalone_certifi is not None else [])
    monkeypatch.setattr(sys, "argv", args)
    if failure:
        with pytest.raises(SystemExit, match=failure):
            main()
    else:
        main()


@pytest.mark.parametrize("package", ["pip", "certifi"])
def test_python_security_verifier_rejects_invalid_versions(monkeypatch, package):
    main = runpy.run_path(str(VERIFY))["main"]
    monkeypatch.setitem(main.__globals__, "version", lambda name: "invalid" if package == "pip" else "26.2.2")
    monkeypatch.setattr(
        main.__globals__["certifi"], "__version__", "invalid" if package == "certifi" else "2026.10.19"
    )
    monkeypatch.setattr(sys, "argv", [str(VERIFY)])
    with pytest.raises(ValueError, match="Invalid version"):
        main()


@pytest.mark.parametrize(
    ("workflow", "job", "require_certifi"),
    [("test.yml", "test", True), ("test.yml", "build", False), ("release.yml", "release", True)],
)
def test_workflows_keep_packaging_security_check_after_installation(workflow, job, require_certifi):
    data = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8"))
    steps = data["jobs"][job]["steps"]
    bootstrap_index = next(i for i, step in enumerate(steps) if step.get("name") == "Bootstrap secure pip")
    verify_index = next(
        i for i, step in enumerate(steps) if step.get("name") == "Verify Python packaging security"
    )
    assert steps[bootstrap_index]["run"] == "./.github/scripts/bootstrap-pip.ps1"
    assert any("pip install" in step.get("run", "") for step in steps[bootstrap_index + 1 : verify_index])
    expected = "python .github/scripts/verify-python-security.py"
    assert steps[verify_index]["run"] == expected + (" --require-certifi" if require_certifi else "")
    assert "if" not in steps[verify_index] and "continue-on-error" not in steps[verify_index]
