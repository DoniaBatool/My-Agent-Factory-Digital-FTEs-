#!/usr/bin/env python3
"""
New Feature Tool - real spec/plan/tasks scaffolding + acceptance-criteria parsing

Commands: scaffold, parse-acceptance-criteria, test
"""
import argparse
import json
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_acceptance_criteria(description: str):
    """Extract bullet/numbered list items from a free-text description as
    acceptance criteria. Falls back to sentence-splitting if there are no
    list markers at all, so this never silently returns an empty list for
    a non-empty description."""
    lines = [l.strip() for l in description.splitlines() if l.strip()]
    bullets = [re.sub(r"^[-*\d.\)]+\s*", "", l) for l in lines if re.match(r"^[-*]\s|^\d+[.\)]\s", l)]
    if bullets:
        return bullets
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", description) if s.strip()]
    return sentences


def scaffold_feature(features_root: Path, name: str, description: str, acceptance_criteria=None):
    folder = features_root / slugify(name)
    folder.mkdir(parents=True, exist_ok=True)
    criteria = acceptance_criteria or parse_acceptance_criteria(description)

    (folder / "spec.md").write_text(
        f"# Spec: {name}\n\n## Description\n{description}\n\n## Acceptance Criteria\n"
        + "\n".join(f"- [ ] {c}" for c in criteria) + "\n"
    )
    (folder / "plan.md").write_text(f"# Plan: {name}\n\n## Architecture changes\n(TBD)\n\n## Rollout/rollback\n(TBD)\n")
    tasks = [f"Implement: {c}" for c in criteria] or ["Implement feature"]
    (folder / "tasks.md").write_text(
        f"# Tasks: {name}\n\n" + "\n".join(f"- [ ] {t}" for t in tasks) + "\n"
    )
    return folder


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_scaffold(args):
    folder = scaffold_feature(Path(args.features_root), args.name, args.description)
    print(f"Created {folder}")
    for f_ in sorted(folder.iterdir()):
        print(f"  {f_.name}")
    return 0


def cmd_parse_acceptance_criteria(args):
    criteria = parse_acceptance_criteria(args.description)
    print(json.dumps(criteria, indent=2))
    return 0


def cmd_test(args):
    import tempfile
    criteria = parse_acceptance_criteria("- User can log in\n- User sees an error on bad password\n")
    ok = criteria == ["User can log in", "User sees an error on bad password"]

    fallback = parse_acceptance_criteria("This is one sentence. This is another.")
    ok = ok and fallback == ["This is one sentence.", "This is another."]

    with tempfile.TemporaryDirectory() as tmp:
        folder = scaffold_feature(Path(tmp), "Todo Chatbot", "- Chat creates tasks\n- Tasks persist")
        ok = ok and (folder / "spec.md").exists() and (folder / "tasks.md").exists()
        ok = ok and "Chat creates tasks" in (folder / "spec.md").read_text()
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="New Feature Tool")
    sub = parser.add_subparsers(dest="command")

    scaffold_p = sub.add_parser("scaffold")
    scaffold_p.add_argument("--features-root", default="features")
    scaffold_p.add_argument("--name", required=True)
    scaffold_p.add_argument("--description", required=True)

    ac_p = sub.add_parser("parse-acceptance-criteria")
    ac_p.add_argument("description")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "scaffold": cmd_scaffold,
        "parse-acceptance-criteria": cmd_parse_acceptance_criteria,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
