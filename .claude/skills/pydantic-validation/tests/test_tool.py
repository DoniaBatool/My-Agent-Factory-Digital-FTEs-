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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess as _subprocess


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- coerce_value edge cases -------------------------------------------------

def test_coerce_value_bool_passthrough_when_already_bool():
    assert tool.coerce_value(True, bool) is True


def test_coerce_value_bool_rejects_unrecognized_string():
    with pytest.raises(ValueError):
        tool.coerce_value("maybe", bool)


def test_coerce_value_bool_rejects_non_string_non_bool():
    # value is an int, not a str and not already a bool -- neither of the
    # string-matching branches applies, so it must fall through to the
    # explicit ValueError rather than silently succeeding.
    with pytest.raises(ValueError):
        tool.coerce_value(1, bool)


def test_coerce_value_string_to_float():
    assert tool.coerce_value("3.14", float) == 3.14


def test_coerce_value_type_error_is_wrapped_as_value_error():
    with pytest.raises(ValueError, match="cannot coerce"):
        tool.coerce_value(None, int)


# --- validate_schema boundary values -----------------------------------------

def test_validate_schema_min_boundary_exact_value_is_valid():
    schema = {"age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"age": 0}, schema)
    assert errors == []


def test_validate_schema_max_boundary_exact_value_is_valid():
    schema = {"age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"age": 120}, schema)
    assert errors == []


def test_validate_schema_one_below_min_is_invalid():
    schema = {"age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"age": -1}, schema)
    assert any(">= 0" in e for e in errors)


def test_validate_schema_one_above_max_is_invalid():
    schema = {"age": {"type": int, "min": 0, "max": 120}}
    errors = tool.validate_schema({"age": 121}, schema)
    assert any("<= 120" in e for e in errors)


def test_validate_schema_missing_optional_field_produces_no_error():
    schema = {"nickname": {"type": str, "required": False}}
    errors = tool.validate_schema({}, schema)
    assert errors == []


def test_validate_schema_explicit_none_on_required_field_is_an_error():
    schema = {"name": {"type": str, "required": True}}
    errors = tool.validate_schema({"name": None}, schema)
    assert any("required" in e for e in errors)


def test_validate_schema_explicit_none_on_optional_field_is_skipped():
    schema = {"nickname": {"type": str, "required": False}}
    errors = tool.validate_schema({"nickname": None}, schema)
    assert errors == []


def test_validate_schema_type_mismatch_skips_min_max_regex_without_crashing():
    # If type-checking didn't `continue`, comparing a str to an int min/max
    # would raise TypeError. It must not.
    schema = {"age": {"type": int, "min": 0, "max": 120, "regex": r"^\d+$"}}
    errors = tool.validate_schema({"age": "not an int"}, schema)
    assert len(errors) == 1
    assert "type" in errors[0]


def test_validate_schema_regex_rule_ignored_for_non_string_value():
    # regex should only apply when the value is a str; a matching type but
    # non-str value (e.g. an int field with a regex rule) must not attempt
    # re.match on it and must not raise or add a spurious error.
    schema = {"code": {"type": int, "regex": r"^[A-Z]{3}$"}}
    errors = tool.validate_schema({"code": 123}, schema)
    assert errors == []


def test_validate_schema_regex_valid_value_produces_no_error():
    schema = {"code": {"type": str, "regex": r"^[A-Z]{3}\d{3}$"}}
    errors = tool.validate_schema({"code": "ABC123"}, schema)
    assert errors == []


def test_validate_schema_required_defaults_to_false_when_omitted():
    schema = {"nickname": {"type": str}}
    errors = tool.validate_schema({}, schema)
    assert errors == []


# --- validate_email edge cases -----------------------------------------------

def test_validate_email_rejects_missing_at_sign():
    assert tool.validate_email("abcexample.com") is False


def test_validate_email_rejects_missing_tld():
    assert tool.validate_email("a@b") is False


def test_validate_email_rejects_embedded_whitespace():
    assert tool.validate_email("a b@example.com") is False


# --- build_error_response ------------------------------------------------

def test_build_error_response_multiple_errors_preserve_order():
    resp = tool.build_error_response(["first bad", "second bad"])
    assert [d["msg"] for d in resp["detail"]] == ["first bad", "second bad"]
    assert all(d["type"] == "value_error" for d in resp["detail"])


# --- CLI layer: cmd_test / main ----------------------------------------------

def test_cmd_test_invokes_pytest_with_expected_args(monkeypatch):
    captured = {}

    class FakeResult:
        returncode = 0

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(_subprocess, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "pytest" in captured["cmd"]
    assert "--import-mode=importlib" in captured["cmd"]
    assert "-q" in captured["cmd"]


def test_cmd_test_propagates_nonzero_pytest_exit_code(monkeypatch):
    class FakeResult:
        returncode = 1

    monkeypatch.setattr(_subprocess, "run", lambda cmd, *a, **kw: FakeResult())
    rc = tool.cmd_test(_Args())
    assert rc == 1


def test_main_no_command_exits_nonzero_because_subcommand_required(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code != 0


def test_main_dispatches_test_command_success(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    monkeypatch.setattr(tool, "cmd_test", lambda args: 0)
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0


def test_main_dispatches_test_command_failure(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    monkeypatch.setattr(tool, "cmd_test", lambda args: 1)
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1


def test_main_rejects_unknown_subcommand(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "bogus-command"])
    with pytest.raises(SystemExit):
        tool.main()


def test_script_runs_as_main_via_subprocess_missing_command_exits_nonzero():
    # Exercises the `if __name__ == "__main__":` guard for real without
    # triggering the "test" subcommand's own (recursive) pytest invocation:
    # omitting the required subcommand fails fast inside argparse.
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()


def test_print_success_and_print_error_format_output(capsys):
    tool.print_success("all good")
    tool.print_error("went wrong")
    out = capsys.readouterr().out
    assert "all good" in out
    assert "went wrong" in out
