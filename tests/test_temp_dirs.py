import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import smoke_test

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("preexisting", [False, True])
def test_pytest_creates_temp_tree_and_keeps_databases_isolated(tmp_path, preexisting):
    project = tmp_path / "project"
    tests = project / "tests"
    tests.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests" / "conftest.py", tests / "conftest.py")
    (project / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    (tests / "test_isolation.py").write_text(
        """import pytest


@pytest.mark.parametrize("username", ["alice", "alice"])
def test_isolated_database(client, username):
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "Public-test-password-2026!"},
    )
    assert response.status_code == 201
""",
        encoding="utf-8",
    )
    temporary_root = project / ".tmp"
    basetemp = temporary_root / "pytest"
    if preexisting:
        temporary_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        basetemp.mkdir(mode=0o700, parents=True, exist_ok=True)
    else:
        assert not temporary_root.exists()

    # Nested pytest exercises the real copied conftest, independent of the
    # outer run's coverage and plugin configuration.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("COV_CORE", "COVERAGE", "PYTEST"))
    }
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--basetemp=.tmp/pytest"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(list(basetemp.rglob("test.db"))) == 2
    if os.name == "posix":
        assert stat.S_IMODE(temporary_root.stat().st_mode) == 0o700
        assert stat.S_IMODE(basetemp.stat().st_mode) == 0o700


def test_smoke_creates_missing_parents_and_isolated_temp_directories(
    tmp_path, monkeypatch
):
    root = tmp_path / "missing" / "checkout"
    monkeypatch.setattr(smoke_test, "ROOT", root)
    with smoke_test.temporary_directory() as first:
        with smoke_test.temporary_directory() as second:
            assert first != second
            assert first.is_dir() and second.is_dir()
            assert first.parent == second.parent == root / ".tmp"
            if os.name == "posix":
                assert stat.S_IMODE(first.parent.stat().st_mode) == 0o700
        assert not second.exists()
        assert first.is_dir()
    assert not first.exists()
