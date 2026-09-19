#!/usr/bin/env python3
"""
Change Management Tool - real change-spec scaffolding + impact scanning

Commands: create-change-spec, scan-impact, rollback-note, test
"""
import argparse
import json
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def next_change_number(changes_root: Path) -> int:
    if not changes_root.exists():
        return 1
    existing = [p.name for p in changes_root.iterdir() if p.is_dir()]
    nums = [int(m.group(1)) for name in existing if (m := re.match(r"(\d+)-", name))]
    return max(nums, default=0) + 1


def create_change_spec(changes_root: Path, feature: str, what: str, why: str, non_goals=None):
    changes_root.mkdir(parents=True, exist_ok=True)
    number = next_change_number(changes_root)
    folder = changes_root / f"{number:03d}-{slugify(feature)}"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "spec.md").write_text(
        f"# Change: {feature}\n\n## What\n{what}\n\n## Why\n{why}\n\n## Non-goals\n"
        + "\n".join(f"- {g}" for g in (non_goals or ["(none specified)"]))
        + "\n"
    )
    (folder / "plan.md").write_text(f"# Plan: {feature}\n\n## Impacted areas\n(fill in via scan-impact)\n")
    (folder / "tasks.md").write_text(f"# Tasks: {feature}\n\n- [ ] Implement change\n- [ ] Update tests\n- [ ] Update docs\n")
    return folder


def scan_impact(project_root: Path, search_term: str, extensions=(".py", ".ts", ".tsx", ".js", ".md")):
    """Real cross-file reference scan: which files under project_root
    mention search_term. Returns sorted list of relative paths."""
    hits = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix in extensions:
            try:
                if search_term in path.read_text(errors="ignore"):
                    hits.append(str(path.relative_to(project_root)))
            except OSError:
                continue
    return sorted(hits)


def build_rollback_note(change_name: str, migration_name=None, feature_flag=None):
    steps = []
    if feature_flag:
        steps.append(f"Disable feature flag '{feature_flag}'")
    if migration_name:
        steps.append(f"Run downgrade for migration '{migration_name}'")
    steps.append(f"Revert the commit(s) implementing '{change_name}'")
    return steps


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_create_change_spec(args):
    folder = create_change_spec(
        Path(args.changes_root), args.feature, args.what, args.why,
        args.non_goals.split(";") if args.non_goals else None,
    )
    print(f"Created {folder}")
    return 0


def cmd_scan_impact(args):
    hits = scan_impact(Path(args.project_root), args.term)
    if not hits:
        print(f"No references to '{args.term}' found")
        return 0
    for h in hits:
        print(f"  {h}")
    return 0


def cmd_rollback_note(args):
    steps = build_rollback_note(args.change_name, args.migration, args.feature_flag)
    print(json.dumps(steps, indent=2))
    return 0


def cmd_test(args):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        folder = create_change_spec(root / "changes", "Add priority field", "add a priority column", "users need to prioritize tasks")
        ok = folder.name.startswith("001-add-priority-field")
        ok = ok and (folder / "spec.md").exists()

        (root / "task.py").write_text("class Task:\n    priority: str\n")
        (root / "other.py").write_text("x = 1\n")
        hits = scan_impact(root, "priority")
        ok = ok and "task.py" in hits and "other.py" not in hits

        steps = build_rollback_note("add priority", migration_name="0012_add_priority")
        ok = ok and any("downgrade" in s for s in steps)
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Change Management Tool")
    sub = parser.add_subparsers(dest="command")

    spec_p = sub.add_parser("create-change-spec")
    spec_p.add_argument("--changes-root", default="changes")
    spec_p.add_argument("--feature", required=True)
    spec_p.add_argument("--what", required=True)
    spec_p.add_argument("--why", required=True)
    spec_p.add_argument("--non-goals", default=None, help="semicolon-separated")

    impact_p = sub.add_parser("scan-impact")
    impact_p.add_argument("--project-root", default=".")
    impact_p.add_argument("--term", required=True)

    rb_p = sub.add_parser("rollback-note")
    rb_p.add_argument("--change-name", required=True)
    rb_p.add_argument("--migration", default=None)
    rb_p.add_argument("--feature-flag", default=None)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "create-change-spec": cmd_create_change_spec,
        "scan-impact": cmd_scan_impact,
        "rollback-note": cmd_rollback_note,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
