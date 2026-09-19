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
