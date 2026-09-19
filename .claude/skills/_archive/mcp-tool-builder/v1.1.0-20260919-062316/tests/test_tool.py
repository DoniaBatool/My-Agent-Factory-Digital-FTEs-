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
