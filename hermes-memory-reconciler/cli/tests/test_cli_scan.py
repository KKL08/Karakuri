from __future__ import annotations

import json
from pathlib import Path
from shutil import copytree

from conftest import FIXTURES, run_cli


def test_missing_hermes_home_returns_missing_profile(isolated_env):
    result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["status"] == "missing_profile"
    assert "scan_id" not in payload


def test_uses_hermes_home_env_before_default_home(tmp_path, isolated_env):
    default_home = Path(isolated_env["HOME"]) / ".hermes"
    copytree(FIXTURES / "hermes_dangerous", default_home)
    custom_home = tmp_path / "custom-hermes"
    copytree(FIXTURES / "hermes_basic", custom_home)
    isolated_env["HERMES_HOME"] = str(custom_home)

    result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    scan_path = Path(payload["summary_path"])
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    source_paths = "\n".join(scan["source_files"])
    assert str(custom_home) in source_paths
    assert str(default_home) not in source_paths


def test_missing_memory_md_returns_partial_scan(tmp_path, isolated_env):
    hermes_home = tmp_path / "partial-hermes"
    copytree(FIXTURES / "hermes_missing_memory", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["files_scanned"] == 1
    assert payload["missing_files"] == ["MEMORY.md"]


def test_default_tests_do_not_touch_real_home(tmp_path, isolated_env):
    hermes_home = tmp_path / "custom-hermes"
    copytree(FIXTURES / "hermes_basic", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)

    assert result.returncode == 0
    assert not (Path(isolated_env["HOME"]) / ".memory-reconciler").exists()
    assert Path(isolated_env["MEMORY_RECONCILER_HOME"]).exists()


def test_scan_stdout_is_summary_not_raw_memory(tmp_path, isolated_env):
    hermes_home = tmp_path / "dangerous-hermes"
    copytree(FIXTURES / "hermes_dangerous", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "memory_entries" not in payload
    assert "issue_items" not in payload
    assert "sk-live-1234567890abcdef1234567890abcdef" not in result.stdout
