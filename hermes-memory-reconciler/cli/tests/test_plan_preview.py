from __future__ import annotations

import json
from pathlib import Path
from shutil import copytree

from conftest import FIXTURES, run_cli


def test_resolve_plan_preview_does_not_write_source_files(tmp_path, isolated_env):
    hermes_home = tmp_path / "hermes"
    copytree(FIXTURES / "hermes_basic", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)
    user_path = hermes_home / "memories" / "USER.md"
    before = user_path.read_text(encoding="utf-8")

    scan = json.loads(run_cli(["scan", "--system", "hermes", "--json"], isolated_env).stdout)
    question = json.loads(run_cli(["next-question", scan["scan_id"], "--json"], isolated_env).stdout)
    decision_id = question["choices"][0]["decision_id"]

    resolution_result = run_cli(
        [
            "resolve",
            question["conflict_id"],
            "--decision",
            decision_id,
            "--note",
            "Prefer concise by default, expand for complex tradeoffs.",
            "--json",
        ],
        isolated_env,
    )
    resolution = json.loads(resolution_result.stdout)
    plan_result = run_cli(["plan", resolution["resolution_id"], "--json"], isolated_env)
    plan = json.loads(plan_result.stdout)
    preview_result = run_cli(["preview", plan["plan_id"], "--json"], isolated_env)
    preview = json.loads(preview_result.stdout)
    artifact_root = Path(isolated_env["MEMORY_RECONCILER_HOME"])

    assert resolution_result.returncode == 0
    assert plan_result.returncode == 0
    assert preview_result.returncode == 0
    assert plan["actions"]
    assert plan["actions"][0]["entry_id"]
    assert plan["actions"][0]["start_line"]
    assert plan["actions"][0]["end_line"]
    assert "quarantine" not in {action["action"] for action in plan["actions"]}
    assert preview["plan_id"] == plan["plan_id"]
    assert "run_id" not in preview
    assert not (artifact_root / "runs").exists()
    assert user_path.read_text(encoding="utf-8") == before


def test_preview_rejects_unknown_id(isolated_env):
    result = run_cli(["preview", "weird_123", "--json"], isolated_env)

    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "unknown_preview_id"


def test_plan_and_preview_redact_secrets_in_stdout(tmp_path, isolated_env):
    hermes_home = tmp_path / "dangerous-hermes"
    copytree(FIXTURES / "hermes_dangerous", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    scan = json.loads(run_cli(["scan", "--system", "hermes", "--json"], isolated_env).stdout)
    question = json.loads(run_cli(["next-question", scan["scan_id"], "--json"], isolated_env).stdout)
    resolution = json.loads(
        run_cli(
            [
                "resolve",
                question["conflict_id"],
                "--decision",
                "decision_remove_unsafe",
                "--json",
            ],
            isolated_env,
        ).stdout
    )

    plan_result = run_cli(["plan", resolution["resolution_id"], "--json"], isolated_env)
    plan = json.loads(plan_result.stdout)
    preview_result = run_cli(["preview", plan["plan_id"], "--json"], isolated_env)
    preview = json.loads(preview_result.stdout)

    assert plan_result.returncode == 0
    assert preview_result.returncode == 0
    assert "sk-live-1234567890abcdef1234567890abcdef" not in plan_result.stdout
    assert "sk-live-1234567890abcdef1234567890abcdef" not in preview_result.stdout
    assert "[REDACTED_SECRET]" in json.dumps(plan)
    assert "[REDACTED_SECRET]" in json.dumps(preview)
