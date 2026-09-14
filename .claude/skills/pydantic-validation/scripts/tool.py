#!/usr/bin/env python3
"""
Pydantic Validation Tool - real stdlib-only schema validation helpers
(works whether or not pydantic itself is installed in the target project).
"""
import argparse
import json
import re
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def coerce_value(value, target_type):
    """Attempt to coerce value to target_type, raising ValueError on failure."""
    if isinstance(value, target_type):
        return value
    try:
        if target_type is bool:
            if isinstance(value, str):
                if value.lower() in ("true", "1", "yes"):
                    return True
                if value.lower() in ("false", "0", "no"):
                    return False
            raise ValueError(f"cannot coerce {value!r} to bool")
        return target_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"cannot coerce {value!r} to {target_type.__name__}") from exc


def validate_schema(data: dict, schema: dict) -> list:
    """Validate `data` against a simple field schema.

    schema: {field: {"type": type, "required": bool, "min": num, "max": num, "regex": str}}
    Returns a list of error strings (empty list = valid).
    """
    errors = []
    for field, rules in schema.items():
        required = rules.get("required", False)
        if field not in data or data[field] is None:
            if required:
                errors.append(f"'{field}' is required")
            continue

        value = data[field]
        expected_type = rules.get("type")
        if expected_type is not None and not isinstance(value, expected_type):
            errors.append(f"'{field}' must be of type {expected_type.__name__}")
            continue

        if "min" in rules and value < rules["min"]:
            errors.append(f"'{field}' must be >= {rules['min']}")
        if "max" in rules and value > rules["max"]:
            errors.append(f"'{field}' must be <= {rules['max']}")
        if "regex" in rules and isinstance(value, str) and not re.match(rules["regex"], value):
            errors.append(f"'{field}' does not match required pattern")

    return errors


def build_error_response(errors: list) -> dict:
    """Build a FastAPI/pydantic-style 422 error envelope from a list of error strings."""
    return {
        "detail": [{"msg": e, "type": "value_error"} for e in errors],
        "valid": len(errors) == 0,
    }


EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def validate_email(value: str) -> bool:
    return bool(re.match(EMAIL_REGEX, value))


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Pydantic Validation Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
