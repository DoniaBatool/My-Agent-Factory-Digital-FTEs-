#!/usr/bin/env python3
"""
CI / pre-commit enforcement for the skill versioning gate.

This script enforces two separate things:

1. EXISTING skills never bypass the gate. Whenever a commit/PR touches an
   existing skill's scripts/ or tests/, that same change must ALSO bump that
   skill's version.json. If it doesn't, the commit is almost certainly a
   direct edit that skipped skill_gate.py promote.

2. BRAND NEW skills are strong enough on day one (the "onboarding gate").
   skill_gate.py promote only protects a skill that already has a baseline --
   it has no opinion on how good a new skill's first version is. This script
   detects a skill's first-ever commit (version.json newly added, not
   modified) and runs new_skill_gate.py's full check (required files, test
   count, coverage, mutation score) against it. A new skill that doesn't
   clear that bar is blocked, with a full score report explaining why --
   the same report prints on a pass, so there's always a visible answer to
   "how strong is this skill and why did it pass/fail", not just an exit code.

Usage:
  As a pre-commit hook (checks staged files):
      python3 .claude/skills/_framework/ci_gate_check.py --staged

  In CI (checks all files changed vs. a base ref, e.g. origin/main):
      python3 .claude/skills/_framework/ci_gate_check.py --base origin/main

Exit code 0 = OK, 1 = blocked (message explains which skill and why, for
either failure mode above).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(_THIS_DIR))
import new_skill_gate  # noqa: E402

SKILL_PATH_RE = re.compile(r"^\.claude/skills/([^/_][^/]*)/(scripts|tests)/")
VERSION_PATH_RE = re.compile(r"^\.claude/skills/([^/_][^/]*)/version\.json$")


def _changed_files_with_status(staged: bool, base: str | None):
    """Returns a list of (status_letter, path) tuples, e.g. [('A', '...'), ('M', '...')]."""
    if staged:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-status"], capture_output=True, text=True, check=True
        ).stdout
    else:
        out = subprocess.run(
            ["git", "diff", "--name-status", f"{base}...HEAD"], capture_output=True, text=True, check=True
        ).stdout
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append((parts[0][0], parts[-1]))  # first char handles rename codes like R100
    return rows


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true", help="Check staged files (pre-commit).")
    g.add_argument("--base", help="Check files changed vs. this ref (CI), e.g. origin/main.")
    args = p.parse_args()

    rows = _changed_files_with_status(args.staged, args.base)

    touched_skills = set()
    version_bumped_skills = set()
    newly_added_skills = set()  # version.json status == Added -> brand-new skill

    for status, path in rows:
        m = SKILL_PATH_RE.match(path)
        if m:
            touched_skills.add(m.group(1))
        vm = VERSION_PATH_RE.match(path)
        if vm:
            version_bumped_skills.add(vm.group(1))
            if status == "A":
                newly_added_skills.add(vm.group(1))

    ok = True

    # --- Check 1: existing skills never bypass the gate --------------------
    existing_touched = touched_skills - newly_added_skills
    violations = existing_touched - version_bumped_skills
    if violations:
        ok = False
        print(
            "BLOCKED: the following skill(s) had scripts/ or tests/ changed without their "
            "version.json also changing in this commit/PR:\n"
            + "\n".join(f"  - {s}" for s in sorted(violations))
            + "\n\nThis almost always means a skill's live files were hand-edited instead of "
            "going through the versioning gate. Stage your change in a full copy of the skill "
            "directory (`<skill>.staged/`) and promote it with:\n"
            "  python3 .claude/skills/_framework/skill_gate.py promote --skill <skill> "
            "--staged-dir <skill>.staged --bump <major|minor|patch> --reason \"...\"\n"
            "See .claude/CLAUDE.md 'Skill Versioning & Regression Gate' for the full contract.\n",
            file=sys.stderr,
        )

    # --- Check 2: brand-new skills must clear the onboarding gate ----------
    for skill_name in sorted(newly_added_skills):
        skill_dir = Path(".claude/skills") / skill_name
        report = new_skill_gate.run_new_skill_checks(skill_dir, skill_name)
        print(f"--- New-skill onboarding check: {skill_name} ---")
        print(new_skill_gate.format_report(report))
        if not report["passed"]:
            ok = False

    if not ok:
        return 1

    print(
        f"OK: {len(existing_touched)} existing skill(s) went through version.json bumps; "
        f"{len(newly_added_skills)} new skill(s) cleared the onboarding gate."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
