from __future__ import annotations

import json
from pathlib import Path
from shutil import copytree

from conftest import FIXTURES, run_cli


def test_report_limits_output_and_next_question_returns_decisions(tmp_path, isolated_env):
    hermes_home = tmp_path / "hermes"
    copytree(FIXTURES / "hermes_basic", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    scan_result = run_cli(["scan", "--system", "hermes", "--json"], isolated_env)
    scan_payload = json.loads(scan_result.stdout)

    report_result = run_cli(["report", scan_payload["scan_id"], "--limit", "2", "--json"], isolated_env)
    question_result = run_cli(["next-question", scan_payload["scan_id"], "--json"], isolated_env)

    assert report_result.returncode == 0
    report = json.loads(report_result.stdout)
    assert report["scan_id"] == scan_payload["scan_id"]
    assert len(report["issues"]) <= 2
    assert "User prefers concise answers.\n- User prefers detailed" not in json.dumps(report)

    assert question_result.returncode == 0
    question = json.loads(question_result.stdout)
    assert question["conflict_id"].startswith("conflict_")
    assert question["choices"]
    assert all(choice["decision_id"].startswith("decision_") for choice in question["choices"])


def test_core_json_payloads_include_schema_version(tmp_path, isolated_env):
    hermes_home = tmp_path / "hermes"
    copytree(FIXTURES / "hermes_basic", hermes_home)
    isolated_env["HERMES_HOME"] = str(hermes_home)

    scan = json.loads(run_cli(["scan", "--system", "hermes", "--json"], isolated_env).stdout)
    report = json.loads(run_cli(["report", scan["scan_id"], "--json"], isolated_env).stdout)
    question = json.loads(run_cli(["next-question", scan["scan_id"], "--json"], isolated_env).stdout)
    resolution = json.loads(
        run_cli(
            [
                "resolve",
                question["conflict_id"],
                "--decision",
                question["choices"][0]["decision_id"],
                "--json",
            ],
            isolated_env,
        ).stdout
    )
    plan = json.loads(run_cli(["plan", resolution["resolution_id"], "--json"], isolated_env).stdout)
    preview = json.loads(run_cli(["preview", plan["plan_id"], "--json"], isolated_env).stdout)
    error = json.loads(run_cli(["preview", "bad_123", "--json"], isolated_env).stdout)

    assert scan["schema_version"] == 1
    assert report["schema_version"] == 1
    assert question["schema_version"] == 1
    assert resolution["schema_version"] == 1
    assert plan["schema_version"] == 1
    assert preview["schema_version"] == 1
    assert error["schema_version"] == 1
