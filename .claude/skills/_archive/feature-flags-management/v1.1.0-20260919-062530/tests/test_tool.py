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
