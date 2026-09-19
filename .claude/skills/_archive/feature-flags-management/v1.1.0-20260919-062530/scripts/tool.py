#!/usr/bin/env python3
"""
Feature Flags Management Tool - real deterministic rollout + flag validation helpers.
"""
import argparse
import hashlib
import json
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def stable_bucket(user_id: str, salt: str) -> int:
    """Deterministically map (user_id, salt) to a stable bucket in [0, 100)."""
    digest = hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def validate_flag_config(config: dict) -> list:
    """Return a list of human-readable validation errors for a flag config (empty = valid)."""
    errors = []
    if not isinstance(config.get("global", True), bool):
        errors.append("'global' must be a boolean")
    pct = config.get("rollout_pct", 100)
    if not isinstance(pct, int) or not (0 <= pct <= 100):
        errors.append("'rollout_pct' must be an integer between 0 and 100")
    overrides = config.get("user_overrides", {})
    if not isinstance(overrides, dict):
        errors.append("'user_overrides' must be an object mapping user_id -> bool")
    return errors


def is_enabled(flag_config: dict, flag_name: str, user_id: str = None) -> bool:
    """Evaluate whether a flag is enabled for an (optional) user.

    Precedence: global off -> False; user override -> that value;
    otherwise a stable percentage rollout bucket.
    """
    errors = validate_flag_config(flag_config)
    if errors:
        raise ValueError(f"invalid flag config: {'; '.join(errors)}")

    if flag_config.get("global", True) is False:
        return False

    overrides = flag_config.get("user_overrides", {})
    if user_id is not None and user_id in overrides:
        return bool(overrides[user_id])

    rollout_pct = flag_config.get("rollout_pct", 100)
    if user_id is None:
        return rollout_pct >= 100
    return stable_bucket(user_id, flag_name) < rollout_pct


def merge_flag_configs(base: dict, override: dict) -> dict:
    """Shallow-merge two flag configs, with override winning per top-level key,
    except user_overrides dicts are merged together."""
    merged = dict(base)
    for key, value in override.items():
        if key == "user_overrides" and isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


_DEFAULT_STAGES = (1, 5, 25, 50, 100)


def next_rollout_stage(current_pct: int, stages=_DEFAULT_STAGES) -> int:
    """Return the next rollout percentage stage strictly greater than current_pct."""
    for stage in stages:
        if stage > current_pct:
            return stage
    return 100


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Feature Flags Management Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
