import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("pydantic_validation_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["pydantic_validation_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_coerce_value_passthrough_same_type():
    assert tool.coerce_value(5, int) == 5


def test_coerce_value_string_to_int():
    assert tool.coerce_value("42", int) == 42


def test_coerce_value_string_to_bool_true_variants():
    assert tool.coerce_value("yes", bool) is True
    assert tool.coerce_value("false", bool) is False


def test_coerce_value_raises_on_bad_input():
    with pytest.raises(ValueError):
        tool.coerce_value("not-a-number", int)


def test_validate_schema_requires_required_fields():
    schema = {"name": {"type": str, "required": True}}
    errors = tool.validate_schema({}, schema)
    assert any("required" in e for e in errors)


def test_validate_schema_type_check():
    schema = {"age": {"type": int}}
    errors = tool.validate_schema({"age": "not an int"}, schema)
    assert any("type" in e for e in errors)


def test_validate_schema_min_max_bounds():
    schema = {"age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"age": 200}, schema)
    assert any(">= 0" not in e for e in errors)
    assert any("<= 120" in e for e in errors)


def test_validate_schema_regex_check():
    schema = {"code": {"type": str, "regex": r"^[A-Z]{3}\d{3}$"}}
    errors = tool.validate_schema({"code": "abc"}, schema)
    assert any("pattern" in e for e in errors)


def test_validate_schema_accepts_valid_data():
    schema = {"name": {"type": str, "required": True}, "age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"name": "Ada", "age": 30}, schema)
    assert errors == []


def test_build_error_response_valid_flag():
    resp_ok = tool.build_error_response([])
    assert resp_ok["valid"] is True
    resp_bad = tool.build_error_response(["bad field"])
    assert resp_bad["valid"] is False
    assert resp_bad["detail"][0]["msg"] == "bad field"


def test_validate_email():
    assert tool.validate_email("a@b.com") is True
    assert tool.validate_email("not-an-email") is False
