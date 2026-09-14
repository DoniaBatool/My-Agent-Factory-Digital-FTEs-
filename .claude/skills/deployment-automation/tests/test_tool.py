import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("deployment_automation_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_check_env_vars_flags_missing():
    missing = tool.check_env_vars(["A", "B"], {"A": "x"})
    assert missing == ["B"]


def test_check_env_vars_flags_empty_string_as_missing():
    missing = tool.check_env_vars(["A"], {"A": ""})
    assert missing == ["A"]


def test_check_env_vars_ok_when_all_present():
    assert tool.check_env_vars(["A", "B"], {"A": "1", "B": "2"}) == []


def test_check_env_vars_never_leaks_values_in_result():
    missing = tool.check_env_vars(["SECRET_KEY"], {})
    assert missing == ["SECRET_KEY"]  # only the name, never a value


def test_build_rollback_plan_always_includes_redeploy_step():
    steps = tool.build_rollback_plan("v1.0.0")
    assert any("v1.0.0" in s for s in steps)


def test_build_rollback_plan_includes_migration_and_flag_when_given():
    steps = tool.build_rollback_plan("v1.0.0", migration_name="0005_x", feature_flag="new_thing")
    assert any("0005_x" in s for s in steps)
    assert any("new_thing" in s for s in steps)


def test_run_smoke_check_reports_failure_for_unreachable_host():
    ok, detail = tool.run_smoke_check("http://localhost:1/definitely-not-running", timeout=2)
    assert ok is False
