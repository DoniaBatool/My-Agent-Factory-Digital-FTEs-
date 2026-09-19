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
