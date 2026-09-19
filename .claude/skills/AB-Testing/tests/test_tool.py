import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("ab_testing_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_assign_variant_is_deterministic_for_same_user():
    v1 = tool.assign_variant("user-1", "test-a", {"control": 0.5, "variant_a": 0.5})
    v2 = tool.assign_variant("user-1", "test-a", {"control": 0.5, "variant_a": 0.5})
    assert v1 == v2


def test_assign_variant_distributes_across_variants_for_many_users():
    counts = {}
    for i in range(2000):
        v = tool.assign_variant(f"user-{i}", "test-a", {"control": 0.5, "variant_a": 0.5})
        counts[v] = counts.get(v, 0) + 1
    assert 800 < counts.get("control", 0) < 1200
    assert 800 < counts.get("variant_a", 0) < 1200


def test_assign_variant_rejects_split_not_summing_to_one():
    try:
        tool.assign_variant("u", "t", {"control": 0.6, "variant_a": 0.6})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_check_significance_detects_clear_lift():
    result = tool.check_significance(100, 1000, 150, 1000)
    assert result["significant"] is True


def test_check_significance_rejects_noise_level_difference():
    result = tool.check_significance(100, 1000, 105, 1000)
    assert result["significant"] is False


def test_check_significance_reports_conversion_rates():
    result = tool.check_significance(50, 500, 60, 500)
    assert result["p_control"] == 0.1
    assert result["p_variant"] == 0.12


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys
from types import SimpleNamespace
import pytest


def test_assign_variant_rejects_empty_split():
    with pytest.raises(ValueError):
        tool.assign_variant("u", "t", {})


def test_assign_variant_accepts_split_within_floating_tolerance():
    # sum is 1.0 + 5e-7, inside the 1e-6 tolerance -> must be accepted
    result = tool.assign_variant("u1", "t1", {"control": 0.5, "variant_a": 0.5 + 5e-7})
    assert result in ("control", "variant_a")


def test_assign_variant_rejects_split_outside_floating_tolerance():
    # sum is 1.0 + 2e-6, outside the 1e-6 tolerance -> must be rejected
    with pytest.raises(ValueError):
        tool.assign_variant("u1", "t1", {"control": 0.5, "variant_a": 0.5 + 2e-6})


def test_assign_variant_single_variant_split_always_returns_it():
    for i in range(20):
        result = tool.assign_variant(f"user-{i}", "only-test", {"only": 1.0})
        assert result == "only"


def test_check_significance_zero_pool_conversions_returns_zero_z_and_not_significant():
    # both groups have zero conversions -> p_pool is 0, se is 0, so the
    # `if se > 0 else 0.0` branch must fire and report z_score == 0.0.
    result = tool.check_significance(0, 100, 0, 100)
    assert result["z_score"] == 0.0
    assert result["significant"] is False


def test_check_significance_negative_z_beyond_threshold_is_significant():
    # variant performs worse than control by a wide margin -> z is negative,
    # but abs(z) >= threshold must still mark it significant.
    result = tool.check_significance(150, 1000, 100, 1000)
    assert result["z_score"] < 0
    assert result["significant"] is True


def test_check_significance_negative_small_difference_not_significant():
    result = tool.check_significance(105, 1000, 100, 1000)
    assert result["significant"] is False


def test_check_significance_boundary_exact_threshold_is_significant():
    # Recompute the exact same raw (unrounded) z the implementation would
    # compute, then use it verbatim as the threshold: an exact tie must
    # still count as significant since the comparison is `>=`, not `>`.
    control_conversions, control_total = 100, 1000
    variant_conversions, variant_total = 150, 1000
    p_control = control_conversions / control_total
    p_variant = variant_conversions / variant_total
    p_pool = (control_conversions + variant_conversions) / (control_total + variant_total)
    se = (p_pool * (1 - p_pool) * (1 / control_total + 1 / variant_total)) ** 0.5
    z = (p_variant - p_control) / se
    result = tool.check_significance(
        control_conversions, control_total, variant_conversions, variant_total, z_threshold=abs(z)
    )
    assert result["significant"] is True


def test_check_significance_zero_total_raises_zero_division():
    with pytest.raises(ZeroDivisionError):
        tool.check_significance(0, 0, 10, 100)


def test_cmd_assign_variant_prints_variant(capsys):
    args = SimpleNamespace(user_id="u1", test_name="t1", split='{"control": 0.5, "variant_a": 0.5}')
    rc = tool.cmd_assign_variant(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out in ("control", "variant_a")


def test_cmd_assign_variant_malformed_json_raises():
    args = SimpleNamespace(user_id="u1", test_name="t1", split="not-json")
    with pytest.raises(json.JSONDecodeError):
        tool.cmd_assign_variant(args)


def test_cmd_check_significance_prints_json(capsys):
    args = SimpleNamespace(control_conversions=100, control_total=1000, variant_conversions=150, variant_total=1000)
    rc = tool.cmd_check_significance(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["significant"] is True


def test_cmd_test_returns_zero_and_prints_pass(capsys):
    rc = tool.cmd_test(SimpleNamespace())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_dispatches_assign_variant_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "assign-variant", "--user-id", "u1", "--test-name", "t1", "--split", '{"only": 1.0}'],
    )
    rc = tool.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "only"


def test_main_dispatches_check_significance_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        [
            "tool.py", "check-significance",
            "--control-conversions", "100", "--control-total", "1000",
            "--variant-conversions", "150", "--variant-total", "1000",
        ],
    )
    rc = tool.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["significant"] is True


def test_main_dispatches_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage" in captured.out.lower()


def test_main_assign_variant_missing_required_split_exits(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "assign-variant", "--user-id", "u1", "--test-name", "t1"],
    )
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_significance_missing_required_total_exits(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        [
            "tool.py", "check-significance",
            "--control-conversions", "100",
            "--variant-conversions", "150", "--variant-total", "1000",
        ],
    )
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    from pathlib import Path as _Path
    script = _Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([sys.executable, str(script), "test"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "SELF-TEST PASS" in proc.stdout


def test_assign_variant_returns_second_variant_when_bucket_exceeds_first_share():
    import hashlib as _hashlib
    user_id, test_name = "boundary-user", "boundary-test"
    digest = _hashlib.sha256(f"{test_name}:{user_id}".encode()).hexdigest()
    bucket = (int(digest, 16) % 10000) / 10000.0
    # Place the boundary just below the real bucket value so the correct
    # implementation (bucket < cumulative) must land in "second" -- an
    # inverted comparison (e.g. >=) would instead wrongly return "first".
    first_share = bucket - 0.0001
    second_share = 1.0 - first_share
    result = tool.assign_variant(user_id, test_name, {"first": first_share, "second": second_share})
    assert result == "second"


def test_main_assign_variant_missing_required_user_id_exits(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "assign-variant", "--test-name", "t1", "--split", '{"only": 1.0}'],
    )
    with pytest.raises(SystemExit):
        tool.main()


def test_main_assign_variant_missing_required_test_name_exits(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "assign-variant", "--user-id", "u1", "--split", '{"only": 1.0}'],
    )
    with pytest.raises(SystemExit):
        tool.main()
