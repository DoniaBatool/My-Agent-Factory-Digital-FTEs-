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

Guardrails added 2026-09-16 (closing the "same test name, weaker assertion"
gap identified after the above fix shipped -- the original gate checked
test IDENTITY (name) and pass/fail, never test CONTENT):

7. Test-body hashing: every baseline test function's exact source is
   hashed. A promotion where an EXISTING test's hash changed is rejected
   unless explicitly acknowledged with a reason (--acknowledge-test-change
   + --change-reason). This makes "keep the name, gut the assertions"
   impossible to do silently -- it must now be a deliberate, logged action.
8. Coverage-never-shrinks: line coverage of scripts/tool.py by the test
   suite is measured and stored. A promotion may not lower it without
   --allow-coverage-drop. (Best-effort: if the `coverage` package isn't
   available, this check is skipped rather than blocking the whole gate.)
9. Golden-file protection (security-critical skills only -- see
   SECURITY_CRITICAL_SKILLS below): the skill's whole tests/test_tool.py
   is hash-locked in golden.json. ANY change, even a legitimate-looking
   one, is rejected unless --acknowledge-golden-change is passed alongside
   --change-reason.
10. Mutation testing (security-critical skills only): a lightweight,
    AST-based mutator flips comparison operators and boolean literals in
    scripts/tool.py, one at a time, and re-runs the test suite against
    each mutant. The fraction of mutants that cause a test failure ("kill
    score") is stored and may not drop without --allow-mutation-drop. This
    is a practical subset of mutation testing (comparisons + booleans),
    not an exhaustive mutation-testing suite -- it exists to catch tests
    that pass but no longer actually exercise the logic they claim to.

Honesty note: even with all of this, a sufficiently determined rewrite
that changes an assertion's *value* while preserving its *shape* (e.g.
`assert result == 42` -> `assert result == 43` where 43 also happens to be
what the new, wrong implementation returns) is not detected by any static
or count-based check. Mutation testing (#10) is the strongest defense
against that, which is why it's mandatory for security-critical skills.
For everything else, the test-body-hash acknowledgment trail (#7) plus the
"show the diff before pushing" human-review step remain the backstop.
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent.parent  # .claude/skills

# Skills whose scripts/tool.py handles auth/secrets/tenant-isolation and so
# gets the strictest guardrails (golden-file lock + mutation testing).
SECURITY_CRITICAL_SKILLS = {"jwt-authentication", "password-security", "user-isolation"}


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


def _parse_test_functions(tests_dir: Path):
    """AST-based: for every top-level `def test_*`/`async def test_*` in
    tests/test_*.py, return {test_id: {"hash": sha256-of-source, "asserts": N}}.

    This is what makes guardrail #7 (test-body hashing) possible: it lets a
    promotion detect "same test name, different body" even though the
    identity-only check (_test_ids_defined) would see no difference.
    """
    out = {}
    if not tests_dir.exists():
        return out
    for f in sorted(tests_dir.glob("test_*.py")):
        try:
            source = f.read_text()
            tree = ast.parse(source, filename=str(f))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                seg = ast.get_source_segment(source, node) or ""
                asserts = sum(1 for n in ast.walk(node) if isinstance(n, ast.Assert))
                out[f"{f.name}::{node.name}"] = {
                    "hash": hashlib.sha256(seg.encode()).hexdigest(),
                    "asserts": asserts,
                }
    return out


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


def _measure_coverage(tests_dir: Path, impl_file: Path):
    """Best-effort line-coverage percentage (0-100) of impl_file exercised by
    tests_dir. Returns None (never blocks) if the `coverage` package isn't
    installed or measurement fails for any reason -- this check degrades
    gracefully rather than being a hard dependency of the gate.
    """
    if not impl_file.exists():
        return None
    impl_file = impl_file.resolve()
    tests_dir = tests_dir.resolve()
    work_dir = tests_dir.parent
    # Use a system temp file, never a file inside the (possibly permission-
    # restricted, user-owned) skill directory -- this is a throwaway
    # measurement artifact, not something that belongs next to the user's
    # files, and some sandboxed shells cannot delete files they didn't
    # create with elevated permission inside a connected folder.
    tmp_handle = tempfile.NamedTemporaryFile(prefix="skillgate-cov-", suffix=".dat", delete=False)
    data_file = Path(tmp_handle.name)
    tmp_handle.close()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "coverage", "run", f"--data-file={data_file}",
             f"--include={impl_file}", "-m", "pytest", "--import-mode=importlib", str(tests_dir)],
            capture_output=True, text=True, timeout=180, cwd=str(work_dir),
        )
        if proc.returncode != 0:
            return None
        rep = subprocess.run(
            [sys.executable, "-m", "coverage", "report", f"--data-file={data_file}", "--format=total"],
            capture_output=True, text=True, timeout=60, cwd=str(work_dir),
        )
        return float(rep.stdout.strip())
    except (FileNotFoundError, ModuleNotFoundError, ValueError, subprocess.TimeoutExpired):
        return None
    finally:
        if data_file.exists():
            data_file.unlink()


_CMP_FLIPS = {
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE, ast.GtE: ast.Lt,
    ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
}


def _mutation_sites(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if type(op) in _CMP_FLIPS:
                    sites.append(("cmp", node.lineno, node.col_offset, i))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            sites.append(("bool", node.lineno, node.col_offset, None))
    return sites


def _apply_mutation(source: str, site):
    kind, lineno, col_offset, extra = site
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if kind == "cmp" and isinstance(node, ast.Compare) and node.lineno == lineno and node.col_offset == col_offset:
            op = node.ops[extra]
            node.ops[extra] = _CMP_FLIPS[type(op)]()
            return ast.unparse(tree)
        if kind == "bool" and isinstance(node, ast.Constant) and node.lineno == lineno and node.col_offset == col_offset:
            node.value = not node.value
            return ast.unparse(tree)
    return source


def _mutation_score(tests_dir: Path, impl_file: Path, max_mutants=20):
    """Lightweight mutation testing (comparisons + booleans only -- see
    module docstring #10). Returns (score 0.0-1.0, mutants_tried) or
    (None, 0) if impl_file has no mutable sites.
    """
    if not impl_file.exists():
        return None, 0
    original = impl_file.read_text()
    sites = _mutation_sites(original)[:max_mutants]
    if not sites:
        return None, 0
    killed = 0
    for site in sites:
        mutated = _apply_mutation(original, site)
        if mutated == original:
            continue
        impl_file.write_text(mutated)
        try:
            code, _, _, _ = _run_pytest(tests_dir)
        finally:
            impl_file.write_text(original)
        if code != 0:
            killed += 1
    return killed / len(sites), len(sites)


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


def _golden_path(skill_dir: Path):
    return skill_dir / "golden.json"


def _check_golden(skill_dir: Path, staged_dir: Path):
    """Security-critical skills only. Returns a list of problems (empty if
    fine, or if the skill has no golden.json yet)."""
    golden_file = _golden_path(skill_dir)
    if not golden_file.exists():
        return []
    golden = json.loads(golden_file.read_text())
    problems = []
    for rel_path, expected_hash in golden.items():
        staged_file = staged_dir / rel_path
        if not staged_file.exists():
            problems.append(f"{rel_path}: missing in staged version")
            continue
        actual_hash = hashlib.sha256(staged_file.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            problems.append(f"{rel_path}: content changed (golden-file hash mismatch)")
    return problems


def _write_golden(skill_dir: Path, rel_paths):
    data = {}
    for rel_path in rel_paths:
        f = skill_dir / rel_path
        if f.exists():
            data[rel_path] = hashlib.sha256(f.read_bytes()).hexdigest()
    _golden_path(skill_dir).write_text(json.dumps(data, indent=2) + "\n")


def promote(skill_name, staged_dir, bump_part="patch", reason="", allow_file_removal=False,
            acknowledge_test_change=None, change_reason="", allow_coverage_drop=False,
            acknowledge_golden_change=False, allow_mutation_drop=False):
    skill_dir = SKILLS_ROOT / skill_name
    staged_dir = Path(staged_dir)
    archive_root = SKILLS_ROOT / "_archive" / skill_name
    acknowledge_test_change = acknowledge_test_change or set()

    # --- Check 1: no silent file loss -----------------------------------
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

    # --- Check 2: test suite never shrinks (by name) ---------------------
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

    # --- Check 3 (NEW): test-body hashing --------------------------------
    # Catches "same test name, weaker/different assertions" -- the gap the
    # original identity-only check could not see.
    version_data = read_version(skill_dir)
    baseline_test_info = version_data.get("test_baseline", {})
    staged_test_info = _parse_test_functions(staged_dir / "tests")
    changed_tests = []
    if baseline_test_info:  # skip gracefully if this skill predates the feature
        for test_id, base_info in baseline_test_info.items():
            staged_info = staged_test_info.get(test_id)
            if staged_info and staged_info["hash"] != base_info["hash"]:
                changed_tests.append((test_id, base_info["asserts"], staged_info["asserts"]))
    if changed_tests:
        unacknowledged = [t for t, _, _ in changed_tests
                          if acknowledge_test_change != {"all"} and t not in acknowledge_test_change]
        if unacknowledged or not change_reason:
            lines = "\n".join(
                f"  - {t}: {old_a} assert(s) -> {new_a} assert(s)" for t, old_a, new_a in changed_tests
            )
            report = (
                f"REJECTED promotion of '{skill_name}': {len(changed_tests)} existing test(s) "
                f"kept their name but their body changed -- this is exactly the 'weaker test, "
                f"same name' pattern this gate exists to catch:\n{lines}\n"
                f"If this change is deliberate and justified, re-run with "
                f"--acknowledge-test-change {','.join(t for t, _, _ in changed_tests)} "
                f"(or --acknowledge-test-change all) and --change-reason \"...\"."
            )
            _log_rejection(archive_root, report)
            print(report)
            return 1

    # --- Check 4 (security-critical only, NEW): golden-file protection --
    if skill_name in SECURITY_CRITICAL_SKILLS:
        golden_problems = _check_golden(skill_dir, staged_dir)
        if golden_problems and not (acknowledge_golden_change and change_reason):
            report = (
                f"REJECTED promotion of security-critical skill '{skill_name}': golden-file "
                f"check failed:\n" + "\n".join(f"  - {p}" for p in golden_problems) + "\n"
                f"Security-critical skills lock their test file's exact content. Any change, "
                f"however reasonable it looks, needs --acknowledge-golden-change and "
                f"--change-reason \"...\"."
            )
            _log_rejection(archive_root, report)
            print(report)
            return 1

    # --- Check 5: full staged pytest run must pass ------------------------
    _, base_passed, _, _ = _run_pytest(skill_dir / "tests")
    staged_code, staged_passed, staged_failed, staged_out = _run_pytest(staged_dir / "tests")
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

    # --- Check 6 (NEW): coverage never shrinks ---------------------------
    baseline_coverage = version_data.get("coverage_pct")
    staged_coverage = _measure_coverage(staged_dir / "tests", staged_dir / "scripts" / "tool.py")
    if baseline_coverage is not None and staged_coverage is not None:
        if staged_coverage + 0.5 < baseline_coverage and not allow_coverage_drop:
            report = (
                f"REJECTED promotion of '{skill_name}': test coverage of scripts/tool.py would "
                f"drop from {baseline_coverage:.1f}% to {staged_coverage:.1f}%. "
                f"Re-run with --allow-coverage-drop if this is deliberate and justified."
            )
            _log_rejection(archive_root, report)
            print(report)
            return 1

    # --- Check 7 (security-critical only, NEW): mutation testing --------
    baseline_mutation = version_data.get("mutation_score")
    staged_mutation = None
    if skill_name in SECURITY_CRITICAL_SKILLS:
        staged_mutation, n_mutants = _mutation_score(staged_dir / "tests", staged_dir / "scripts" / "tool.py")
        if baseline_mutation is not None and staged_mutation is not None:
            if staged_mutation + 0.001 < baseline_mutation and not allow_mutation_drop:
                report = (
                    f"REJECTED promotion of security-critical skill '{skill_name}': mutation "
                    f"kill-score would drop from {baseline_mutation:.0%} to {staged_mutation:.0%} "
                    f"({n_mutants} mutants tried) -- the test suite would catch fewer injected "
                    f"bugs than before, even though it passes. Re-run with "
                    f"--allow-mutation-drop if this is deliberate and justified."
                )
                _log_rejection(archive_root, report)
                print(report)
                return 1

    # --- All checks passed: promote --------------------------------------
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
    version_data["test_baseline"] = staged_test_info
    if staged_coverage is not None:
        version_data["coverage_pct"] = staged_coverage
    if staged_mutation is not None:
        version_data["mutation_score"] = staged_mutation
    history_entry = {
        "version": new_version,
        "date": ts,
        "reason": reason or "promotion",
        "baseline_tests_verified": sorted(baseline_static),
        "new_tests_added": sorted(staged_static - baseline_static),
    }
    if changed_tests:
        history_entry["acknowledged_test_changes"] = {
            t: {"reason": change_reason, "asserts_before": old_a, "asserts_after": new_a}
            for t, old_a, new_a in changed_tests
        }
    version_data.setdefault("history", []).append(history_entry)
    write_version(skill_dir, version_data)

    if skill_name in SECURITY_CRITICAL_SKILLS:
        _write_golden(skill_dir, ["tests/test_tool.py"])

    changelog_lines = [
        f"\n## {new_version} - {ts}",
        reason or "Promoted via skill_gate.py",
        f"- Verified {len(baseline_static)} pre-existing test(s) still pass",
        f"- {len(staged_static) - len(baseline_static)} new test(s) added",
    ]
    if changed_tests:
        changelog_lines.append(
            f"- ACKNOWLEDGED change to {len(changed_tests)} existing test(s): {change_reason}"
        )
        for t, old_a, new_a in changed_tests:
            changelog_lines.append(f"  - {t}: {old_a} -> {new_a} assert(s)")
    if staged_coverage is not None:
        changelog_lines.append(f"- Coverage of scripts/tool.py: {staged_coverage:.1f}%")
    if staged_mutation is not None:
        changelog_lines.append(f"- Mutation kill-score: {staged_mutation:.0%}")
    with open(skill_dir / "CHANGELOG.md", "a") as f:
        f.write("\n".join(changelog_lines) + "\n")

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
    promote_p.add_argument("--acknowledge-test-change", default="",
                            help="Comma-separated test ids whose body change is deliberate, or 'all'.")
    promote_p.add_argument("--change-reason", default="",
                            help="Required alongside --acknowledge-test-change / --acknowledge-golden-change.")
    promote_p.add_argument("--allow-coverage-drop", action="store_true")
    promote_p.add_argument("--acknowledge-golden-change", action="store_true")
    promote_p.add_argument("--allow-mutation-drop", action="store_true")

    check_p = sub.add_parser("check")
    check_p.add_argument("--skill", required=True)

    args = p.parse_args()
    if args.command == "promote":
        ack = set(x for x in args.acknowledge_test_change.split(",") if x) if args.acknowledge_test_change else set()
        return promote(
            args.skill, Path(args.staged_dir), args.bump, args.reason, args.allow_file_removal,
            acknowledge_test_change=ack, change_reason=args.change_reason,
            allow_coverage_drop=args.allow_coverage_drop,
            acknowledge_golden_change=args.acknowledge_golden_change,
            allow_mutation_drop=args.allow_mutation_drop,
        )
    if args.command == "check":
        return check(args.skill)
    return 1


if __name__ == "__main__":
    sys.exit(main())
