import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("devops_engineer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_audit_pipeline_flags_missing_ci_workflow(tmp_path):
    findings = tool.audit_pipeline(tmp_path)
    assert findings["ci_workflow"]["present"] is False


def test_audit_pipeline_detects_present_ci_workflow(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
    findings = tool.audit_pipeline(tmp_path)
    assert findings["ci_workflow"]["present"] is True


def test_audit_pipeline_detects_dockerfile_without_healthcheck(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
    findings = tool.audit_pipeline(tmp_path)
    assert findings["dockerfile"]["present"] is True
    assert findings["healthcheck_in_dockerfile"]["present"] is False


def test_audit_pipeline_detects_healthcheck_present(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\nHEALTHCHECK CMD curl -f http://localhost/health\n")
    findings = tool.audit_pipeline(tmp_path)
    assert findings["healthcheck_in_dockerfile"]["present"] is True


def test_generate_runbook_returns_known_incident_steps():
    steps = tool.generate_runbook("deploy_failed")
    assert len(steps) >= 1


def test_generate_runbook_rejects_unknown_incident():
    try:
        tool.generate_runbook("alien_invasion")
        assert False, "expected ValueError"
    except ValueError:
        pass

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess
import sys as _sys


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_cmd_audit_pipeline_all_present_returns_0_and_prints_json(tmp_path, capsys):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\nHEALTHCHECK CMD curl -f http://localhost/health\n")
    args = _Args(project_root=str(tmp_path))
    rc = tool.cmd_audit_pipeline(args)
    out = capsys.readouterr().out
    assert rc == 0
    parsed = tool.json.loads(out)
    assert parsed["ci_workflow"]["present"] is True
    assert parsed["dockerfile"]["present"] is True
    assert parsed["healthcheck_in_dockerfile"]["present"] is True


def test_cmd_audit_pipeline_missing_everything_returns_1(tmp_path, capsys):
    args = _Args(project_root=str(tmp_path))
    rc = tool.cmd_audit_pipeline(args)
    out = capsys.readouterr().out
    assert rc == 1
    parsed = tool.json.loads(out)
    assert parsed["ci_workflow"]["present"] is False
    assert parsed["dockerfile"]["present"] is False
    assert parsed["healthcheck_in_dockerfile"]["present"] is False


def test_cmd_generate_runbook_known_prints_numbered_steps_and_returns_0(capsys):
    args = _Args(incident_type="database_connection_exhausted")
    rc = tool.cmd_generate_runbook(args)
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0
    assert out[0].startswith("1. ")
    assert len(out) == len(tool.RUNBOOKS["database_connection_exhausted"])


def test_cmd_generate_runbook_unknown_prints_message_and_returns_1(capsys):
    args = _Args(incident_type="alien_invasion")
    rc = tool.cmd_generate_runbook(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Unknown incident type" in out
    assert "alien_invasion" in out


def test_cmd_test_self_test_passes(capsys):
    args = _Args()
    rc = tool.cmd_test(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage" in captured.out.lower()


def test_main_audit_pipeline_end_to_end(monkeypatch, tmp_path, capsys):
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
    monkeypatch.setattr(_sys, "argv", ["tool.py", "audit-pipeline", str(tmp_path)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    parsed = tool.json.loads(out)
    assert parsed["dockerfile"]["present"] is True
    assert parsed["ci_workflow"]["present"] is False


def test_main_generate_runbook_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-runbook", "high_error_rate"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "1. Check recent deploys" in out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_generate_runbook_rejects_invalid_choice_via_argparse(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-runbook", "not_a_real_incident"])
    try:
        tool.main()
        assert False, "expected SystemExit from argparse choices validation"
    except SystemExit as e:
        assert e.code == 2


def test_main_audit_pipeline_missing_required_positional_raises_systemexit(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "audit-pipeline"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing project_root"
    except SystemExit as e:
        assert e.code == 2


def test_subprocess_runs_as_script_and_exercises_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [_sys.executable, str(script), "generate-runbook", "deploy_failed"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "1. Check build logs" in result.stdout
