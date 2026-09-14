#!/usr/bin/env python3
"""
GraphQL API Tool - real SDL generation + N+1 risk detection

Commands: build-sdl, check-n-plus-one, test
"""
import argparse
import re
import sys


def build_type_sdl(type_name: str, fields: dict) -> str:
    """fields: {field_name: graphql_type_string}. Returns SDL 'type X { ... }'."""
    lines = [f"type {type_name} {{"]
    for name, gql_type in fields.items():
        lines.append(f"  {name}: {gql_type}")
    lines.append("}")
    return "\n".join(lines)


def build_schema_sdl(types: dict, query_fields: dict):
    """types: {type_name: {field: gql_type}}. query_fields: {field: gql_type}."""
    parts = [build_type_sdl(name, fields) for name, fields in types.items()]
    parts.append(build_type_sdl("Query", query_fields))
    return "\n\n".join(parts) + "\n"


def check_n_plus_one_risk(resolver_source: str):
    """Heuristic: a resolver that returns a list AND contains a query call
    inside a loop (for ... : ... query/get/fetch) is a classic N+1 risk.
    Real pattern match, not a hand-wave -- looks for a for-loop whose body
    calls something ending in _service.get/query/fetch."""
    findings = []
    for m in re.finditer(r"for\s+\w+\s+in\s+[\w.]+:\n((?:[ \t]+.*\n?)+)", resolver_source):
        body = m.group(1)
        if re.search(r"\.(get|query|fetch)\w*\(", body):
            findings.append("possible N+1: a database/service call happens inside a for-loop")
    return findings


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_build_sdl(args):
    import json
    types = json.loads(args.types)
    query_fields = json.loads(args.query_fields)
    print(build_schema_sdl(types, query_fields))
    return 0


def cmd_check_n_plus_one(args):
    with open(args.path) as f:
        source = f.read()
    findings = check_n_plus_one_risk(source)
    if not findings:
        print("OK: no obvious N+1 patterns found")
        return 0
    for f_ in findings:
        print(f"  - {f_}")
    return 1


def cmd_test(args):
    sdl = build_schema_sdl({"Task": {"id": "ID!", "title": "String!"}}, {"tasks": "[Task!]!"})
    ok = "type Task {" in sdl and "id: ID!" in sdl and "type Query {" in sdl

    risky = "def resolve_tasks(root):\n    result = []\n    for uid in user_ids:\n        result.append(user_service.get(uid))\n    return result\n"
    ok = ok and len(check_n_plus_one_risk(risky)) == 1

    safe = "def resolve_tasks(root):\n    return task_service.get_all(user_ids)\n"
    ok = ok and check_n_plus_one_risk(safe) == []
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="GraphQL API Tool")
    sub = parser.add_subparsers(dest="command")

    sdl_p = sub.add_parser("build-sdl")
    sdl_p.add_argument("--types", required=True, help='JSON {"TypeName": {"field": "GqlType"}}')
    sdl_p.add_argument("--query-fields", required=True, help='JSON {"field": "GqlType"}')

    n1_p = sub.add_parser("check-n-plus-one")
    n1_p.add_argument("path")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "build-sdl": cmd_build_sdl,
        "check-n-plus-one": cmd_check_n_plus_one,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
