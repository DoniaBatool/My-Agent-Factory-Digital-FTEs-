#!/usr/bin/env python3
"""
Production Checklist Tool - real go-live checks against a project directory

Commands: run-checklist, test
"""
import argparse
import json
import re
import sys
from pathlib import Path

SECRET_LIKE = re.compile(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"]{6,}['\"]")


def check_env_gitignored(project_root: Path):
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return False, "no .gitignore found"
    text = gitignore.read_text()
    if ".env" in text or "*.env" in text:
        return True, ".env is git-ignored"
    return False, ".env is not listed in .gitignore"


def check_no_hardcoded_secrets(project_root: Path, extensions=(".py", ".ts", ".js")):
    offenders = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix in extensions and "test" not in path.name.lower():
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if SECRET_LIKE.search(text):
                offenders.append(str(path.relative_to(project_root)))
    return len(offenders) == 0, offenders


def check_tests_exist(project_root: Path):
    candidates = [project_root / "tests", project_root / "test"]
    found = any(p.exists() and any(p.rglob("test_*.py")) for p in candidates)
    return found, "tests/ directory with test_*.py files" if found else "no tests/ directory with test files found"


def check_health_endpoint(project_root: Path):
    for path in project_root.rglob("*.py"):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if re.search(r"(?i)['\"]\/?health['\"]", text):
            return True, str(path)
    return False, "no /health route found"


def run_checklist(project_root: Path):
    project_root = Path(project_root)
    results = {}
    ok, detail = check_env_gitignored(project_root)
    results["env_gitignored"] = {"pass": ok, "detail": detail}
    ok, offenders = check_no_hardcoded_secrets(project_root)
    results["no_hardcoded_secrets"] = {"pass": ok, "detail": offenders or "none found"}
    ok, detail = check_tests_exist(project_root)
    results["tests_exist"] = {"pass": ok, "detail": detail}
    ok, detail = check_health_endpoint(project_root)
    results["health_endpoint"] = {"pass": ok, "detail": detail}
    return results


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_run_checklist(args):
    results = run_checklist(Path(args.project_root))
    print(json.dumps(results, indent=2))
    all_pass = all(r["pass"] for r in results.values())
    print("GO-LIVE: READY" if all_pass else "GO-LIVE: NOT READY")
    return 0 if all_pass else 1


def cmd_test(args):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".gitignore").write_text(".env\n")
        (root / "app.py").write_text("password = 'hunter2'\n")
        (root / "tests").mkdir()
        (root / "tests" / "test_app.py").write_text("def test_x(): assert True\n")
        results = run_checklist(root)
        ok = results["env_gitignored"]["pass"] is True
        ok = ok and results["no_hardcoded_secrets"]["pass"] is False
        ok = ok and results["tests_exist"]["pass"] is True
        ok = ok and results["health_endpoint"]["pass"] is False
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Production Checklist Tool")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run-checklist")
    run_p.add_argument("project_root")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {"run-checklist": cmd_run_checklist, "test": cmd_test}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
