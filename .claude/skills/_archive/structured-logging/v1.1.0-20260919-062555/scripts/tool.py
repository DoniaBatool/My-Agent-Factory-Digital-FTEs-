#!/usr/bin/env python3
"""
Structured Logging Tool - real JSON log building, correlation id, flattening and level-filter helpers.
"""
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key", "apikey"}


def redact_fields(fields: dict, sensitive_keys=None) -> dict:
    keys = sensitive_keys or _SENSITIVE_KEYS
    return {
        k: ("***REDACTED***" if any(s in k.lower() for s in keys) else v)
        for k, v in fields.items()
    }


def add_correlation_id(fields: dict, correlation_id: str = None) -> dict:
    out = dict(fields)
    out["correlation_id"] = correlation_id or str(uuid.uuid4())
    return out


def flatten_context(context: dict, prefix: str = "") -> dict:
    """Flatten a nested dict into dot-notation keys, e.g. {'user': {'id': 1}} -> {'user.id': 1}."""
    flat = {}
    for key, value in context.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_context(value, full_key))
        else:
            flat[full_key] = value
    return flat


def filter_log_level(configured_level: str, message_level: str) -> bool:
    """Return True if a message at message_level should be emitted given configured_level."""
    if configured_level not in _LEVELS or message_level not in _LEVELS:
        raise ValueError("unknown log level")
    return _LEVELS[message_level] >= _LEVELS[configured_level]


def to_json_log(level: str, message: str, **fields) -> str:
    if level not in _LEVELS:
        raise ValueError(f"unknown log level: {level}")
    safe_fields = redact_fields(flatten_context(fields))
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **safe_fields,
    }
    return json.dumps(record, sort_keys=True)


def parse_json_log(line: str) -> dict:
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not a valid JSON log line: {exc}") from exc


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Structured Logging Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
