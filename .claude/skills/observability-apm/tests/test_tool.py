import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("observability_apm_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["observability_apm_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_parse_trace_span_computes_duration():
    span = {"trace_id": "t1", "span_id": "s1", "name": "fetch", "start_time": 1.0, "end_time": 1.25}
    parsed = tool.parse_trace_span(span)
    assert parsed["duration_ms"] == 250.0


def test_parse_trace_span_rejects_missing_fields():
    with pytest.raises(ValueError):
        tool.parse_trace_span({"trace_id": "t1"})


def test_parse_trace_span_rejects_negative_duration():
    with pytest.raises(ValueError):
        tool.parse_trace_span({"trace_id": "t1", "span_id": "s1", "name": "x", "start_time": 2.0, "end_time": 1.0})


def test_build_span_tree_nests_children_under_parent():
    spans = [
        {"span_id": "root", "parent_id": None},
        {"span_id": "child1", "parent_id": "root"},
        {"span_id": "child2", "parent_id": "root"},
        {"span_id": "grandchild", "parent_id": "child1"},
    ]
    tree = tool.build_span_tree(spans)
    assert len(tree["roots"]) == 1
    root = tree["roots"][0]
    assert len(root["children"]) == 2
    child1 = next(c for c in root["children"] if c["span_id"] == "child1")
    assert child1["children"][0]["span_id"] == "grandchild"


def test_detect_slow_spans_filters_and_sorts_desc():
    spans = [
        {"trace_id": "t", "span_id": "a", "name": "a", "start_time": 0, "end_time": 0.1},
        {"trace_id": "t", "span_id": "b", "name": "b", "start_time": 0, "end_time": 1.0},
        {"trace_id": "t", "span_id": "c", "name": "c", "start_time": 0, "end_time": 0.6},
    ]
    slow = tool.detect_slow_spans(spans, threshold_ms=500)
    assert [s["span_id"] for s in slow] == ["b", "c"]


def test_aggregate_metrics_basic_stats():
    stats = tool.aggregate_metrics([10, 20, 30, 40, 50])
    assert stats["min"] == 10
    assert stats["max"] == 50
    assert stats["avg"] == 30
    assert stats["p50"] == 30


def test_aggregate_metrics_empty_list():
    stats = tool.aggregate_metrics([])
    assert stats["count"] == 0


def test_check_error_rate_flags_alert_above_threshold():
    result = tool.check_error_rate(100, 10, threshold=0.05)
    assert result["rate"] == 0.1
    assert result["alert"] is True


def test_check_error_rate_no_alert_below_threshold():
    result = tool.check_error_rate(1000, 5, threshold=0.05)
    assert result["alert"] is False


def test_check_error_rate_rejects_errors_exceeding_total():
    with pytest.raises(ValueError):
        tool.check_error_rate(5, 10)


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import sys as _sys


def test_print_success_includes_checkmark_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_includes_cross_and_message(capsys):
    tool.print_error("broke")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "broke" in out


def test_parse_trace_span_zero_duration_is_allowed_not_negative():
    span = {"trace_id": "t1", "span_id": "s1", "name": "x", "start_time": 5.0, "end_time": 5.0}
    parsed = tool.parse_trace_span(span)
    assert parsed["duration_ms"] == 0.0


def test_build_span_tree_empty_list_yields_no_roots():
    assert tool.build_span_tree([]) == {"roots": []}


def test_build_span_tree_missing_parent_id_key_treated_as_root():
    # a span with no "parent_id" key at all -- span.get("parent_id") defaults
    # to None, same bucket as an explicit parent_id=None root.
    spans = [{"span_id": "orphan"}]
    tree = tool.build_span_tree(spans)
    assert len(tree["roots"]) == 1
    assert tree["roots"][0]["span_id"] == "orphan"
    assert tree["roots"][0]["children"] == []


def test_detect_slow_spans_excludes_span_exactly_at_threshold():
    spans = [{"trace_id": "t", "span_id": "a", "name": "a", "start_time": 0, "end_time": 0.5}]
    slow = tool.detect_slow_spans(spans, threshold_ms=500)
    assert slow == []  # strictly greater-than, not >=


def test_detect_slow_spans_skips_reparsing_spans_with_precomputed_duration():
    # a span that already has duration_ms is used as-is, so it need not
    # have the required raw fields (trace_id/span_id/name/start_time/end_time)
    spans = [{"duration_ms": 999.0}]
    slow = tool.detect_slow_spans(spans, threshold_ms=500)
    assert slow == [{"duration_ms": 999.0}]


def test_percentile_exact_integer_rank_no_interpolation():
    assert tool._percentile([10, 20, 30], 50) == 20


def test_percentile_empty_list_returns_zero():
    assert tool._percentile([], 90) == 0.0


def test_percentile_single_value_returns_that_value():
    assert tool._percentile([42], 99) == 42


def test_aggregate_metrics_single_sample():
    stats = tool.aggregate_metrics([7])
    assert stats["count"] == 1
    assert stats["min"] == stats["max"] == stats["avg"] == 7
    assert stats["p50"] == stats["p95"] == stats["p99"] == 7


def test_check_error_rate_zero_total_has_zero_rate_no_alert():
    result = tool.check_error_rate(0, 0)
    assert result["rate"] == 0.0
    assert result["alert"] is False


def test_check_error_rate_exactly_at_threshold_is_not_an_alert():
    result = tool.check_error_rate(100, 5, threshold=0.05)
    assert result["rate"] == 0.05
    assert result["alert"] is False  # strictly greater-than, not >=


def test_check_error_rate_rejects_negative_total():
    with pytest.raises(ValueError):
        tool.check_error_rate(-1, 0)


def test_check_error_rate_rejects_negative_errors():
    with pytest.raises(ValueError):
        tool.check_error_rate(10, -1)


def test_cmd_test_invokes_pytest_subprocess_with_expected_args(monkeypatch):
    calls = []

    class _FakeCompleted:
        returncode = 3

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted()

    import subprocess as _subprocess_mod
    monkeypatch.setattr(_subprocess_mod, "run", fake_run)
    rc = tool.cmd_test(None)
    assert rc == 3
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[0] == _sys.executable
    assert "pytest" in cmd
    assert "--import-mode=importlib" in cmd
    assert "-q" in cmd
    assert str(Path(__file__).resolve().parent) in cmd[-2] or cmd[-2].endswith("tests")


def test_main_test_subcommand_dispatches_to_cmd_test_and_exits_with_its_code(monkeypatch):
    monkeypatch.setattr(tool, "cmd_test", lambda args: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 0


def test_main_test_subcommand_propagates_nonzero_exit_code(monkeypatch):
    monkeypatch.setattr(tool, "cmd_test", lambda args: 1)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 1


def test_main_missing_required_command_exits_nonzero(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code != 0
