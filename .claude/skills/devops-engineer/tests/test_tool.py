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
