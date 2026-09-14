#!/usr/bin/env python3
"""
MCP Tool Builder Tool - real input-schema validation + tool stub generation

Commands: validate-schema, generate-stub, test
"""
import argparse
import json
import re
import sys

VALID_JSON_SCHEMA_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}


def validate_tool_schema(schema: dict):
    """Every property in an MCP tool's input schema should have a 'type'
    and a 'description' -- ambiguous tool inputs are exactly what makes an
    AI agent call a tool incorrectly. Returns list of violations."""
    violations = []
    props = schema.get("properties", {})
    if not props:
        violations.append("schema has no 'properties' -- a tool with no declared inputs is only valid if it truly takes none")
    for name, prop in props.items():
        if "type" not in prop:
            violations.append(f"property '{name}' has no 'type'")
        elif prop["type"] not in VALID_JSON_SCHEMA_TYPES:
            violations.append(f"property '{name}' has invalid type '{prop['type']}'")
        if "description" not in prop:
            violations.append(f"property '{name}' has no 'description'")
    required = schema.get("required", [])
    for r in required:
        if r not in props:
            violations.append(f"'{r}' is in 'required' but not declared in 'properties'")
    return violations


def generate_tool_stub(tool_name: str, schema: dict, idempotent=True):
    """Generate a Python function stub matching the schema's properties,
    with a docstring reflecting whether it's idempotent (per this skill's
    'idempotent operations with database constraints' guidance)."""
    props = schema.get("properties", {})
    args = ", ".join(f"{name}: {_py_type(p.get('type', 'string'))}" for name, p in props.items())
    idempotency_note = "Idempotent: safe to call more than once with the same arguments." if idempotent else "NOT idempotent: calling twice creates two effects."
    return (
        f"def {tool_name}({args}):\n"
        f'    """{schema.get("description", tool_name)}\n\n    {idempotency_note}\n    """\n'
        f"    raise NotImplementedError\n"
    )


def _py_type(json_type: str) -> str:
    return {"string": "str", "number": "float", "integer": "int", "boolean": "bool", "array": "list", "object": "dict"}.get(json_type, "str")


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_validate_schema(args):
    schema = json.loads(args.schema)
    violations = validate_tool_schema(schema)
    if not violations:
        print("OK: schema is well-formed")
        return 0
    for v in violations:
        print(f"  - {v}")
    return 1


def cmd_generate_stub(args):
    schema = json.loads(args.schema)
    print(generate_tool_stub(args.name, schema, not args.not_idempotent))
    return 0


def cmd_test(args):
    good = {"properties": {"task_id": {"type": "string", "description": "the task id"}}, "required": ["task_id"]}
    ok = validate_tool_schema(good) == []

    bad = {"properties": {"task_id": {"type": "string"}}}
    violations = validate_tool_schema(bad)
    ok = ok and any("description" in v for v in violations)

    stub = generate_tool_stub("complete_task", good)
    ok = ok and "def complete_task(task_id: str):" in stub and "Idempotent" in stub
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="MCP Tool Builder Tool")
    sub = parser.add_subparsers(dest="command")

    val_p = sub.add_parser("validate-schema")
    val_p.add_argument("--schema", required=True, help="JSON schema")

    gen_p = sub.add_parser("generate-stub")
    gen_p.add_argument("--name", required=True)
    gen_p.add_argument("--schema", required=True, help="JSON schema")
    gen_p.add_argument("--not-idempotent", action="store_true")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "validate-schema": cmd_validate_schema,
        "generate-stub": cmd_generate_stub,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
