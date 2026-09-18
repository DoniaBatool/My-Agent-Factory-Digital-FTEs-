#!/usr/bin/env python3
"""
New-skill onboarding gate.

Problem this closes: the existing skill_gate.py (promote/check) only protects
a skill that ALREADY has a baseline -- it prevents *regressions*. It has no
opinion on how strong a BRAND NEW skill's test suite is on day one. Nothing
stopped a new skill from being committed with a thin/absent tests/ dir.

This script is the one-time entry gate for a new skill's FIRST commit. It is
intentionally stricter than the ongoing promote() gate in one respect: it
always runs mutation testing (not just for SECURITY_CRITICAL_SKILLS), because
this check fires once per skill's lifetime (at creation), not on every future
promotion -- so the extra cost is affordable here in a way it would not be if
paid on every regular update.

Checks (all must pass for a PASS verdict):
  1. Required files present: SKILL.md, scripts/tool.py, tests/test_tool.py,
     version.json, CHANGELOG.md.
     (examples/ and README.md are RECOMMENDED, reported but non-blocking --
     not every skill needs worked examples to be trustworthy.)
  2. tests/test_tool.py defines at least MIN_TESTS test functions.
  3. The full test suite for this skill passes (0 failures).
  4. Line coverage of scripts/tool.py >= MIN_COVERAGE.
  5. Mutation kill-score of scripts/tool.py's test suite >= MIN_MUTATION.

Usage:
  python3 new_skill_gate.py check --skill-dir <path-to-skill-dir> --skill-name <name>

Exit code 0 = PASS (skill is strong enough to onboard), 1 = BLOCKED.
Always prints a full, human-readable score report on stdout, on both
outcomes -- this is the "notification" ci_gate_check.py surfaces so a
human/agent always sees WHY a new skill passed or was blocked, not just a
bare exit code.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# Import the measurement primitives from the existing gate so both scripts
# agree on exactly how coverage/mutation/test-parsing are computed.
_THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(_THIS_DIR))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("skill_gate", _THIS_DIR / "skill_gate.py")
skill_gate = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(skill_gate)

REQUIRED_FILES = ["SKILL.md", "scripts/tool.py", "tests/test_tool.py", "version.json", "CHANGELOG.md"]
RECOMMENDED_FILES = ["examples/", "README.md"]

# Deliberately close to (but not literally) 100 / 100: a handful of legitimate
# defensive branches (e.g. "this OS call can never actually fail in tests")
# make a hard 100% requirement counter-productive -- it would reward deleting
# defensive code over writing a test for it. Tune here if these prove wrong
# in practice; the point is "as close to bulletproof as realistically gets
# enforced automatically", not a magic number.
MIN_TESTS = 5
MIN_COVERAGE = 95.0
MIN_MUTATION = 90.0
MAX_MUTANTS = 30


def _missing_required_files(skill_dir: Path):
    missing = []
    for rel in REQUIRED_FILES:
        if not (skill_dir / rel).exists():
            missing.append(rel)
    return missing


def _missing_recommended_files(skill_dir: Path):
    missing = []
    for rel in RECOMMENDED_FILES:
        p = skill_dir / rel.rstrip("/")
        if not p.exists():
            missing.append(rel)
    return missing


def run_new_skill_checks(skill_dir: Path, skill_name: str) -> dict:
    """Runs every onboarding check and returns a full report dict.
    Never raises for an expected failure mode -- unmet checks show up as
    reasons in the report, not exceptions."""
    report = {
        "skill": skill_name,
        "passed": False,
        "reasons": [],
        "missing_required_files": [],
        "missing_recommended_files": [],
        "test_count": None,
        "tests_passed": None,
        "coverage_pct": None,
        "mutation_score": None,
        "mutants_tried": None,
    }

    missing_required = _missing_required_files(skill_dir)
    report["missing_required_files"] = missing_required
    if missing_required:
        report["reasons"].append(
            f"Missing required file(s): {', '.join(missing_required)}"
        )

    report["missing_recommended_files"] = _missing_recommended_files(skill_dir)

    tests_dir = skill_dir / "tests"
    impl_file = skill_dir / "scripts" / "tool.py"

    if (tests_dir / "test_tool.py").exists():
        test_info = skill_gate._parse_test_functions(tests_dir)
        report["test_count"] = len(test_info)
        if len(test_info) < MIN_TESTS:
            report["reasons"].append(
                f"Only {len(test_info)} test(s) found; minimum required is {MIN_TESTS}."
            )
    else:
        report["test_count"] = 0
        report["reasons"].append(f"No tests/test_tool.py found; minimum required is {MIN_TESTS} tests.")

    # Run the suite for real, regardless of the count check above, so we
    # always know whether what's there actually passes.
    if tests_dir.exists():
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--import-mode=importlib", "-q", str(tests_dir)],
            capture_output=True, text=True, timeout=120,
        )
        report["tests_passed"] = proc.returncode == 0
        if proc.returncode != 0:
            report["reasons"].append("Test suite does not pass (pytest exited non-zero).")
    else:
        report["tests_passed"] = False

    if impl_file.exists() and tests_dir.exists():
        cov = skill_gate._measure_coverage(tests_dir, impl_file)
        report["coverage_pct"] = cov
        if cov is None:
            report["reasons"].append("Could not measure coverage (tests failed to run under `coverage`).")
        elif cov < MIN_COVERAGE:
            report["reasons"].append(
                f"Coverage {cov:.1f}% is below the required {MIN_COVERAGE:.1f}%."
            )

        mut_score, n_mutants = skill_gate._mutation_score(tests_dir, impl_file, max_mutants=MAX_MUTANTS)
        report["mutation_score"] = mut_score
        report["mutants_tried"] = n_mutants
        if mut_score is None:
            report["reasons"].append("Could not measure mutation score.")
        elif mut_score < MIN_MUTATION / 100.0:
            report["reasons"].append(
                f"Mutation score {mut_score*100:.1f}% is below the required {MIN_MUTATION:.1f}%"
                f" ({n_mutants} mutants tried)."
            )
    else:
        report["reasons"].append("scripts/tool.py or tests/ missing -- cannot measure coverage/mutation.")

    report["passed"] = len(report["reasons"]) == 0
    return report


def format_report(report: dict) -> str:
    lines = []
    name = report["skill"]
    if report["passed"]:
        lines.append(f"PASS -- '{name}' is strong enough to onboard.")
    else:
        lines.append(f"BLOCKED -- '{name}' is NOT strong enough to onboard yet.")
    lines.append("")
    lines.append("  Score breakdown:")
    tc = report["test_count"]
    lines.append(f"    Tests defined:     {tc if tc is not None else 'N/A'} (minimum {MIN_TESTS})")
    tp = report["tests_passed"]
    lines.append(f"    Tests passing:     {'yes' if tp else 'no' if tp is not None else 'N/A'}")
    cov = report["coverage_pct"]
    lines.append(f"    Coverage:          {f'{cov:.1f}%' if cov is not None else 'N/A'} (minimum {MIN_COVERAGE:.1f}%)")
    mut = report["mutation_score"]
    nm = report["mutants_tried"]
    if mut is not None:
        lines.append(f"    Mutation score:    {mut*100:.1f}% ({nm} mutants tried) (minimum {MIN_MUTATION:.1f}%)")
    else:
        lines.append(f"    Mutation score:    N/A (minimum {MIN_MUTATION:.1f}%)")
    # "Strength score" = the mutation score, reported as a percentage --
    # deliberately NOT a blended/opaque formula. Coverage tells you how much
    # code ran during tests; mutation score tells you whether the tests would
    # actually NOTICE if that code broke. The second one is the true "how
    # tough/solid is this skill" number, so it IS the strength score rather
    # than being folded into one.
    if mut is not None:
        lines.append(f"    Strength score:    {mut*100:.1f}%  (this is what 'how strong/tough is this skill' means)")
    else:
        lines.append("    Strength score:    N/A")
    lines.append("")
    if report["missing_required_files"]:
        lines.append(f"  Missing REQUIRED files: {', '.join(report['missing_required_files'])}")
    if report["missing_recommended_files"]:
        lines.append(f"  Missing recommended (non-blocking) files: {', '.join(report['missing_recommended_files'])}")
    if report["reasons"]:
        lines.append("")
        lines.append("  Reason(s) this is BLOCKED:" if not report["passed"] else "  (unreachable)")
        for r in report["reasons"]:
            lines.append(f"    - {r}")
    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check")
    check_p.add_argument("--skill-dir", required=True)
    check_p.add_argument("--skill-name", required=True)
    args = p.parse_args()

    if args.command == "check":
        report = run_new_skill_checks(Path(args.skill_dir), args.skill_name)
        print(format_report(report))
        return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
