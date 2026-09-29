import importlib.util as _ilu
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "fullstack_architect_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# print helpers
# ---------------------------------------------------------------------------

def test_print_success_shows_message(capsys):
    tool.print_success("done")
    assert "done" in capsys.readouterr().out


def test_print_error_shows_message(capsys):
    tool.print_error("oops")
    assert "oops" in capsys.readouterr().out


def test_print_warning_shows_message(capsys):
    tool.print_warning("careful")
    assert "careful" in capsys.readouterr().out


def test_print_info_shows_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_shows_arrow_and_message(capsys):
    tool.print_header("Section")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section" in out


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_success_returns_real_stdout():
    code, out, err = tool.run_command("echo hello-fullstack")
    assert code == 0
    assert "hello-fullstack" in out


def test_run_command_nonzero_exit_returns_real_code():
    code, out, err = tool.run_command("exit 5")
    assert code == 5


def test_run_command_exception_returns_default_error_tuple(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(tool.subprocess, "run", boom)
    assert tool.run_command("anything") == (1, "", "Error")


# ---------------------------------------------------------------------------
# design_system
# ---------------------------------------------------------------------------

def test_design_system_writes_requirements_and_sections(tmp_path, capsys):
    args = _Args(name="Order Service", requirements="fast checkout,secure payments", output=str(tmp_path))
    rc = tool.design_system(args)
    assert rc == 0
    content = (tmp_path / "order-service-design.md").read_text()
    assert "# System Design: Order Service" in content
    assert "- fast checkout" in content
    assert "- secure payments" in content
    assert "## 2. System Architecture" in content
    assert "## 9. Cost Estimation" in content
    out = capsys.readouterr().out
    assert "Created:" in out


def test_design_system_default_requirements_when_none(tmp_path):
    args = _Args(name="Widget", requirements=None, output=str(tmp_path))
    tool.design_system(args)
    content = (tmp_path / "widget-design.md").read_text()
    assert "### Functional Requirements\n\n### Non-Functional Requirements" in content


def test_design_system_lowercases_and_hyphenates_filename(tmp_path):
    args = _Args(name="My Cool System", requirements=None, output=str(tmp_path))
    tool.design_system(args)
    assert (tmp_path / "my-cool-system-design.md").exists()


def test_design_system_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.design_system(_Args(name="Widget", requirements=None, output=None))
    assert (tmp_path / "docs" / "architecture" / "widget-design.md").exists()


# ---------------------------------------------------------------------------
# create_adr
# ---------------------------------------------------------------------------

def test_create_adr_default_number_and_status(tmp_path, capsys):
    args = _Args(title="Use Postgres", number=None, status=None, output=str(tmp_path))
    rc = tool.create_adr(args)
    assert rc == 0
    content = (tmp_path / "001-use-postgres.md").read_text()
    assert "# ADR-001: Use Postgres" in content
    assert "**Status:** Proposed" in content
    out = capsys.readouterr().out
    assert "ADR Number: 001" in out


def test_create_adr_custom_number_and_status_zero_padded(tmp_path):
    args = _Args(title="Use Redis", number=42, status="Accepted", output=str(tmp_path))
    tool.create_adr(args)
    content = (tmp_path / "042-use-redis.md").read_text()
    assert "# ADR-042: Use Redis" in content
    assert "**Status:** Accepted" in content


def test_create_adr_uses_default_output_dir_when_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_adr(_Args(title="Use Postgres", number=None, status=None, output=None))
    assert (tmp_path / "docs" / "adr" / "001-use-postgres.md").exists()


# ---------------------------------------------------------------------------
# diagram_architecture
# ---------------------------------------------------------------------------

def test_diagram_architecture_c4_default(capsys):
    rc = tool.diagram_architecture(_Args(type=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "C4 Model Diagrams" in out
    assert "Context Diagram:" in out


def test_diagram_architecture_sequence(capsys):
    tool.diagram_architecture(_Args(type="sequence"))
    out = capsys.readouterr().out
    assert "@startuml" in out
    assert "POST /api/v1/auth/login" in out


def test_diagram_architecture_deployment(capsys):
    tool.diagram_architecture(_Args(type="deployment"))
    out = capsys.readouterr().out
    assert "Load Balancer" in out
    assert "PostgreSQL" in out


def test_diagram_architecture_prints_footer(capsys):
    tool.diagram_architecture(_Args(type="c4"))
    out = capsys.readouterr().out
    assert "Diagram templates generated" in out
    assert "PlantUML" in out


# ---------------------------------------------------------------------------
# evaluate_tradeoffs
# ---------------------------------------------------------------------------

def test_evaluate_tradeoffs_known_choice_prints_all_options(capsys):
    rc = tool.evaluate_tradeoffs(_Args(choice="database", options=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "PostgreSQL:" in out
    assert "MongoDB:" in out
    assert "DynamoDB:" in out


def test_evaluate_tradeoffs_is_case_insensitive(capsys):
    tool.evaluate_tradeoffs(_Args(choice="DATABASE", options=None))
    out = capsys.readouterr().out
    assert "PostgreSQL:" in out


def test_evaluate_tradeoffs_unknown_choice_warns(capsys):
    tool.evaluate_tradeoffs(_Args(choice="blockchain", options=None))
    out = capsys.readouterr().out
    assert "No predefined tradeoffs for 'blockchain'" in out


def test_evaluate_tradeoffs_prints_provided_options(capsys):
    tool.evaluate_tradeoffs(_Args(choice="api", options="REST,GraphQL"))
    out = capsys.readouterr().out
    assert "Options: REST, GraphQL" in out


# ---------------------------------------------------------------------------
# plan_scaling
# ---------------------------------------------------------------------------

def test_plan_scaling_default_users(capsys):
    rc = tool.plan_scaling(_Args(current_users=None, target_users=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Current: 1,000 users" in out
    assert "Target: 100,000 users" in out
    assert "Growth: 100.0x" in out
    # target // 20000 == 5, so max(5, 5) == 5 -- lower bound is exercised
    # separately below.
    assert "Target: 5 API servers" in out
    assert "Read replicas: 2" in out


def test_plan_scaling_below_floor_uses_minimum_server_count(capsys):
    # target_users // 20000 == 0 for a small target, so max(5, 0) == 5.
    tool.plan_scaling(_Args(current_users=100, target_users=1000))
    out = capsys.readouterr().out
    assert "Target: 5 API servers" in out
    assert "Read replicas: 2" in out


def test_plan_scaling_large_target_scales_beyond_minimum(capsys):
    tool.plan_scaling(_Args(current_users=1000, target_users=1000000))
    out = capsys.readouterr().out
    assert "Target: 50 API servers" in out
    assert "Read replicas: 20" in out


# ---------------------------------------------------------------------------
# security_review
# ---------------------------------------------------------------------------

def test_security_review_prints_all_sections(capsys):
    rc = tool.security_review(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "## 1. Authentication & Authorization" in out
    assert "## 6. Monitoring & Audit" in out
    assert "Security checklist complete" in out


# ---------------------------------------------------------------------------
# cost_estimate
# ---------------------------------------------------------------------------

def test_cost_estimate_default_medium_traffic(capsys):
    rc = tool.cost_estimate(_Args(environment=None, traffic=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Environment: production" in out
    assert "Traffic: medium" in out
    assert "Estimated cost: $560/month" in out


def test_cost_estimate_low_traffic_totals_correctly(capsys):
    tool.cost_estimate(_Args(environment="staging", traffic="low"))
    out = capsys.readouterr().out
    assert "Estimated cost: $185/month" in out


def test_cost_estimate_high_traffic_totals_correctly(capsys):
    tool.cost_estimate(_Args(environment="production", traffic="high"))
    out = capsys.readouterr().out
    assert "Estimated cost: $1580/month" in out


def test_cost_estimate_unknown_traffic_falls_back_to_medium(capsys):
    # bypasses argparse's choices restriction by calling the function directly
    tool.cost_estimate(_Args(environment="production", traffic="ultra"))
    out = capsys.readouterr().out
    assert "Estimated cost: $560/month" in out


# ---------------------------------------------------------------------------
# tech_stack_recommendation
# ---------------------------------------------------------------------------

def test_tech_stack_recommendation_web_app(capsys):
    rc = tool.tech_stack_recommendation(_Args(project_type="web-app", team_size=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Frontend" in out
    assert "Next.js 14 (React 18, TypeScript, Tailwind CSS)" in out
    assert "Team Size: 5" in out


def test_tech_stack_recommendation_microservices(capsys):
    tool.tech_stack_recommendation(_Args(project_type="microservices", team_size=10))
    out = capsys.readouterr().out
    assert "Service Mesh" in out
    assert "Istio or Linkerd" in out
    assert "Team Size: 10" in out


def test_tech_stack_recommendation_unknown_type_warns(capsys):
    tool.tech_stack_recommendation(_Args(project_type="blockchain-app", team_size=None))
    out = capsys.readouterr().out
    assert "No recommendation for 'blockchain-app'" in out


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_design_system_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "design-system", "--name", "Cart", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "cart-design.md").exists()


def test_main_create_adr_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "create-adr", "--title", "Use Kafka", "--output", str(tmp_path)]
    )
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "001-use-kafka.md").exists()


def test_main_diagram_architecture_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "diagram-architecture", "--type", "sequence"])
    rc = tool.main()
    assert rc == 0
    assert "@startuml" in capsys.readouterr().out


def test_main_evaluate_tradeoffs_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "evaluate-tradeoffs", "--choice", "auth"])
    rc = tool.main()
    assert rc == 0
    assert "JWT:" in capsys.readouterr().out


def test_main_plan_scaling_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "plan-scaling", "--current-users", "500", "--target-users", "50000"]
    )
    rc = tool.main()
    assert rc == 0
    assert "Growth: 100.0x" in capsys.readouterr().out


def test_main_security_review_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "security-review"])
    rc = tool.main()
    assert rc == 0
    assert "Security checklist complete" in capsys.readouterr().out


def test_main_cost_estimate_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "cost-estimate", "--traffic", "low"])
    rc = tool.main()
    assert rc == 0
    assert "$185/month" in capsys.readouterr().out


def test_main_tech_stack_recommendation_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        _sys, "argv", ["tool.py", "tech-stack-recommendation", "--project-type", "api"]
    )
    rc = tool.main()
    assert rc == 0
    assert "OpenAPI/Swagger" in capsys.readouterr().out


def test_main_create_adr_missing_required_title_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-adr"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_evaluate_tradeoffs_missing_required_choice_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "evaluate-tradeoffs"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_tech_stack_recommendation_missing_required_project_type_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "tech-stack-recommendation"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_design_system_missing_required_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "design-system"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_diagram_architecture_rejects_invalid_type_choice(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "diagram-architecture", "--type", "bogus"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_cost_estimate_rejects_invalid_traffic_choice(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "cost-estimate", "--traffic", "ultra"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_unknown_command_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit):
        tool.main()


# ---------------------------------------------------------------------------
# subprocess smoke tests (real __main__ entrypoint end to end)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_test_security_review():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "security-review"], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert "Security checklist complete" in proc.stdout


def test_cli_subprocess_smoke_test_no_command_returns_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_test_design_system_writes_real_file(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "design-system", "--name", "Widget", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert (tmp_path / "widget-design.md").exists()
