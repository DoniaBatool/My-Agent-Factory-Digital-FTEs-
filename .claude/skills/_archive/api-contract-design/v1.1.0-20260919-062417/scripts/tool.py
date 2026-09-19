#!/usr/bin/env python3
"""
API Contract Design Tool - real OpenAPI path building + contract validation

Commands: build-path-spec, validate-contract, check-breaking-change, test
"""
import argparse
import json
import sys

REQUIRED_RESPONSE_CODES_BY_METHOD = {
    "get": ["200"],
    "post": ["201"],
    "put": ["200"],
    "delete": ["204"],
}


def build_path_spec(method: str, path: str, summary: str, response_schema=None, error_codes=("401", "404", "422")):
    method = method.lower()
    responses = {}
    for code in REQUIRED_RESPONSE_CODES_BY_METHOD.get(method, ["200"]):
        responses[code] = {"description": "Success", "content": {"application/json": {"schema": response_schema or {}}}}
    for code in error_codes:
        responses[code] = {"description": _error_description(code)}
    return {path: {method: {"summary": summary, "responses": responses}}}


def _error_description(code: str) -> str:
    return {
        "400": "Bad Request", "401": "Unauthorized", "403": "Forbidden",
        "404": "Not Found", "422": "Validation Error", "500": "Internal Server Error",
    }.get(code, "Error")


def validate_contract(openapi_spec: dict):
    """Return list of violations: every path/method must declare a success
    response for its method (per REQUIRED_RESPONSE_CODES_BY_METHOD) and at
    least one 4xx error response."""
    violations = []
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, op in methods.items():
            responses = op.get("responses", {})
            required = REQUIRED_RESPONSE_CODES_BY_METHOD.get(method.lower(), ["200"])
            if not any(code in responses for code in required):
                violations.append(f"{method.upper()} {path}: missing success response ({required})")
            if not any(code.startswith("4") for code in responses):
                violations.append(f"{method.upper()} {path}: no 4xx error response documented")
    return violations


def check_breaking_change(old_spec: dict, new_spec: dict):
    """Very small, real breaking-change detector: a path+method present in
    old_spec but removed in new_spec is breaking; a required response code
    present in old but missing in new is breaking."""
    breaking = []
    old_paths = old_spec.get("paths", {})
    new_paths = new_spec.get("paths", {})
    for path, methods in old_paths.items():
        for method in methods:
            if path not in new_paths or method not in new_paths[path]:
                breaking.append(f"removed: {method.upper()} {path}")
            else:
                old_codes = set(methods[method].get("responses", {}))
                new_codes = set(new_paths[path][method].get("responses", {}))
                removed_codes = old_codes - new_codes
                if removed_codes:
                    breaking.append(f"{method.upper()} {path}: removed response codes {sorted(removed_codes)}")
    return breaking


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_build_path_spec(args):
    spec = build_path_spec(args.method, args.path, args.summary)
    print(json.dumps(spec, indent=2))
    return 0


def cmd_validate_contract(args):
    with open(args.spec_file) as f:
        spec = json.load(f)
    violations = validate_contract(spec)
    if not violations:
        print("OK: contract is complete")
        return 0
    for v in violations:
        print(f"  - {v}")
    return 1


def cmd_check_breaking_change(args):
    with open(args.old) as f:
        old_spec = json.load(f)
    with open(args.new) as f:
        new_spec = json.load(f)
    breaking = check_breaking_change(old_spec, new_spec)
    if not breaking:
        print("OK: no breaking changes detected")
        return 0
    for b in breaking:
        print(f"  - {b}")
    return 1


def cmd_test(args):
    spec = build_path_spec("get", "/tasks", "List tasks")
    ok = "200" in spec["/tasks"]["get"]["responses"]
    ok = ok and "404" in spec["/tasks"]["get"]["responses"]

    full_spec = {"paths": spec}
    ok = ok and validate_contract(full_spec) == []

    broken_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}
    ok = ok and len(validate_contract(broken_spec)) == 1  # missing 4xx

    old_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}, "404": {}}}}}}
    new_spec = {"paths": {}}
    ok = ok and check_breaking_change(old_spec, new_spec) == ["removed: GET /tasks"]
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="API Contract Design Tool")
    sub = parser.add_subparsers(dest="command")

    build_p = sub.add_parser("build-path-spec")
    build_p.add_argument("--method", required=True)
    build_p.add_argument("--path", required=True)
    build_p.add_argument("--summary", required=True)

    val_p = sub.add_parser("validate-contract")
    val_p.add_argument("spec_file")

    bc_p = sub.add_parser("check-breaking-change")
    bc_p.add_argument("--old", required=True)
    bc_p.add_argument("--new", required=True)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "build-path-spec": cmd_build_path_spec,
        "validate-contract": cmd_validate_contract,
        "check-breaking-change": cmd_check_breaking_change,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
