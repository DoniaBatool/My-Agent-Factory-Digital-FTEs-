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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess as _subprocess
import pytest


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- classify_severity / build_test_plan edge cases -------------------------

def test_classify_severity_prioritizes_critical_over_high_when_both_match():
    assert tool.classify_severity("app crashes and cannot login") == "critical"


def test_classify_severity_matches_cannot_log_in_with_space():
    assert tool.classify_severity("cannot log in to the app") == "critical"


def test_build_test_plan_matches_multiword_keyword():
    plan = tool.build_test_plan(["User isolation check"])
    assert plan[0]["risk"] == "high"


def test_build_test_plan_defaults_unrecognized_flow_to_medium():
    plan = tool.build_test_plan(["Some totally unrelated flow"])
    assert plan[0]["risk"] == "medium"


# --- CLI layer: cmd_* functions ----------------------------------------------

def test_cmd_build_test_plan_splits_flows_and_prints_json(capsys):
    rc = tool.cmd_build_test_plan(_Args(flows="Auth login,Display avatar"))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["flow"] == "Auth login"
    assert data[0]["risk"] == "high"


def test_cmd_classify_severity_prints_result(capsys):
    rc = tool.cmd_classify_severity(_Args(description="App crashes on save"))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "high"


def test_cmd_format_bug_report_splits_repro_steps_on_semicolons(capsys):
    rc = tool.cmd_format_bug_report(_Args(
        title="X", repro="open app;click save;observe crash",
        expected="saves", actual="crashes", environment="staging",
    ))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["repro_steps"] == ["open app", "click save", "observe crash"]
    assert data["environment"] == "staging"


def test_cmd_run_tests_prints_pass_gate_on_success(tmp_path, capsys):
    (tmp_path / "test_ok.py").write_text("def test_x():\n    assert True\n")
    rc = tool.cmd_run_tests(_Args(target=str(tmp_path)))
    assert rc == 0
    assert "QA GATE: PASS" in capsys.readouterr().out


def test_cmd_run_tests_prints_fail_gate_on_failure(tmp_path, capsys):
    (tmp_path / "test_bad.py").write_text("def test_x():\n    assert False\n")
    rc = tool.cmd_run_tests(_Args(target=str(tmp_path)))
    assert rc != 0
    assert "QA GATE: FAIL" in capsys.readouterr().out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_cmd_test_reports_fail_when_classify_severity_broken(monkeypatch, capsys):
    monkeypatch.setattr(tool, "classify_severity", lambda desc: "medium")
    rc = tool.cmd_test(_Args())
    assert rc == 1
    assert "SELF-TEST FAIL" in capsys.readouterr().out


# --- main(): required-arg enforcement ----------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_build_test_plan_requires_flows(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-test-plan"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_classify_severity_requires_description_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "classify-severity"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_format_bug_report_requires_title(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "format-bug-report", "--repro", "x", "--expected", "y", "--actual", "z"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_format_bug_report_requires_repro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "format-bug-report", "--title", "t", "--expected", "y", "--actual", "z"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_format_bug_report_requires_expected(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "format-bug-report", "--title", "t", "--repro", "x", "--actual", "z"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_format_bug_report_requires_actual(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "format-bug-report", "--title", "t", "--repro", "x", "--expected", "y"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_run_tests_requires_target_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-tests"])
    with pytest.raises(SystemExit):
        tool.main()


# --- main(): end-to-end dispatch ---------------------------------------------

def test_main_build_test_plan_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-test-plan", "--flows", "Auth login,Display avatar"])
    rc = tool.main()
    assert rc == 0
    assert "Auth login" in capsys.readouterr().out


def test_main_classify_severity_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "classify-severity", "typo in the footer"])
    rc = tool.main()
    assert rc == 0
    assert "low" in capsys.readouterr().out


def test_main_format_bug_report_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "format-bug-report", "--title", "X", "--repro", "a;b", "--expected", "y", "--actual", "z"])
    rc = tool.main()
    assert rc == 0
    assert '"repro_steps"' in capsys.readouterr().out


def test_main_run_tests_end_to_end(monkeypatch, capsys, tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_x():\n    assert True\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-tests", str(tmp_path)])
    rc = tool.main()
    assert rc == 0
    assert "QA GATE: PASS" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_script_runs_as_main_via_subprocess():
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run(
        [sys.executable, script, "classify-severity", "cosmetic typo"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "low" in result.stdout
