from __future__ import annotations

import json

from conftest import run_cli


def test_help_lists_core_commands(isolated_env):
    result = run_cli(["--help"], isolated_env)

    assert result.returncode == 0
    assert "scan" in result.stdout
    assert "preview" in result.stdout
    assert "rollback" in result.stdout


def test_stage_apply_rollback_are_explicitly_not_implemented(isolated_env):
    for command in ("stage", "apply", "rollback"):
        result = run_cli([command, "plan_123", "--json"], isolated_env)

        assert result.returncode == 2
        payload = json.loads(result.stdout)
        assert payload["status"] == "not_implemented"
        assert payload["command"] == command


def test_preview_run_id_is_explicitly_not_implemented(isolated_env):
    result = run_cli(["preview", "run_123", "--json"], isolated_env)

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "not_implemented"
    assert payload["run_id"] == "run_123"
