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


def test_redact_sensitive_leaves_non_string_values_untouched_when_not_sensitive():
    fields = {"count": 42, "ratio": 0.5}
    redacted = tool.redact_sensitive(fields)
    assert redacted == {"count": 42, "ratio": 0.5}


def test_redact_sensitive_matches_substring_not_just_exact_key():
    # "api_key" is a sensitive key but so is any key merely CONTAINING one --
    # this proves it's substring matching, e.g. "user_api_key" or "my_token".
    fields = {"user_api_key": "abc", "my_token_value": "xyz", "plain": "ok"}
    redacted = tool.redact_sensitive(fields)
    assert redacted["user_api_key"] == "***REDACTED***"
    assert redacted["my_token_value"] == "***REDACTED***"
    assert redacted["plain"] == "ok"


def test_format_log_line_sorts_fields_alphabetically_regardless_of_call_order():
    line = tool.format_log_line("INFO", "msg", zeta="z", alpha="a", mid="m")
    alpha_pos = line.index("alpha=")
    mid_pos = line.index("mid=")
    zeta_pos = line.index("zeta=")
    assert alpha_pos < mid_pos < zeta_pos


def test_format_log_line_with_no_extra_fields():
    line = tool.format_log_line("DEBUG", "hello")
    assert line == "level=DEBUG message='hello'"


def test_compute_duration_ms_zero_duration_allowed_not_negative():
    assert tool.compute_duration_ms(3.0, 3.0) == 0.0


def test_is_slow_exactly_at_threshold_is_not_slow():
    assert tool.is_slow(200, threshold_ms=200) is False  # strictly greater-than, not >=


def test_percentile_exact_integer_rank_no_interpolation():
    assert tool._percentile([10, 20, 30], 50) == 20


def test_percentile_empty_list_returns_zero():
    assert tool._percentile([], 90) == 0.0


def test_aggregate_timings_single_sample():
    stats = tool.aggregate_timings([15])
    assert stats["count"] == 1
    assert stats["avg_ms"] == 15
    assert stats["p95_ms"] == stats["p99_ms"] == 15


def test_rate_limited_logger_item_exactly_at_cutoff_is_excluded():
    # bucket keeps entries with t > cutoff (strict); an entry timestamped
    # exactly at now-window_seconds must be dropped, freeing a slot.
    state = {"k": [5.0]}  # logged at t=5.0
    # window_seconds=5, now=10.0 -> cutoff=5.0 -> the t=5.0 entry is NOT > cutoff, dropped
    allowed = tool.rate_limited_logger(state, "k", max_per_window=1, window_seconds=5.0, now=10.0)
    assert allowed is True
    assert state["k"] == [10.0]


def test_rate_limited_logger_max_zero_always_blocks():
    state = {}
    assert tool.rate_limited_logger(state, "k", max_per_window=0, window_seconds=10.0, now=1.0) is False
    assert state["k"] == []


def test_rate_limited_logger_different_keys_are_independent():
    state = {}
    for _ in range(2):
        tool.rate_limited_logger(state, "a", max_per_window=2, window_seconds=10.0, now=1.0)
    # "a" bucket is full (2/2); "b" is a fresh independent bucket and should still be allowed
    assert tool.rate_limited_logger(state, "a", max_per_window=2, window_seconds=10.0, now=1.0) is False
    assert tool.rate_limited_logger(state, "b", max_per_window=2, window_seconds=10.0, now=1.0) is True


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
    assert cmd[-2].endswith("tests")


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
