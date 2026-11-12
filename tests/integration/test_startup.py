"""Exercise the real shell startup with a fake interpreter; never install packages or models."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FAKE_PYTHON = r"""
import hashlib, json, os, pathlib, shutil, sys
args = sys.argv[1:]
root = pathlib.Path.cwd()
with open(os.environ['FAKE_LOG'], 'a') as handle:
    handle.write(json.dumps(args) + '\n')
if args[:2] == ['-m', 'venv']:
    destination = root / args[2] / 'bin'
    destination.mkdir(parents=True)
    shutil.copyfile(__file__, destination / 'python')
    (destination / 'python').chmod(0o755)
elif args[:2] == ['-m', 'pip']:
    if 'install' in args:
        if os.environ.get('FAIL_INSTALL'):
            raise SystemExit(1)
        (root / '.deps-ok').touch()
elif args and args[0] == 'scripts/check_environment.py':
    if not (root / '.deps-ok').exists():
        raise SystemExit(1)
elif args and args[0] == 'scripts/generate_data.py':
    (root / 'data' / 'synthetic_expenses.csv').write_text('demo')
elif args[:2] == ['-m', 'streamlit']:
    print('FAKE STREAMLIT STARTED')
elif args and args[0] == '-c':
    if 'hashlib' in args[1]:
        exec(args[1])
    elif os.environ.get('UNSUPPORTED_PYTHON'):
        raise SystemExit(1)
else:
    raise SystemExit('Unexpected command: ' + repr(args))
"""


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project with spaces"
    root.mkdir()
    shutil.copy(ROOT / "start.sh", root / "start.sh")
    (root / "requirements.txt").write_text("example==1.0\n")
    (root / ".env.example").write_text("OLLAMA_MODEL=qwen3:4b-q4_K_M\n")
    fake = tmp_path / "fake-python"
    # /usr/bin/env avoids an invalid shebang when the repository path contains spaces.
    fake.write_text("#!/usr/bin/env python3\n" + FAKE_PYTHON)
    fake.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    env = dict(os.environ, EXPENSEGUARD_PYTHON=str(fake), FAKE_LOG=str(log))
    return root, log, env


def invoke(project, **updates):
    root, log, env = project
    return subprocess.run(
        ["bash", str(root / "start.sh")],
        cwd=root.parent,
        env=dict(env, **updates),
        capture_output=True,
        text=True,
        timeout=30,
    )


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_first_run_and_repeat_skips_installation(project):
    root, log, _ = project
    result = invoke(project)
    assert result.returncode == 0, result.stderr
    assert "Dependencies installed" in result.stdout
    assert "FAKE STREAMLIT STARTED" in result.stdout
    assert (root / ".env").is_file()
    assert (root / "data/synthetic_expenses.csv").exists()
    assert (root / ".venv/.expenseguard-dependencies.sha256").exists()
    assert not (root / ".venv/.expenseguard-setup.lock").exists()
    repeat = invoke(project)
    assert repeat.returncode == 0, repeat.stderr
    assert "skipping installation" in repeat.stdout
    installs = [item for item in calls(log) if item[:3] == ["-m", "pip", "install"]]
    assert len(installs) == 1
    assert not any("pull" in item for item in calls(log))


def test_missing_dependency_and_changed_lock_reinstall(project):
    root, log, _ = project
    assert invoke(project).returncode == 0
    (root / ".deps-ok").unlink()
    assert invoke(project).returncode == 0
    (root / "requirements.txt").write_text("example==2.0\n")
    assert invoke(project).returncode == 0
    assert len([x for x in calls(log) if x[:3] == ["-m", "pip", "install"]]) == 3


def test_failed_install_does_not_stamp_and_can_retry(project):
    root, _, _ = project
    result = invoke(project, FAIL_INSTALL="1")
    assert result.returncode != 0
    assert "Startup failed" in result.stderr
    assert not (root / ".venv/.expenseguard-dependencies.sha256").exists()
    assert not (root / ".venv/.expenseguard-setup.lock").exists()
    assert invoke(project).returncode == 0


def test_missing_python_is_actionable(project):
    result = invoke(project, EXPENSEGUARD_PYTHON="/nonexistent/python")
    assert result.returncode != 0
    assert "Install Python 3.11 or 3.12" in result.stderr


def test_unsupported_python_is_rejected(project):
    result = invoke(project, UNSUPPORTED_PYTHON="1")
    assert result.returncode != 0
    assert "Install Python" in result.stderr


def test_incomplete_environment_and_concurrent_setup(project):
    root, _, _ = project
    (root / ".venv").mkdir()
    result = invoke(project)
    assert result.returncode != 0
    assert "incomplete" in result.stderr
    shutil.rmtree(root / ".venv")
    assert invoke(project).returncode == 0
    (root / ".venv/.expenseguard-setup.lock").mkdir()
    result = invoke(project)
    assert result.returncode != 0
    assert "Another startup" in result.stderr


def test_script_syntax_and_executable():
    subprocess.run(["bash", "-n", str(ROOT / "start.sh")], check=True)
    assert os.access(ROOT / "start.sh", os.X_OK)
