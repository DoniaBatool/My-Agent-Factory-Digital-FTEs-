import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("feature_flags_management_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["feature_flags_management_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_stable_bucket_is_deterministic():
    a = tool.stable_bucket("user-1", "flag-a")
    b = tool.stable_bucket("user-1", "flag-a")
    assert a == b
    assert 0 <= a < 100


def test_stable_bucket_distributes_across_users():
    buckets = {tool.stable_bucket(f"user-{i}", "flag-a") for i in range(200)}
    assert len(buckets) > 50


def test_validate_flag_config_accepts_valid():
    assert tool.validate_flag_config({"global": True, "rollout_pct": 50}) == []


def test_validate_flag_config_rejects_out_of_range_pct():
    errors = tool.validate_flag_config({"rollout_pct": 150})
    assert any("rollout_pct" in e for e in errors)


def test_is_enabled_false_when_global_off():
    config = {"global": False, "rollout_pct": 100}
    assert tool.is_enabled(config, "flag-a", "user-1") is False


def test_is_enabled_respects_user_override_true_even_at_zero_rollout():
    config = {"global": True, "rollout_pct": 0, "user_overrides": {"user-1": True}}
    assert tool.is_enabled(config, "flag-a", "user-1") is True


def test_is_enabled_respects_user_override_false_even_at_full_rollout():
    config = {"global": True, "rollout_pct": 100, "user_overrides": {"user-1": False}}
    assert tool.is_enabled(config, "flag-a", "user-1") is False


def test_is_enabled_full_rollout_enables_everyone():
    config = {"global": True, "rollout_pct": 100}
    for i in range(50):
        assert tool.is_enabled(config, "flag-a", f"user-{i}") is True


def test_is_enabled_raises_on_invalid_config():
    with pytest.raises(ValueError):
        tool.is_enabled({"rollout_pct": 999}, "flag-a", "user-1")


def test_merge_flag_configs_merges_user_overrides():
    base = {"global": True, "rollout_pct": 10, "user_overrides": {"u1": True}}
    override = {"rollout_pct": 50, "user_overrides": {"u2": False}}
    merged = tool.merge_flag_configs(base, override)
    assert merged["rollout_pct"] == 50
    assert merged["user_overrides"] == {"u1": True, "u2": False}


def test_next_rollout_stage_progression():
    assert tool.next_rollout_stage(0) == 1
    assert tool.next_rollout_stage(1) == 5
    assert tool.next_rollout_stage(99) == 100
    assert tool.next_rollout_stage(100) == 100

# --- edge cases + CLI layer (added for bulletproofing pass) ---
# NOTE: cmd_test() invokes `python3 -m pytest` on this very tests/ directory as a
# real subprocess. Calling it for real from inside this suite would recurse
# (this suite would re-run itself, which would call cmd_test again, ...), so every
# test below that touches cmd_test/main()'s "test" dispatch mocks subprocess.run.
# The one real-subprocess smoke test instead runs the script with NO command,
# which argparse rejects before cmd_test is ever reached -- that safely exercises
# the `if __name__ == "__main__": main()` line without any recursion risk.
import hashlib
import subprocess


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_stable_bucket_matches_reference_hash_formula():
    digest = hashlib.sha256("flag-x:user-42".encode("utf-8")).hexdigest()
    expected = int(digest[:8], 16) % 100
    assert tool.stable_bucket("user-42", "flag-x") == expected


def test_stable_bucket_reference_formula_second_pair():
    digest = hashlib.sha256("other-flag:another-user".encode("utf-8")).hexdigest()
    expected = int(digest[:8], 16) % 100
    assert tool.stable_bucket("another-user", "other-flag") == expected


def test_print_success_and_print_error_include_message(capsys):
    tool.print_success("all good")
    tool.print_error("uh oh")
    out = capsys.readouterr().out
    assert "all good" in out
    assert "uh oh" in out
    assert "✓" in out  # check mark
    assert "✗" in out  # cross mark


def test_validate_flag_config_rejects_non_bool_global():
    errors = tool.validate_flag_config({"global": "yes"})
    assert any("global" in e for e in errors)


def test_validate_flag_config_rejects_non_dict_user_overrides():
    errors = tool.validate_flag_config({"user_overrides": ["not", "a", "dict"]})
    assert any("user_overrides" in e for e in errors)


def test_validate_flag_config_collects_multiple_errors_at_once():
    errors = tool.validate_flag_config({"global": "nope", "rollout_pct": -5, "user_overrides": 3})
    assert len(errors) == 3


def test_is_enabled_boundary_bucket_exactly_at_threshold_is_disabled():
    user_id, flag_name = "boundary-user", "boundary-flag"
    bucket = tool.stable_bucket(user_id, flag_name)
    config = {"global": True, "rollout_pct": bucket}
    assert tool.is_enabled(config, flag_name, user_id) is False


def test_is_enabled_boundary_bucket_one_above_threshold_is_enabled():
    user_id, flag_name = "boundary-user", "boundary-flag"
    bucket = tool.stable_bucket(user_id, flag_name)
    config = {"global": True, "rollout_pct": bucket + 1}
    assert tool.is_enabled(config, flag_name, user_id) is True


def test_is_enabled_no_user_id_partial_rollout_returns_false():
    config = {"global": True, "rollout_pct": 50}
    assert tool.is_enabled(config, "flag-a", None) is False


def test_is_enabled_no_user_id_full_rollout_returns_true():
    config = {"global": True, "rollout_pct": 100}
    assert tool.is_enabled(config, "flag-a", None) is True


def test_merge_flag_configs_override_wins_when_base_lacks_dict_value():
    base = {"global": True, "rollout_pct": 10}
    override = {"user_overrides": {"u1": True}}
    merged = tool.merge_flag_configs(base, override)
    assert merged["user_overrides"] == {"u1": True}


def test_next_rollout_stage_custom_stages_returns_first_greater():
    assert tool.next_rollout_stage(2, stages=(1, 5, 10)) == 5


def test_next_rollout_stage_custom_stages_falls_back_to_100_when_none_greater():
    assert tool.next_rollout_stage(50, stages=(1, 5, 10)) == 100


def test_cmd_test_invokes_pytest_on_tests_dir_and_returns_its_code(monkeypatch):
    calls = {}

    class FakeResult:
        returncode = 3

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 3
    cmd = calls["cmd"]
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "pytest"]
    assert "--import-mode=importlib" in cmd
    assert cmd[-1] == "-q"
    expected_tests_dir = str(_MODULE_PATH.parent.parent / "tests")
    assert expected_tests_dir in cmd


def test_main_dispatches_test_command_and_exits_with_its_code(monkeypatch):
    class FakeResult:
        returncode = 0

    def fake_run(cmd, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0


def test_main_dispatches_test_command_nonzero_exit_code(monkeypatch):
    class FakeResult:
        returncode = 1

    def fake_run(cmd, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1


def test_main_missing_command_raises_systemexit_2(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 2


def test_subprocess_runs_as_script_with_no_command_and_exits_2():
    result = subprocess.run(
        [sys.executable, str(_MODULE_PATH)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "usage" in (result.stderr + result.stdout).lower()


def test_is_enabled_defaults_global_to_true_when_key_absent():
    # "global" is optional in a flag config; when omitted it must default to
    # True (globally on) rather than silently disabling the flag.
    config = {"rollout_pct": 100}
    assert tool.is_enabled(config, "flag-a", None) is True
