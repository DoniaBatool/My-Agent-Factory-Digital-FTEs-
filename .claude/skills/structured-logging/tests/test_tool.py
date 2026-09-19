import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("structured_logging_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["structured_logging_tool"] = tool
_spec.loader.exec_module(tool)

import pytest
import json


def test_redact_fields_masks_sensitive():
    out = tool.redact_fields({"token": "abc", "name": "x"})
    assert out["token"] == "***REDACTED***"
    assert out["name"] == "x"


def test_add_correlation_id_generates_when_missing():
    out = tool.add_correlation_id({"a": 1})
    assert "correlation_id" in out
    assert len(out["correlation_id"]) == 36


def test_add_correlation_id_preserves_given_id():
    out = tool.add_correlation_id({"a": 1}, correlation_id="fixed-id")
    assert out["correlation_id"] == "fixed-id"


def test_flatten_context_nested_dict():
    flat = tool.flatten_context({"user": {"id": 1, "profile": {"name": "Ada"}}})
    assert flat == {"user.id": 1, "user.profile.name": "Ada"}


def test_filter_log_level_allows_higher_or_equal():
    assert tool.filter_log_level("INFO", "ERROR") is True
    assert tool.filter_log_level("INFO", "INFO") is True


def test_filter_log_level_blocks_lower():
    assert tool.filter_log_level("WARNING", "DEBUG") is False


def test_filter_log_level_rejects_unknown_level():
    with pytest.raises(ValueError):
        tool.filter_log_level("INFO", "NOISY")


def test_to_json_log_produces_valid_json_with_redaction():
    line = tool.to_json_log("INFO", "user logged in", user_id="u1", password="secret")
    record = json.loads(line)
    assert record["level"] == "INFO"
    assert record["message"] == "user logged in"
    assert record["password"] == "***REDACTED***"


def test_to_json_log_rejects_unknown_level():
    with pytest.raises(ValueError):
        tool.to_json_log("VERBOSE", "hi")


def test_parse_json_log_round_trip():
    line = tool.to_json_log("ERROR", "boom", code=500)
    parsed = tool.parse_json_log(line)
    assert parsed["code"] == 500


def test_parse_json_log_rejects_garbage():
    with pytest.raises(ValueError):
        tool.parse_json_log("not json at all {")


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess as _subprocess_module
from pathlib import Path


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_redact_fields_case_insensitive_key_match():
    out = tool.redact_fields({"Token": "abc", "PASSWORD": "xyz"})
    assert out["Token"] == "***REDACTED***"
    assert out["PASSWORD"] == "***REDACTED***"


def test_redact_fields_substring_match_in_key():
    # "api_key_id" contains "api_key" so it should still be redacted
    out = tool.redact_fields({"api_key_id": "abc123"})
    assert out["api_key_id"] == "***REDACTED***"


def test_redact_fields_with_custom_sensitive_keys():
    out = tool.redact_fields({"ssn": "123-45-6789", "name": "Ada"}, sensitive_keys={"ssn"})
    assert out["ssn"] == "***REDACTED***"
    assert out["name"] == "Ada"


def test_redact_fields_no_matches_returns_values_unchanged():
    out = tool.redact_fields({"user_id": 42, "city": "NYC"})
    assert out == {"user_id": 42, "city": "NYC"}


def test_add_correlation_id_empty_string_treated_as_missing():
    out = tool.add_correlation_id({"a": 1}, correlation_id="")
    assert out["correlation_id"] != ""
    assert len(out["correlation_id"]) == 36


def test_flatten_context_empty_dict_returns_empty_dict():
    assert tool.flatten_context({}) == {}


def test_flatten_context_honors_prefix_argument():
    flat = tool.flatten_context({"a": 1}, prefix="pre")
    assert flat == {"pre.a": 1}


def test_filter_log_level_rejects_unknown_configured_level():
    with pytest.raises(ValueError):
        tool.filter_log_level("NOISY", "INFO")


def test_to_json_log_with_no_extra_fields():
    line = tool.to_json_log("DEBUG", "no fields here")
    record = json.loads(line)
    assert record["message"] == "no fields here"
    assert record["level"] == "DEBUG"
    assert set(record.keys()) == {"timestamp", "level", "message"}


def test_to_json_log_timestamp_is_iso_parseable():
    from datetime import datetime
    line = tool.to_json_log("INFO", "hi")
    record = json.loads(line)
    datetime.fromisoformat(record["timestamp"])  # raises if not valid ISO


def test_parse_json_log_accepts_non_dict_json():
    parsed = tool.parse_json_log("[1, 2, 3]")
    assert parsed == [1, 2, 3]


def test_print_success_outputs_checkmark_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_outputs_cross_and_message(capsys):
    tool.print_error("broken")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "broken" in out


def test_cmd_test_invokes_pytest_with_expected_args_and_returns_its_code(monkeypatch):
    captured = {}

    class _FakeCompletedProcess:
        returncode = 7

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return _FakeCompletedProcess()

    monkeypatch.setattr(_subprocess_module, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 7
    cmd = captured["cmd"]
    assert cmd[0] == sys.executable
    assert "-m" in cmd and "pytest" in cmd
    assert "--import-mode=importlib" in cmd
    assert cmd[-1] == "-q"
    expected_tests_dir = str(Path(tool.__file__).resolve().parent.parent / "tests")
    assert expected_tests_dir in cmd


def test_main_test_command_dispatches_via_func_and_exits_with_code(monkeypatch):
    class _FakeCompletedProcess:
        returncode = 3

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: _FakeCompletedProcess())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 3


def test_main_missing_command_is_required_and_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_no_args_hits_main_guard_and_exits_nonzero():
    script = Path(tool.__file__).resolve()
    result = _subprocess_module.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "command" in result.stderr.lower() or "required" in result.stderr.lower()


def test_to_json_log_output_has_deterministic_sorted_key_order():
    # sort_keys=True makes log lines diffable/greppable in a stable order;
    # verify the raw string, not just the parsed dict, reflects that.
    line = tool.to_json_log("INFO", "msg", zebra=1, apple=2)
    assert line.index('"apple"') < line.index('"zebra"')
    assert line.index('"level"') < line.index('"message"') < line.index('"timestamp"')
