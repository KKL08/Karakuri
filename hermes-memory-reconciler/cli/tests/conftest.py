from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FIXTURES = ROOT / "tests" / "fixtures"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    hermes_home = tmp_path / "hermes-home"
    artifact_home = tmp_path / "memory-reconciler"
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("MEMORY_RECONCILER_HOME", str(artifact_home))
    monkeypatch.setenv("HOME", str(fake_home))
    return {
        "HERMES_HOME": str(hermes_home),
        "MEMORY_RECONCILER_HOME": str(artifact_home),
        "HOME": str(fake_home),
    }


def run_cli(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    command_env.update(env)
    command_env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "memory_reconciler.cli", *args],
        cwd=ROOT,
        env=command_env,
        text=True,
        capture_output=True,
        check=False,
    )
