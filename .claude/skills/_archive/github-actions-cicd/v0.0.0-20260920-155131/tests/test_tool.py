import importlib.util as _ilu
import json
import subprocess
import sys as _sys
from pathlib import Path

import pytest
import yaml

_spec = _ilu.spec_from_file_location(
    "github_actions_cicd_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class RecordingRunner:
    """Stand-in for tool.run_command that records every cmd it is asked to run
    and returns a canned (code, stdout, stderr) based on the first matching
    substring key in `mapping` (dict order matters), or `default` otherwise."""

    def __init__(self, mapping=None, default=(0, "", "")):
        self.calls = []
        self.mapping = mapping or {}
        self.default = default

    def __call__(self, cmd, timeout=300):
        self.calls.append(cmd)
        for key, resp in self.mapping.items():
            if key in cmd:
                return resp
        return self.default


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_contains_message_and_checkmark(capsys):
    tool.print_success("hello")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "✓" in out


def test_print_error_contains_message_and_x(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "bad thing" in out
    assert "✗" in out


def test_print_warning_contains_message_and_symbol(capsys):
    tool.print_warning("watch out")
    out = capsys.readouterr().out
    assert "watch out" in out
    assert "⚠" in out


def test_print_info_contains_message(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert "fyi" in out


def test_print_header_contains_arrow_and_message(capsys):
    tool.print_header("Section Title")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section Title" in out


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_returns_real_subprocess_output():
    code, out, err = tool.run_command("echo hi")
    assert code == 0
    assert out.strip() == "hi"
    assert err == ""


def test_run_command_returns_nonzero_on_failing_shell_command():
    code, out, err = tool.run_command("exit 4")
    assert code == 4


def test_run_command_handles_timeout(monkeypatch):
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("sleep 100", timeout=9)
    assert code == 1
    assert out == ""
    assert "timed out after 9s" in err


def test_run_command_handles_generic_exception(monkeypatch):
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        raise OSError("boom")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "boom"


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def _all_ok_prereq_mapping():
    return {
        "git --version": (0, "git version 2.42.0", ""),
        "gh --version": (0, "gh version 2.40.0 (2024-01-01)", ""),
        "gh auth status": (0, "Logged in", ""),
        "git rev-parse --is-inside-work-tree": (0, "true", ""),
        "git remote get-url origin": (0, "git@github.com:user/repo.git", ""),
    }


def test_check_prerequisites_all_pass_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(_all_ok_prereq_mapping()))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Passed: 5/5" in out
    assert "Failed: 0/5" in out
    assert "Git installed: git version 2.42.0" in out
    assert "GitHub CLI installed: 2.40.0" in out


def test_check_prerequisites_git_missing_fails(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["git --version"] = (1, "", "not found")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Passed: 4/5" in out
    assert "Failed: 1/5" in out
    assert "Git not installed" in out


def test_check_prerequisites_gh_cli_missing_fails(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["gh --version"] = (1, "", "not found")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "GitHub CLI not installed" in out


def test_check_prerequisites_not_authenticated_fails(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["gh auth status"] = (1, "", "not logged in")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not authenticated with GitHub" in out


def test_check_prerequisites_not_inside_git_repo_fails(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["git rev-parse --is-inside-work-tree"] = (1, "", "not a repo")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not inside a git repository" in out


def test_check_prerequisites_no_github_remote_fails_when_remote_missing(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["git remote get-url origin"] = (1, "", "no remote")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No GitHub remote configured" in out


def test_check_prerequisites_no_github_remote_fails_when_remote_is_non_github(monkeypatch, capsys):
    mapping = _all_ok_prereq_mapping()
    mapping["git remote get-url origin"] = (0, "git@gitlab.com:user/repo.git", "")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No GitHub remote configured" in out


def test_check_prerequisites_gh_version_parsing_raises_on_too_few_tokens(monkeypatch):
    # Documents actual current behavior: unlike the dapr-integration tool's
    # equivalent check, this one has no length guard before indexing [2],
    # so a short "gh --version" response crashes rather than degrading.
    mapping = _all_ok_prereq_mapping()
    mapping["gh --version"] = (0, "gh", "")
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    with pytest.raises(IndexError):
        tool.check_prerequisites(_Args())


# ---------------------------------------------------------------------------
# generate_workflow
# ---------------------------------------------------------------------------

def test_generate_workflow_creates_ci_and_default_environment_files(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(app_name=None, environments=None)
    rc = tool.generate_workflow(args)
    out = capsys.readouterr().out
    assert rc == 0
    wf_dir = tmp_path / ".github" / "workflows"
    assert (wf_dir / "ci.yml").exists()
    assert (wf_dir / "deploy-dev.yml").exists()
    assert (wf_dir / "deploy-staging.yml").exists()
    assert (wf_dir / "deploy-prod.yml").exists()
    assert "Generated 4 workflow files" in out

    ci_doc = yaml.safe_load((wf_dir / "ci.yml").read_text())
    assert ci_doc["name"] == "CI - Test and Build"
    assert ci_doc["on"]["push"]["branches"] == ["main", "develop", "feature/*"]
    assert ci_doc["jobs"]["build"]["needs"] == "test"
    assert ":app-" in ci_doc["jobs"]["build"]["steps"][-1]["with"]["tags"]  # default app_name is "app"
    assert ci_doc["jobs"]["build"]["steps"][-1]["with"]["push"] is True

    prod_doc = yaml.safe_load((wf_dir / "deploy-prod.yml").read_text())
    assert prod_doc["name"] == "CD - Deploy to PROD"
    assert prod_doc["on"]["push"]["branches"] == ["main"]
    assert prod_doc["jobs"]["deploy"]["environment"] == "prod"

    dev_doc = yaml.safe_load((wf_dir / "deploy-dev.yml").read_text())
    assert dev_doc["on"]["push"]["branches"] == ["dev/*"]


def test_generate_workflow_ci_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tool.generate_workflow(_Args(app_name=None, environments="prod"))
    text = (tmp_path / ".github" / "workflows" / "ci.yml").read_text()
    assert not text.startswith("{")  # block style: a flow-style dump starts with "{name: ..."
    idx_test_job = text.find("  test:")
    idx_build_job = text.find("  build:")
    assert idx_test_job != -1 and idx_build_job != -1
    assert idx_test_job < idx_build_job  # jobs dict keeps insertion order (test, build)


def test_generate_workflow_cd_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tool.generate_workflow(_Args(app_name=None, environments="prod"))
    text = (tmp_path / ".github" / "workflows" / "deploy-prod.yml").read_text()
    assert not text.startswith("{")  # block style: a flow-style dump starts with "{name: ..."
    idx_on = text.find("'on':")
    idx_jobs = text.find("jobs:")
    assert idx_on != -1 and idx_jobs != -1
    assert idx_on < idx_jobs  # top-level dict keeps insertion order (name, on, jobs)


def test_generate_workflow_honors_custom_app_name_and_single_environment(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(app_name="myapp", environments="qa")
    rc = tool.generate_workflow(args)
    out = capsys.readouterr().out
    assert rc == 0
    wf_dir = tmp_path / ".github" / "workflows"
    assert (wf_dir / "deploy-qa.yml").exists()
    assert not (wf_dir / "deploy-prod.yml").exists()
    assert "Generated 2 workflow files" in out

    qa_doc = yaml.safe_load((wf_dir / "deploy-qa.yml").read_text())
    assert qa_doc["on"]["push"]["branches"] == ["qa/*"]
    assert qa_doc["jobs"]["deploy"]["environment"] == "qa"
    for step in qa_doc["jobs"]["deploy"]["steps"]:
        if "run" in step and "kubectl apply" in step["run"]:
            assert "myapp-qa" in step["run"]

    ci_doc = yaml.safe_load((wf_dir / "ci.yml").read_text())
    assert "myapp-" in ci_doc["jobs"]["build"]["steps"][-1]["with"]["tags"]


def test_generate_workflow_uses_default_environments_when_empty_string(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    rc = tool.generate_workflow(_Args(app_name=None, environments=""))
    assert rc == 0
    wf_dir = tmp_path / ".github" / "workflows"
    assert (wf_dir / "deploy-dev.yml").exists()
    assert (wf_dir / "deploy-staging.yml").exists()
    assert (wf_dir / "deploy-prod.yml").exists()


# ---------------------------------------------------------------------------
# setup_secrets
# ---------------------------------------------------------------------------

def test_setup_secrets_lists_required_secrets_and_returns_0(capsys, monkeypatch):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "DATABASE_URL\nJWT_SECRET", "")))
    rc = tool.setup_secrets(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "DATABASE_URL" in out
    assert "OPENAI_API_KEY" in out
    assert "JWT_SECRET" in out
    assert "gh secret set DATABASE_URL" in out
    assert "Existing secrets:" in out


def test_setup_secrets_warns_when_secret_list_command_fails(capsys, monkeypatch):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "not authenticated")))
    rc = tool.setup_secrets(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Could not list secrets" in out


# ---------------------------------------------------------------------------
# test_workflow
# ---------------------------------------------------------------------------

def test_test_workflow_returns_1_when_no_workflows_dir(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No workflows found" in out


def test_test_workflow_returns_1_when_dir_exists_but_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No workflow files found" in out


def test_test_workflow_passes_for_valid_workflow_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text(yaml.dump({"name": "CI", "on": {"push": {}}, "jobs": {"test": {}}}))
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Passed: 1/1" in out
    assert "Valid syntax" in out


def test_test_workflow_fails_when_name_field_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bad.yml").write_text(yaml.dump({"on": {"push": {}}, "jobs": {"test": {}}}))
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Missing 'name' field" in out
    assert "Failed: 1/1" in out


def test_test_workflow_fails_when_on_field_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bad.yml").write_text(yaml.dump({"name": "CI", "jobs": {"test": {}}}))
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Missing 'on' (trigger) field" in out


def test_test_workflow_fails_when_jobs_field_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bad.yml").write_text(yaml.dump({"name": "CI", "on": {"push": {}}}))
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Missing 'jobs' field" in out


def test_test_workflow_reports_yaml_syntax_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "bad.yml").write_text("name: [unterminated\n  - broken: [")
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "YAML syntax error" in out


def test_test_workflow_reports_generic_error_for_empty_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "empty.yml").write_text("")  # parses to None -> 'name' not in None -> TypeError
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Error:" in out


def test_test_workflow_aggregates_pass_and_fail_counts_across_files(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "good.yml").write_text(yaml.dump({"name": "CI", "on": {"push": {}}, "jobs": {"test": {}}}))
    (wf_dir / "bad.yaml").write_text(yaml.dump({"on": {"push": {}}, "jobs": {"test": {}}}))
    rc = tool.test_workflow(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Passed: 1/2" in out
    assert "Failed: 1/2" in out


# ---------------------------------------------------------------------------
# enable_actions
# ---------------------------------------------------------------------------

def test_enable_actions_returns_1_when_api_call_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "not found")))
    rc = tool.enable_actions(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Could not fetch repository info" in out


def test_enable_actions_reports_already_enabled(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, json.dumps({"has_actions": True}), "")))
    rc = tool.enable_actions(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "already enabled" in out


def test_enable_actions_reports_not_enabled(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, json.dumps({"has_actions": False}), "")))
    rc = tool.enable_actions(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "GitHub Actions not enabled" in out


def test_enable_actions_defaults_to_not_enabled_when_key_missing(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, json.dumps({}), "")))
    rc = tool.enable_actions(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "GitHub Actions not enabled" in out


# ---------------------------------------------------------------------------
# monitor
# ---------------------------------------------------------------------------

def test_monitor_returns_1_when_fetch_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "api error")))
    rc = tool.monitor(_Args(limit=None))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Could not fetch workflow runs" in out
    assert "api error" in out


def test_monitor_warns_when_no_runs_found(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "[]", "")))
    rc = tool.monitor(_Args(limit=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "No workflow runs found" in out


def test_monitor_uses_default_limit_of_10_in_command(monkeypatch):
    runner = RecordingRunner(default=(0, "[]", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    tool.monitor(_Args(limit=None))
    assert "--limit 10" in runner.calls[0]


def test_monitor_honors_custom_limit_in_command(monkeypatch):
    runner = RecordingRunner(default=(0, "[]", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    tool.monitor(_Args(limit=5))
    assert "--limit 5" in runner.calls[0]


def test_monitor_prints_icons_and_fields_for_each_status_kind(monkeypatch, capsys):
    runs = [
        {"status": "completed", "conclusion": "success", "name": "CI", "createdAt": "t1", "url": "u1"},
        {"status": "completed", "conclusion": "failure", "name": "CD", "createdAt": "t2", "url": "u2"},
        {"status": "in_progress", "conclusion": "", "name": "Deploy", "createdAt": "t3", "url": "u3"},
        {"status": "queued", "conclusion": "", "name": "Lint", "createdAt": "t4", "url": "u4"},
        {"status": "mystery_status", "conclusion": "", "name": "Odd", "createdAt": "t5", "url": "u5"},
    ]
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, json.dumps(runs), "")))
    rc = tool.monitor(_Args(limit=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Found 5 recent runs" in out
    assert "✅ CI" in out
    assert "❌ CD" in out
    assert "\U0001F504 Deploy" in out
    assert "⏳ Lint" in out
    assert "❓ Odd" in out
    assert "(success)" in out
    assert "Status: in_progress " in out  # empty conclusion -> no parens suffix


# ---------------------------------------------------------------------------
# troubleshoot
# ---------------------------------------------------------------------------

def test_troubleshoot_returns_1_when_fetch_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "err")))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Could not fetch failed runs" in out


def test_troubleshoot_reports_no_failures(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "[]", "")))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No recent failures" in out


def test_troubleshoot_prints_failed_runs_and_fetches_logs(monkeypatch, capsys):
    failed_runs = [
        {"databaseId": 111, "name": "CI failed", "url": "http://x/1"},
        {"databaseId": 222, "name": "CD failed", "url": "http://x/2"},
    ]
    mapping = {
        "gh run list --status failure": (0, json.dumps(failed_runs), ""),
        "gh run view 111 --log-failed": (0, "some log output " * 5, ""),
        "gh run view 222 --log-failed": (1, "", "no logs"),
    }
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "CI failed (ID: 111)" in out
    assert "CD failed (ID: 222)" in out
    assert "some log output" in out
    assert "Common Issues & Fixes" in out


def test_troubleshoot_truncates_logs_to_500_chars(monkeypatch, capsys):
    long_logs = "x" * 600
    mapping = {
        "gh run list --status failure": (0, json.dumps([{"databaseId": 1, "name": "n", "url": "u"}]), ""),
        "gh run view 1 --log-failed": (0, long_logs, ""),
    }
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert "x" * 500 in out
    assert "x" * 501 not in out


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def test_cleanup_returns_1_when_list_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "boom")))
    rc = tool.cleanup(_Args(days=None))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Could not fetch workflow runs" in out


def test_cleanup_uses_default_days_message(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "[]", "")))
    tool.cleanup(_Args(days=None))
    out = capsys.readouterr().out
    assert "older than 30 days" in out


def test_cleanup_uses_custom_days_message(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "[]", "")))
    tool.cleanup(_Args(days=7))
    out = capsys.readouterr().out
    assert "older than 7 days" in out


def test_cleanup_counts_only_successful_deletions(monkeypatch, capsys):
    runs = [{"databaseId": 1}, {"databaseId": 2}, {"databaseId": 3}]
    mapping = {
        "gh run list --status completed": (0, json.dumps(runs), ""),
        "gh run delete 1 --yes": (0, "", ""),
        "gh run delete 2 --yes": (1, "", "permission denied"),
        "gh run delete 3 --yes": (0, "", ""),
    }
    monkeypatch.setattr(tool, "run_command", RecordingRunner(mapping))
    rc = tool.cleanup(_Args(days=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Deleted 2 old workflow runs" in out


def test_cleanup_with_no_runs_deletes_nothing(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "[]", "")))
    rc = tool.cleanup(_Args(days=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Deleted 0 old workflow runs" in out


# ---------------------------------------------------------------------------
# run_tests_cmd
# ---------------------------------------------------------------------------

def _stub_cmd_functions(monkeypatch, prereq=0, workflow=0, actions=0):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: prereq)
    monkeypatch.setattr(tool, "test_workflow", lambda a: workflow)
    monkeypatch.setattr(tool, "enable_actions", lambda a: actions)


def test_run_tests_cmd_all_healthy_returns_0(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch)
    runner = RecordingRunner({
        "gh secret list": (0, "SOME_SECRET", ""),
        "gh run list --limit 1": (0, "[]", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total tests: 6" in out
    assert "Passed: 6" in out
    assert "All tests passed" in out


def test_run_tests_cmd_prerequisites_failure_causes_overall_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch, prereq=1)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "S", ""), "gh run list --limit 1": (0, "[]", ""),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Prerequisites check failed" in out


def test_run_tests_cmd_missing_workflow_files_causes_overall_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)  # no .github/workflows at all
    _stub_cmd_functions(monkeypatch)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "S", ""), "gh run list --limit 1": (0, "[]", ""),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No workflow files found" in out


def test_run_tests_cmd_workflow_syntax_failure_causes_overall_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch, workflow=1)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "S", ""), "gh run list --limit 1": (0, "[]", ""),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Workflow syntax errors found" in out


def test_run_tests_cmd_actions_not_enabled_causes_overall_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch, actions=1)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "S", ""), "gh run list --limit 1": (0, "[]", ""),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "GitHub Actions check failed" in out


def test_run_tests_cmd_no_secrets_configured_causes_overall_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "   ", ""), "gh run list --limit 1": (0, "[]", ""),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No secrets found" in out


def test_run_tests_cmd_no_workflow_runs_yet_is_not_fatal(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\n")
    _stub_cmd_functions(monkeypatch)
    monkeypatch.setattr(tool, "run_command", RecordingRunner({
        "gh secret list": (0, "S", ""), "gh run list --limit 1": (1, "", "no runs"),
    }))
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No workflow runs yet" in out


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_rejects_unknown_subcommand_with_system_exit(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_check_prerequisites(monkeypatch):
    called = {}

    def fake(a):
        called["hit"] = True
        return 0

    monkeypatch.setattr(tool, "check_prerequisites", fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-prerequisites"])
    assert tool.main() == 0
    assert called.get("hit")


def test_main_dispatches_generate_workflow_with_parsed_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "generate_workflow", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "generate-workflow", "--app-name", "svc", "--environments", "qa,prod",
    ])
    assert tool.main() == 0
    assert captured["app_name"] == "svc"
    assert captured["environments"] == "qa,prod"


def test_main_dispatches_generate_workflow_with_defaults(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "generate_workflow", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-workflow"])
    assert tool.main() == 0
    assert captured["app_name"] == "app"
    assert captured["environments"] == "dev,staging,prod"


def test_main_dispatches_setup_secrets(monkeypatch):
    monkeypatch.setattr(tool, "setup_secrets", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-secrets"])
    assert tool.main() == 0


def test_main_dispatches_test_workflow(monkeypatch):
    monkeypatch.setattr(tool, "test_workflow", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test-workflow"])
    assert tool.main() == 0


def test_main_dispatches_enable_actions(monkeypatch):
    monkeypatch.setattr(tool, "enable_actions", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "enable-actions"])
    assert tool.main() == 0


def test_main_dispatches_monitor_with_parsed_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "monitor", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "monitor", "--limit", "3"])
    assert tool.main() == 0
    assert captured["limit"] == 3


def test_main_dispatches_monitor_with_default_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "monitor", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "monitor"])
    assert tool.main() == 0
    assert captured["limit"] == 10


def test_main_dispatches_troubleshoot(monkeypatch):
    monkeypatch.setattr(tool, "troubleshoot", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot"])
    assert tool.main() == 0


def test_main_dispatches_cleanup_with_parsed_days(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "cleanup", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "cleanup", "--days", "14"])
    assert tool.main() == 0
    assert captured["days"] == 14


def test_main_dispatches_test_subcommand(monkeypatch):
    monkeypatch.setattr(tool, "run_tests_cmd", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    assert tool.main() == 0


# ---------------------------------------------------------------------------
# subprocess smoke test (real __main__ entrypoint; only file-only commands
# are exercised here to avoid any real `gh`/network call)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_no_command_prints_usage_and_exits_1():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_generate_workflow_end_to_end(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "generate-workflow", "--app-name", "demo", "--environments", "prod"],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert proc.returncode == 0
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    assert (tmp_path / ".github" / "workflows" / "deploy-prod.yml").exists()
