#!/usr/bin/env python3
"""
Skill Learner Tool - real learning capture + skill-mapping + staging helper

Commands: capture-learning, find-skill-for-issue, stage-skill, test

This tool intentionally does NOT replace live skill files itself -- that
step is delegated to .claude/skills/_framework/skill_gate.py, which is the
only sanctioned promotion path (see skill-versioning-policy.md). This
tool's job is upstream of that: turn a fix into a structured learning
record and figure out which skill it belongs to.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent

# Same keyword-based approach as prompt-analyzer, applied to bug/issue text
# instead of feature-request text.
ISSUE_KEYWORD_TO_SKILL = {
    "migration": "database-schema-expander",
    "database": "database-engineer",
    "docker": "docker-expert",
    "kubernetes": "kubernetes-deployment",
    "deploy": "deployment-automation",
    "jwt": "jwt-authentication",
    "password": "password-security",
    "cross-user": "user-isolation",
    "idor": "user-isolation",
    "secret": "security-engineer",
    "grafana": "grafana-expert",
    "prometheus": "prometheus-monitoring",
    "test": "qa-engineer",
    "edge case": "edge-case-tester",
}


def find_skill_for_issue(issue_text: str):
    """Return the list of skills whose keyword appears in issue_text,
    longest keyword first (so 'edge case' beats a bare 'test' match)."""
    text = issue_text.lower()
    return [skill for kw, skill in sorted(ISSUE_KEYWORD_TO_SKILL.items(), key=lambda kv: -len(kv[0])) if kw in text]


def capture_learning(issue: str, root_cause: str, fix: str, edge_case: str = "", test_case: str = ""):
    return {
        "issue": issue,
        "root_cause": root_cause,
        "fix": fix,
        "edge_case": edge_case,
        "test_case": test_case,
        "captured_at": int(time.time()),
    }


def append_learning_log(log_path: Path, learning: dict):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if log_path.exists():
        entries = json.loads(log_path.read_text())
    entries.append(learning)
    log_path.write_text(json.dumps(entries, indent=2))
    return entries


def stage_skill(skill_name: str, skills_root: Path = None):
    """Copy the live skill directory to <skill>.staged/ so an update can be
    prepared without ever editing the live directory in place. Returns the
    staged path. Raises FileNotFoundError if the skill doesn't exist."""
    skills_root = skills_root or SKILLS_ROOT
    live_dir = skills_root / skill_name
    if not live_dir.exists():
        raise FileNotFoundError(f"no such skill: {skill_name}")
    staged_dir = skills_root / f"{skill_name}.staged"
    if staged_dir.exists():
        shutil.rmtree(staged_dir)
    shutil.copytree(live_dir, staged_dir)
    return staged_dir


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_capture_learning(args):
    learning = capture_learning(args.issue, args.root_cause, args.fix, args.edge_case or "", args.test_case or "")
    log_path = Path(args.log) if args.log else SKILLS_ROOT / "_framework" / "learning_log.json"
    append_learning_log(log_path, learning)
    print(json.dumps(learning, indent=2))
    return 0


def cmd_find_skill_for_issue(args):
    skills = find_skill_for_issue(args.issue)
    print(", ".join(skills) if skills else "(no matching skill found)")
    return 0 if skills else 1


def cmd_stage_skill(args):
    try:
        staged = stage_skill(args.skill)
    except FileNotFoundError as e:
        print(str(e))
        return 1
    print(f"Staged copy ready at {staged}")
    print(f"Next: edit {staged}, then run:")
    print(f"  python3 .claude/skills/_framework/skill_gate.py promote --skill {args.skill} --staged-dir {staged}")
    return 0


def cmd_test(args):
    import tempfile
    ok = find_skill_for_issue("JWT token expired but no refresh") == ["jwt-authentication"]
    ok = ok and "user-isolation" in find_skill_for_issue("cross-user data leak via IDOR")

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log.json"
        learning = capture_learning("issue", "cause", "fix")
        append_learning_log(log_path, learning)
        entries = json.loads(log_path.read_text())
        ok = ok and len(entries) == 1 and entries[0]["fix"] == "fix"

        skills_root = Path(tmp) / "skills"
        (skills_root / "demo-skill" / "scripts").mkdir(parents=True)
        (skills_root / "demo-skill" / "scripts" / "tool.py").write_text("# v1\n")
        staged = stage_skill("demo-skill", skills_root=skills_root)
        ok = ok and staged.exists() and (staged / "scripts" / "tool.py").read_text() == "# v1\n"

    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Skill Learner Tool")
    sub = parser.add_subparsers(dest="command")

    cap_p = sub.add_parser("capture-learning")
    cap_p.add_argument("--issue", required=True)
    cap_p.add_argument("--root-cause", required=True)
    cap_p.add_argument("--fix", required=True)
    cap_p.add_argument("--edge-case", default=None)
    cap_p.add_argument("--test-case", default=None)
    cap_p.add_argument("--log", default=None)

    find_p = sub.add_parser("find-skill-for-issue")
    find_p.add_argument("issue")

    stage_p = sub.add_parser("stage-skill")
    stage_p.add_argument("skill")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "capture-learning": cmd_capture_learning,
        "find-skill-for-issue": cmd_find_skill_for_issue,
        "stage-skill": cmd_stage_skill,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
