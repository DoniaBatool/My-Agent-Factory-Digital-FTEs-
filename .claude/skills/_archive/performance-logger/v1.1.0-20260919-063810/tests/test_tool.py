import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("performance_logger_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["performance_logger_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_redact_sensitive_masks_known_keys():
    fields = {"password": "hunter2", "user_id": "u1", "Authorization": "Bearer xyz"}
    redacted = tool.redact_sensitive(fields)
    assert redacted["password"] == "***REDACTED***"
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["user_id"] == "u1"


def test_format_log_line_includes_redacted_fields():
    line = tool.format_log_line("INFO", "login", password="secret", user_id="u1")
    assert "REDACTED" in line
    assert "secret" not in line
    assert "level=INFO" in line


def test_compute_duration_ms_basic():
    assert tool.compute_duration_ms(1.0, 1.5) == 500.0


def test_compute_duration_ms_rejects_negative():
    with pytest.raises(ValueError):
        tool.compute_duration_ms(2.0, 1.0)


def test_is_slow_threshold():
    assert tool.is_slow(300, threshold_ms=200) is True
    assert tool.is_slow(100, threshold_ms=200) is False


def test_aggregate_timings_basic():
    stats = tool.aggregate_timings([10, 20, 30, 40, 50])
    assert stats["count"] == 5
    assert stats["avg_ms"] == 30


def test_aggregate_timings_empty():
    stats = tool.aggregate_timings([])
    assert stats["count"] == 0


def test_rate_limited_logger_allows_up_to_max():
    state = {}
    results = [tool.rate_limited_logger(state, "k", 3, 10.0, now=1.0) for _ in range(3)]
    assert all(results)


def test_rate_limited_logger_blocks_beyond_max_within_window():
    state = {}
    for _ in range(3):
        tool.rate_limited_logger(state, "k", 3, 10.0, now=1.0)
    assert tool.rate_limited_logger(state, "k", 3, 10.0, now=1.5) is False


def test_rate_limited_logger_allows_again_after_window_passes():
    state = {}
    for _ in range(3):
        tool.rate_limited_logger(state, "k", 3, 10.0, now=1.0)
    assert tool.rate_limited_logger(state, "k", 3, 10.0, now=20.0) is True
