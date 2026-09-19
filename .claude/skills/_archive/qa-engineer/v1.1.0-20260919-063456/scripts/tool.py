#!/usr/bin/env python3
"""
QA Engineer Tool - real risk-based planning, bug reports, and test execution

Commands: build-test-plan, classify-severity, format-bug-report, run-tests, test

This is the skill README.md names as the enforcer of "Agents do not mark a
feature complete until tests pass" -- its previous `test` command was a
TODO stub that always printed success regardless of anything, which made
that README claim false. `run-tests` here genuinely shells out to pytest.
"""
import argparse
import json
import re
import subprocess
import sys

SEVERITY_RULES = [
    ("critical", [r"data loss", r"security breach", r"cannot log ?in", r"corrupt"]),
    ("high", [r"crash", r"500 error", r"blocked", r"feature broken"]),
    ("medium", [r"edge case", r"workaround", r"intermittent"]),
    ("low", [r"cosmetic", r"typo", r"rare"]),
]

RISK_KEYWORDS = {
    "auth": "high",
    "payment": "high",
    "user isolation": "high",
    "data integrity": "high",
    "ui": "medium",
    "display": "low",
}


def classify_severity(description: str) -> str:
    desc = description.lower()
    for severity, patterns in SEVERITY_RULES:
        if any(re.search(p, desc) for p in patterns):
            return severity
    return "medium"  # default: never silently "low" an unclassified bug


def build_test_plan(critical_flows):
    """critical_flows: list of flow name strings. Returns a risk-annotated
    plan: each flow gets a risk level from RISK_KEYWORDS (substring match),
    defaulting to 'medium' for anything not recognized."""
    plan = []
    for flow in critical_flows:
        flow_lower = flow.lower()
        risk = next((lvl for kw, lvl in RISK_KEYWORDS.items() if kw in flow_lower), "medium")
        plan.append({"flow": flow, "risk": risk})
    return sorted(plan, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["risk"]])


def format_bug_report(title, repro_steps, expected, actual, environment="unspecified"):
    severity = classify_severity(f"{title} {actual}")
    return {
        "title": title,
        "severity": severity,
        "repro_steps": repro_steps,
        "expected": expected,
        "actual": actual,
        "environment": environment,
    }


def run_pytest_suite(target_dir: str, timeout=300):
    """Genuinely invoke pytest against target_dir. Returns (exit_code, output)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", target_dir, "-v"],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_build_test_plan(args):
    flows = args.flows.split(",")
    plan = build_test_plan(flows)
    print(json.dumps(plan, indent=2))
    return 0


def cmd_classify_severity(args):
    print(classify_severity(args.description))
    return 0


def cmd_format_bug_report(args):
    report = format_bug_report(args.title, args.repro.split(";"), args.expected, args.actual, args.environment)
    print(json.dumps(report, indent=2))
    return 0


def cmd_run_tests(args):
    code, output = run_pytest_suite(args.target)
    print(output)
    if code == 0:
        print("QA GATE: PASS")
    else:
        print("QA GATE: FAIL - feature may not be marked complete")
    return code


def cmd_test(args):
    ok = classify_severity("This causes data loss on save") == "critical"
    ok = ok and classify_severity("Minor cosmetic misalignment") == "low"
    plan = build_test_plan(["Auth login", "Display avatar"])
    ok = ok and plan[0]["risk"] == "high" and plan[0]["flow"] == "Auth login"
    report = format_bug_report("Crash on save", ["open app", "click save"], "saves", "crashes")
    ok = ok and report["severity"] == "high"
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="QA Engineer Tool")
    sub = parser.add_subparsers(dest="command")

    plan_p = sub.add_parser("build-test-plan")
    plan_p.add_argument("--flows", required=True, help="comma-separated critical flow names")

    sev_p = sub.add_parser("classify-severity")
    sev_p.add_argument("description")

    bug_p = sub.add_parser("format-bug-report")
    bug_p.add_argument("--title", required=True)
    bug_p.add_argument("--repro", required=True, help="semicolon-separated repro steps")
    bug_p.add_argument("--expected", required=True)
    bug_p.add_argument("--actual", required=True)
    bug_p.add_argument("--environment", default="unspecified")

    run_p = sub.add_parser("run-tests")
    run_p.add_argument("target")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "build-test-plan": cmd_build_test_plan,
        "classify-severity": cmd_classify_severity,
        "format-bug-report": cmd_format_bug_report,
        "run-tests": cmd_run_tests,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
