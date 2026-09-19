#!/usr/bin/env python3
"""
Deployment Automation Tool - real env-var validation + smoke checks + rollback plan

Commands: check-env-vars, smoke-check, rollback-plan, test
"""
import argparse
import json
import subprocess
import sys


def check_env_vars(required, actual: dict):
    """Return list of required env vars missing or empty in `actual`.
    Never returns the VALUE of any var, only names, so secrets are never
    printed even by accident."""
    return [name for name in required if not actual.get(name)]


def build_rollback_plan(previous_version: str, migration_name=None, feature_flag=None):
    steps = [f"Redeploy previous version: {previous_version}"]
    if migration_name:
        steps.append(f"Run migration downgrade: alembic downgrade -1  # {migration_name}")
    if feature_flag:
        steps.append(f"Disable feature flag: {feature_flag}")
    return steps


def run_smoke_check(url: str, timeout=10):
    """Real HTTP check via curl. Returns (ok, http_code_or_error)."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)
    code = proc.stdout.strip()
    return code == "200", code


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_check_env_vars(args):
    import os
    required = args.required.split(",")
    missing = check_env_vars(required, dict(os.environ))
    if not missing:
        print("OK: all required env vars present")
        return 0
    print("MISSING: " + ", ".join(missing))
    return 1


def cmd_smoke_check(args):
    ok, detail = run_smoke_check(args.url, timeout=args.timeout)
    print(f"{'OK' if ok else 'FAIL'}: {detail}")
    return 0 if ok else 1


def cmd_rollback_plan(args):
    steps = build_rollback_plan(args.previous_version, args.migration, args.feature_flag)
    print(json.dumps(steps, indent=2))
    return 0


def cmd_test(args):
    missing = check_env_vars(["DATABASE_URL", "SECRET_KEY"], {"DATABASE_URL": "postgres://x"})
    ok = missing == ["SECRET_KEY"]
    steps = build_rollback_plan("v1.2.3", migration_name="0012_add_priority")
    ok = ok and any("v1.2.3" in s for s in steps) and any("downgrade" in s for s in steps)
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Deployment Automation Tool")
    sub = parser.add_subparsers(dest="command")

    env_p = sub.add_parser("check-env-vars")
    env_p.add_argument("--required", required=True, help="comma-separated var names")

    smoke_p = sub.add_parser("smoke-check")
    smoke_p.add_argument("--url", required=True)
    smoke_p.add_argument("--timeout", type=int, default=10)

    rb_p = sub.add_parser("rollback-plan")
    rb_p.add_argument("--previous-version", required=True)
    rb_p.add_argument("--migration", default=None)
    rb_p.add_argument("--feature-flag", default=None)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "check-env-vars": cmd_check_env_vars,
        "smoke-check": cmd_smoke_check,
        "rollback-plan": cmd_rollback_plan,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
