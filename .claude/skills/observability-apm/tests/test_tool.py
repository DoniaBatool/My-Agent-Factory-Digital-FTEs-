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
