#!/usr/bin/env python3
"""
Skill Version & Regression Gate
================================

Fixes a specific failure mode flagged in external code review (Sept 2026):
"Letting the agent rewrite both its instructions and its tests makes it
too easy to mistake a weaker test for an improvement."

Before this tool existed, `live-skill-learner` / `skill-learner` could edit
a skill's tool.py, its SKILL.md/README.md, AND its "test coverage" notes in
the same pass, with nothing independent checking whether the new version
was actually as good as the old one. Concretely this already happened once
in this repo: a 659-line grafana-expert tool.py with real multi-path
prerequisite checks was silently replaced by a 106-line version whose
"test" command prints "[Test 1/6]" but only ever runs test 1.

This module is the only sanctioned way to replace a skill's live files.
It intentionally lives outside any agent's prose instructions, as a
separately-testable program, so a weaker rewrite of an agent's
*instructions* cannot also weaken *this* gate.

Contract
--------
1. Tests live in `<skill>/tests/test_*.py` and are the regression baseline.
   A promotion may ADD test functions. It may never remove or rename an
   existing test function -- that is "the test suite shrank" and is
   rejected before pytest is even invoked.
2. A proposed change is prepared in a staging copy of the skill directory,
   never edited in place.
3. This gate runs the CURRENT live tests to get a baseline (the set of
   test ids), then runs the STAGED tests.
4. Promotion is allowed only if every baseline test id still exists in the
   staged suite AND still passes staged AND the staged pytest run exits 0.
5. On approval: the current live dir is archived under
   `_archive/<skill>/v<old-version>-<timestamp>/`, the staged dir becomes
   the new live dir, version.json is bumped, and CHANGELOG.md gets a dated
   entry naming exactly which baseline tests were verified.
6. On rejection: nothing about the live skill changes. A report is printed
   and appended to `_archive/<skill>/REJECTED.log` so a rejected attempt
   stays visible instead of silently vanishing.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent.parent  # .claude/skills


def _test_ids_defined(tests_dir: Path):
    """Statically list test function names across tests/test_*.py.

    Static (regex-over-source) rather than pytest-collection based, so a
    deleted test is caught even if the staged file fails to import.
    """
    ids = set()
    if not tests_dir.exists():
        return ids
    for f in sorted(tests_dir.glob("test_*.py")):
        for m in re.finditer(r"^def (test_\w+)", f.read_text(), re.MULTILINE):
            ids.add(f"{f.name}::{m.group(1)}")
    return ids


def _run_pytest(tests_dir: Path):
    """Run pytest against tests_dir. Returns (exit_code, passed_ids, failed_ids, raw_output)."""
    if not tests_dir.exists():
        return 1, set(), set(), f"no tests/ directory at {tests_dir}"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-v", "--tb=short"],
        capture_output=True, text=True, timeout=180,
    )
    passed, failed = set(), set()
    for line in proc.stdout.splitlines():
        m = re.match(r"(\S+\.py::\S+)\s+(PASSED|FAILED)", line)
        if m:
            test_id = f"{Path(m.group(1).split('::')[0]).name}::{m.group(1).split('::', 1)[1]}"
            (passed if m.group(2) == "PASSED" else failed).add(test_id)
    return proc.returncode, passed, failed, proc.stdout + proc.stderr


def read_version(skill_dir: Path):
    vf = skill_dir / "version.json"
    if vf.exists():
        return json.loads(vf.read_text())
    return {"version": "0.0.0", "history": []}


def write_version(skill_dir: Path, version_data):
    (skill_dir / "version.json").write_text(json.dumps(version_data, indent=2) + "\n")


def bump(version: str, part="patch"):
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _log_rejection(archive_root: Path, report: str):
    archive_root.mkdir(parents=True, exist_ok=True)
    with open(archive_root / "REJECTED.log", "a") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n{report}\n")


IGNORED_TOP_LEVEL = {"__pycache__", ".DS_Store", "CHANGELOG.md", "version.json"}


def _unexplained_missing_files(skill_dir: Path, staged_dir: Path):
    """Top-level files/dirs that exist live but vanished in the staged
    version, excluding files skill_gate.py itself manages. Catches the
    exact mistake this framework exists to prevent generalized to the
    staging step itself: e.g. hand-building a staged copy by cherry-picking
    SKILL.md + scripts/ and forgetting a pre-existing README.md/EXAMPLES.md."""
    if not skill_dir.exists():
        return []
    live_names = {p.name for p in skill_dir.iterdir()} - IGNORED_TOP_LEVEL
    staged_names = {p.name for p in staged_dir.iterdir()} - IGNORED_TOP_LEVEL if staged_dir.exists() else set()
    return sorted(live_names - staged_names)


def promote(skill_name: str, staged_dir: Path, bump_part="patch", reason="", allow_file_removal=False):
    skill_dir = SKILLS_ROOT / skill_name
    staged_dir = Path(staged_dir)
    archive_root = SKILLS_ROOT / "_archive" / skill_name

    missing_files = _unexplained_missing_files(skill_dir, staged_dir)
    if missing_files and not allow_file_removal:
        report = (
            f"REJECTED promotion of '{skill_name}': the staged version is missing "
            f"{len(missing_files)} file(s)/dir(s) that exist in the live skill: {missing_files}\n"
            f"If this staged copy was hand-built by cherry-picking files instead of "
            f"copying the whole live directory first, this is accidental content loss "
            f"(this happened once already: grafana-expert/README.md, "
            f"prometheus-monitoring/README.md, and prompt-analyzer/EXAMPLES.md were briefly "
            f"lost this way before this check existed). If the removal is deliberate, "
            f"re-run with allow_file_removal=True / --allow-file-removal."
        )
        _log_rejection(archive_root, report)
        print(report)
        return 1

    baseline_static = _test_ids_defined(skill_dir / "tests")
    staged_static = _test_ids_defined(staged_dir / "tests")
    missing = baseline_static - staged_static
    if missing:
        report = (
            f"REJECTED promotion of '{skill_name}': staged version deletes/renames "
            f"{len(missing)} existing test(s): {sorted(missing)}\n"
            f"A skill update must not shrink its own test suite."
        )
        _log_rejection(archive_root, report)
        print(report)
        return 1

    _, base_passed, _, _ = _run_pytest(skill_dir / "tests")
    staged_code, staged_passed, staged_failed, staged_out = _run_pytest(staged_dir / "tests")

    # Any baseline test that isn't verifiably passing staged is a regression,
    # whether it disappeared, errored, or now fails.
    regressed = baseline_static - staged_passed

    if staged_code != 0 or regressed:
        report = (
            f"REJECTED promotion of '{skill_name}':\n"
            f"  baseline tests: {len(baseline_static)} (previously passing: {len(base_passed)})\n"
            f"  staged pass: {len(staged_passed)}, staged fail: {len(staged_failed)}\n"
            f"  regressed (used to be a baseline test, not passing staged): {sorted(regressed) or 'none'}\n"
            f"  staged pytest exit code: {staged_code}\n"
            f"--- staged pytest output (tail) ---\n{staged_out[-4000:]}\n"
        )
        _log_rejection(archive_root, report)
        print(report)
        return 1

    version_data = read_version(skill_dir)
    old_version = version_data.get("version", "0.0.0")
    ts = time.strftime("%Y%m%d-%H%M%S")
    archive_root.mkdir(parents=True, exist_ok=True)
    if skill_dir.exists():
        shutil.copytree(skill_dir, archive_root / f"v{old_version}-{ts}", dirs_exist_ok=True)
    new_version = bump(old_version, bump_part)

    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    shutil.copytree(staged_dir, skill_dir)

    version_data["version"] = new_version
    version_data.setdefault("history", []).append({
        "version": new_version,
        "date": ts,
        "reason": reason or "promotion",
        "baseline_tests_verified": sorted(baseline_static),
        "new_tests_added": sorted(staged_static - baseline_static),
    })
    write_version(skill_dir, version_data)

    changelog = skill_dir / "CHANGELOG.md"
    entry = (
        f"\n## {new_version} - {ts}\n"
        f"{reason or 'Promoted via skill_gate.py'}\n"
        f"- Verified {len(baseline_static)} pre-existing test(s) still pass\n"
        f"- {len(staged_static) - len(baseline_static)} new test(s) added\n"
    )
    with open(changelog, "a") as f:
        f.write(entry)

    print(
        f"PROMOTED '{skill_name}': {old_version} -> {new_version}. "
        f"{len(baseline_static)} baseline test(s) verified, "
        f"{len(staged_static) - len(baseline_static)} new test(s) added. "
        f"Old version archived at {archive_root}/v{old_version}-{ts}"
    )
    return 0


def check(skill_name: str):
    skill_dir = SKILLS_ROOT / skill_name
    code, passed, failed, out = _run_pytest(skill_dir / "tests")
    print(out)
    print(f"passed={len(passed)} failed={len(failed)} exit={code}")
    return code


def main():
    p = argparse.ArgumentParser(description="Skill version & regression gate")
    sub = p.add_subparsers(dest="command", required=True)

    promote_p = sub.add_parser("promote")
    promote_p.add_argument("--skill", required=True)
    promote_p.add_argument("--staged-dir", required=True)
    promote_p.add_argument("--bump", choices=["major", "minor", "patch"], default="patch")
    promote_p.add_argument("--reason", default="")
    promote_p.add_argument("--allow-file-removal", action="store_true")

    check_p = sub.add_parser("check")
    check_p.add_argument("--skill", required=True)

    args = p.parse_args()
    if args.command == "promote":
        return promote(args.skill, Path(args.staged_dir), args.bump, args.reason, args.allow_file_removal)
    if args.command == "check":
        return check(args.skill)
    return 1


if __name__ == "__main__":
    sys.exit(main())
