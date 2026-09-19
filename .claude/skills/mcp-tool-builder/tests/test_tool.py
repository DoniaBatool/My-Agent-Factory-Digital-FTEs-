import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("mcp_tool_builder_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_validate_tool_schema_passes_well_formed_schema():
    schema = {"properties": {"task_id": {"type": "string", "description": "the task id"}}, "required": ["task_id"]}
    assert tool.validate_tool_schema(schema) == []


def test_validate_tool_schema_flags_missing_description():
    schema = {"properties": {"task_id": {"type": "string"}}}
    violations = tool.validate_tool_schema(schema)
    assert any("description" in v for v in violations)


def test_validate_tool_schema_flags_missing_type():
    schema = {"properties": {"task_id": {"description": "x"}}}
    violations = tool.validate_tool_schema(schema)
    assert any("no 'type'" in v for v in violations)


def test_validate_tool_schema_flags_invalid_type():
    schema = {"properties": {"task_id": {"type": "bogus", "description": "x"}}}
    violations = tool.validate_tool_schema(schema)
    assert any("invalid type" in v for v in violations)


def test_validate_tool_schema_flags_required_field_not_declared():
    schema = {"properties": {}, "required": ["task_id"]}
    violations = tool.validate_tool_schema(schema)
    assert any("task_id" in v and "required" in v for v in violations)


def test_generate_tool_stub_produces_typed_signature():
    schema = {"properties": {"task_id": {"type": "string", "description": "x"}, "count": {"type": "integer", "description": "y"}}}
    stub = tool.generate_tool_stub("do_thing", schema)
    assert "def do_thing(task_id: str, count: int):" in stub


def test_generate_tool_stub_notes_non_idempotency_when_specified():
    schema = {"properties": {}}
    stub = tool.generate_tool_stub("do_thing", schema, idempotent=False)
    assert "NOT idempotent" in stub


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys as _sys
import pytest


def test_validate_tool_schema_flags_no_properties():
    violations = tool.validate_tool_schema({})
    assert any("no 'properties'" in v for v in violations)


def test_py_type_defaults_to_str_for_unknown_json_type():
    assert tool._py_type("bogus-type") == "str"


def test_py_type_maps_all_known_json_schema_types():
    assert tool._py_type("number") == "float"
    assert tool._py_type("boolean") == "bool"
    assert tool._py_type("array") == "list"
    assert tool._py_type("object") == "dict"


def test_generate_tool_stub_uses_tool_name_when_no_description():
    schema = {"properties": {}}
    stub = tool.generate_tool_stub("nameless", schema)
    assert '"""nameless' in stub


def test_generate_tool_stub_uses_schema_description_when_present():
    schema = {"properties": {}, "description": "Does the thing."}
    stub = tool.generate_tool_stub("do_thing", schema)
    assert "Does the thing." in stub


def test_generate_tool_stub_defaults_to_idempotent_true():
    # generate_tool_stub's idempotent default (True) is exercised only via the
    # 2-arg call form -- this is distinct from the explicit idempotent=False test.
    schema = {"properties": {}}
    stub = tool.generate_tool_stub("do_thing", schema)
    assert "Idempotent: safe to call more than once" in stub


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_cmd_validate_schema_prints_ok_and_returns_0_for_well_formed_schema(capsys):
    args = _Args(schema=json.dumps({"properties": {"x": {"type": "string", "description": "d"}}}))
    rc = tool.cmd_validate_schema(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK: schema is well-formed" in out


def test_cmd_validate_schema_prints_violations_and_returns_1_for_bad_schema(capsys):
    args = _Args(schema=json.dumps({"properties": {"x": {"type": "string"}}}))
    rc = tool.cmd_validate_schema(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "description" in out


def test_cmd_generate_stub_idempotent_by_default(capsys):
    args = _Args(name="foo", schema=json.dumps({"properties": {}}), not_idempotent=False)
    rc = tool.cmd_generate_stub(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "def foo():" in out
    assert "Idempotent: safe" in out


def test_cmd_generate_stub_not_idempotent_flag(capsys):
    args = _Args(name="foo", schema=json.dumps({"properties": {}}), not_idempotent=True)
    rc = tool.cmd_generate_stub(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "NOT idempotent" in out


def test_cmd_test_self_test_passes(capsys):
    args = _Args()
    rc = tool.cmd_test(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_validate_schema_end_to_end(monkeypatch, capsys):
    schema = json.dumps({"properties": {"x": {"type": "string", "description": "d"}}})
    monkeypatch.setattr(_sys, "argv", ["tool.py", "validate-schema", "--schema", schema])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_main_generate_stub_end_to_end(monkeypatch, capsys):
    schema = json.dumps({"properties": {"a": {"type": "integer", "description": "d"}}})
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-stub", "--name", "make_it", "--schema", schema])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "def make_it(a: int):" in out


def test_main_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_validate_schema_missing_required_schema_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "validate-schema"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_generate_stub_missing_required_name_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-stub", "--schema", "{}"])
    with pytest.raises(SystemExit):
        tool.main()


def test_cli_subprocess_smoke_test_runs_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    schema = json.dumps({"properties": {"x": {"type": "string", "description": "d"}}})
    proc = subprocess.run(
        [_sys.executable, str(script), "validate-schema", "--schema", schema],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_cli_subprocess_smoke_test_bad_schema_exits_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    schema = json.dumps({"properties": {"x": {"type": "string"}}})
    proc = subprocess.run(
        [_sys.executable, str(script), "validate-schema", "--schema", schema],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 1
    assert "description" in proc.stdout
