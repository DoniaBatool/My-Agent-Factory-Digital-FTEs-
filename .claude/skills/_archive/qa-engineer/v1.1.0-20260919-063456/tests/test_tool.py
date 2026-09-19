import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("qa_engineer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_classify_severity_critical_for_data_loss():
    assert tool.classify_severity("This bug causes data loss on refresh") == "critical"


def test_classify_severity_high_for_crash():
    assert tool.classify_severity("App crashes when submitting the form") == "high"


def test_classify_severity_low_for_cosmetic():
    assert tool.classify_severity("Cosmetic misalignment on the settings page") == "low"


def test_classify_severity_defaults_to_medium_never_silently_low():
    assert tool.classify_severity("something odd happens sometimes") == "medium"


def test_build_test_plan_ranks_high_risk_flows_first():
    plan = tool.build_test_plan(["Display avatar", "Auth login", "Payment checkout"])
    assert plan[0]["risk"] == "high"
    assert plan[-1]["flow"] == "Display avatar"


def test_format_bug_report_infers_severity_from_actual_behavior():
    report = tool.format_bug_report("Save fails", ["click save"], "task is saved", "app crashes")
    assert report["severity"] == "high"
    assert report["repro_steps"] == ["click save"]


def test_run_pytest_suite_runs_real_pytest_and_reports_failure(tmp_path):
    """This is the load-bearing fix: the previous `test` command always
    printed success no matter what. This proves run-tests genuinely
    executes pytest and returns a non-zero exit code for a failing test."""
    (tmp_path / "test_intentional_failure.py").write_text("def test_x():\n    assert False\n")
    code, output = tool.run_pytest_suite(str(tmp_path))
    assert code != 0
    assert "1 failed" in output


def test_run_pytest_suite_reports_success_for_passing_tests(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_x():\n    assert True\n")
    code, output = tool.run_pytest_suite(str(tmp_path))
    assert code == 0
    assert "1 passed" in output
