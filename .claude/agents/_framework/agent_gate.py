#!/usr/bin/env python3
"""
Agent onboarding/regression gate for .claude/agents/*.md Digital FTE agent
definitions.

Unlike skills (executable scripts/tool.py we can unit-test, measure coverage
and mutation-kill-rate on), agents are markdown persona/instruction files
consumed by an LLM at runtime -- there is no code path to execute or mutate.
So this gate enforces a *structural* bar instead of an execution bar:

  1. Required frontmatter fields are present (name, role, description,
     version).
  2. Required section headings exist in the body, so every agent explicitly
     states its role, its in-scope work, which tools it may use, its
     guardrails, its escalation rules, and what it will NOT do.
  3. A companion eval-scenarios file (.claude/agents/_meta/<agent>/eval_scenarios.yaml)
     exists with at least MIN_EVAL_SCENARIOS well-formed entries (a scenario
     prompt + the expected behavior) -- documented test cases a human or a
     future live-eval runner can execute the agent against, even though this
     gate does not itself make any LLM calls.
  4. A companion red-team/adversarial-prompts file
     (.claude/agents/_meta/<agent>/redteam_prompts.yaml) exists with at
     least MIN_REDTEAM_PROMPTS well-formed entries (a boundary-testing
     prompt + the expected refusal/escalation behavior).
  5. A per-agent version.json exists under the same _meta/<agent>/ dir with
     a 'version' field, mirroring the skills framework's version.json.

This is deliberately the "static/structural" tier of agent QA (no live LLM
grading calls) -- an explicit, deliberate choice to avoid the LLM-call
volume a live-eval-grading pass would need. Nothing here stops a future
live-eval runner from being layered on top using the same
eval_scenarios.yaml / redteam_prompts.yaml files as its input; this gate
only guarantees that input material exists and is well-formed.

Usage:
  python3 agent_gate.py check --agents-dir <path-to-.claude/agents> --agent-name <name>

Exit code 0 = PASS, 1 = BLOCKED. Always prints a full, human-readable score
report on stdout on both outcomes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in envs without PyYAML
    yaml = None


REQUIRED_FRONTMATTER_FIELDS = ["name", "role", "description", "version"]

# Each entry: (label, regex matched against a stripped line, case-insensitive)
# Matches a markdown heading (##, ###, ...) whose text starts with the given
# keyword(s), so agents are free to phrase headings naturally (e.g.
# "## Scope & Boundaries", "## Tools & Permissions") as long as the required
# keyword leads the heading text.
REQUIRED_SECTIONS = [
    ("Role", r"^#{1,4}\s*role\b"),
    ("Scope", r"^#{1,4}\s*(in[- ]scope\b|scope\b)"),
    ("Tools Allowed", r"^#{1,4}\s*(allowed tools\b|tools allowed\b|tools\s*(&|and)?\s*permissions\b)"),
    ("Guardrails", r"^#{1,4}\s*guardrails?\b"),
    ("Escalation Rules", r"^#{1,4}\s*escalation"),
    ("Out of Scope", r"^#{1,4}\s*out[- ]of[- ]scope"),
]

MIN_EVAL_SCENARIOS = 5
MIN_REDTEAM_PROMPTS = 5

META_DIRNAME = "_meta"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n(.*)$", re.DOTALL)
FALLBACK_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def meta_dir_for(agents_dir: Path, agent_name: str) -> Path:
    return agents_dir / META_DIRNAME / agent_name


def _parse_frontmatter_fallback(fm_text: str) -> dict:
    """Minimal top-level `key: value` extractor used only if PyYAML is not
    installed. Handles the flat string fields this gate checks
    (name/role/description/version); does not attempt list/nested parsing,
    so a list-valued key like `skills:` is simply skipped here."""
    data = {}
    for line in fm_text.splitlines():
        if not line or line[0] in " \t-#":
            continue
        m = FALLBACK_KEY_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val:
                data[key] = val.strip("\"'")
    return data


def parse_frontmatter(md_text: str):
    """Returns (frontmatter_dict, body_text). frontmatter_dict is {} if no
    frontmatter block is found or it fails to parse."""
    m = FRONTMATTER_RE.match(md_text)
    if not m:
        return {}, md_text
    fm_text, body = m.group(1), m.group(2)
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    else:
        data = _parse_frontmatter_fallback(fm_text)
    return data, body


def missing_frontmatter_fields(frontmatter: dict):
    return [f for f in REQUIRED_FRONTMATTER_FIELDS if not frontmatter.get(f)]


def missing_sections(body: str):
    lines = [ln.strip() for ln in body.splitlines()]
    missing = []
    for label, pattern in REQUIRED_SECTIONS:
        rx = re.compile(pattern, re.IGNORECASE)
        if not any(rx.search(ln) for ln in lines):
            missing.append(label)
    return missing


def _load_yaml_list(path: Path):
    """Loads a YAML file expected to be a top-level list of dicts. Returns
    (list_or_None, error_message_or_None)."""
    if not path.exists():
        return None, f"{path.name} not found"
    text = path.read_text()
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            return None, f"{path.name} is not valid YAML: {e}"
    else:
        try:
            data = json.loads(text)
        except Exception as e:
            return None, (
                f"{path.name} could not be parsed (no PyYAML installed, "
                f"and it is not valid JSON either): {e}"
            )
    if data is None:
        data = []
    if not isinstance(data, list):
        return None, f"{path.name} must be a YAML list of entries"
    return data, None


def _valid_eval_scenario(entry) -> bool:
    return bool(
        isinstance(entry, dict)
        and isinstance(entry.get("scenario"), str) and entry.get("scenario").strip()
        and isinstance(entry.get("expected_behavior"), str) and entry.get("expected_behavior").strip()
    )


def _valid_redteam_prompt(entry) -> bool:
    return bool(
        isinstance(entry, dict)
        and isinstance(entry.get("prompt"), str) and entry.get("prompt").strip()
        and isinstance(entry.get("expected_behavior"), str) and entry.get("expected_behavior").strip()
    )


def check_eval_scenarios(meta_dir: Path):
    data, err = _load_yaml_list(meta_dir / "eval_scenarios.yaml")
    if err:
        return 0, [err]
    reasons = []
    valid = [e for e in data if _valid_eval_scenario(e)]
    invalid_count = len(data) - len(valid)
    if invalid_count:
        reasons.append(
            f"{invalid_count} eval_scenarios.yaml entry(ies) missing 'scenario' or 'expected_behavior'"
        )
    if len(valid) < MIN_EVAL_SCENARIOS:
        reasons.append(
            f"Only {len(valid)} well-formed eval scenario(s); minimum required is {MIN_EVAL_SCENARIOS}."
        )
    return len(valid), reasons


def check_redteam_prompts(meta_dir: Path):
    data, err = _load_yaml_list(meta_dir / "redteam_prompts.yaml")
    if err:
        return 0, [err]
    reasons = []
    valid = [e for e in data if _valid_redteam_prompt(e)]
    invalid_count = len(data) - len(valid)
    if invalid_count:
        reasons.append(
            f"{invalid_count} redteam_prompts.yaml entry(ies) missing 'prompt' or 'expected_behavior'"
        )
    if len(valid) < MIN_REDTEAM_PROMPTS:
        reasons.append(
            f"Only {len(valid)} well-formed red-team prompt(s); minimum required is {MIN_REDTEAM_PROMPTS}."
        )
    return len(valid), reasons


def check_agent_version_file(meta_dir: Path):
    path = meta_dir / "version.json"
    if not path.exists():
        return None, [f"version.json not found in {META_DIRNAME}/{meta_dir.name}/"]
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return None, [f"version.json is not valid JSON: {e}"]
    if not isinstance(data, dict) or not data.get("version"):
        return None, ["version.json must be an object with a non-empty 'version' field"]
    return data.get("version"), []


def check_eval_results(meta_dir: Path, eval_count: int, redteam_count: int):
    """Verifies a live-eval run was actually recorded: eval_results.json
    must exist, list a result for every eval_scenarios and redteam_prompts
    entry (by 1-indexed id `eval_scenarios#N` / `redteam_prompts#N`), and
    every recorded verdict must be PASS. A live eval that was run and
    produced a FAIL/CONCERN is a genuine finding -- it blocks the gate
    until the underlying agent definition is fixed and re-evaluated; it
    must never be papered over by deleting or skipping the failing entry.
    """
    path = meta_dir / "eval_results.json"
    if not path.exists():
        return {}, [f"eval_results.json not found in {META_DIRNAME}/{meta_dir.name}/ -- live eval has not been run"]
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return {}, [f"eval_results.json is not valid JSON: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return {}, ["eval_results.json must be an object with a 'results' list"]

    by_id = {}
    for entry in data["results"]:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            by_id[entry["id"]] = entry.get("verdict")

    reasons = []
    expected_ids = [f"eval_scenarios#{i}" for i in range(1, eval_count + 1)]
    expected_ids += [f"redteam_prompts#{i}" for i in range(1, redteam_count + 1)]

    missing_ids = [eid for eid in expected_ids if eid not in by_id]
    if missing_ids:
        reasons.append(f"eval_results.json is missing result(s) for: {', '.join(missing_ids)}")

    failing_ids = [eid for eid in expected_ids if by_id.get(eid) not in (None, "PASS")]
    if failing_ids:
        details = ", ".join(f"{eid}={by_id[eid]}" for eid in failing_ids)
        reasons.append(f"Live eval did not PASS for: {details}")

    return by_id, reasons


def run_agent_checks(agents_dir: Path, agent_name: str) -> dict:
    """Runs every onboarding/regression check and returns a full report
    dict. Never raises for an expected failure mode -- unmet checks show up
    as reasons in the report, not exceptions."""
    report = {
        "agent": agent_name,
        "passed": False,
        "reasons": [],
        "missing_frontmatter_fields": [],
        "missing_sections": [],
        "eval_scenario_count": 0,
        "redteam_prompt_count": 0,
        "meta_version": None,
        "eval_results": {},
    }

    md_path = agents_dir / f"{agent_name}.md"
    if not md_path.exists():
        report["reasons"].append(f"{agent_name}.md not found")
        return report

    md_text = md_path.read_text()
    frontmatter, body = parse_frontmatter(md_text)

    missing_fm = missing_frontmatter_fields(frontmatter)
    report["missing_frontmatter_fields"] = missing_fm
    if missing_fm:
        report["reasons"].append(f"Missing required frontmatter field(s): {', '.join(missing_fm)}")

    missing_sec = missing_sections(body)
    report["missing_sections"] = missing_sec
    if missing_sec:
        report["reasons"].append(f"Missing required section(s): {', '.join(missing_sec)}")

    meta_dir = meta_dir_for(agents_dir, agent_name)

    eval_count, eval_reasons = check_eval_scenarios(meta_dir)
    report["eval_scenario_count"] = eval_count
    report["reasons"].extend(eval_reasons)

    redteam_count, redteam_reasons = check_redteam_prompts(meta_dir)
    report["redteam_prompt_count"] = redteam_count
    report["reasons"].extend(redteam_reasons)

    version, version_reasons = check_agent_version_file(meta_dir)
    report["meta_version"] = version
    report["reasons"].extend(version_reasons)

    eval_results, eval_result_reasons = check_eval_results(meta_dir, eval_count, redteam_count)
    report["eval_results"] = eval_results
    report["reasons"].extend(eval_result_reasons)

    report["passed"] = len(report["reasons"]) == 0
    return report


def format_report(report: dict) -> str:
    lines = []
    name = report["agent"]
    if report["passed"]:
        lines.append(f"PASS -- '{name}' meets the agent QA bar.")
    else:
        lines.append(f"BLOCKED -- '{name}' does NOT meet the agent QA bar yet.")
    lines.append("")
    lines.append("  Score breakdown:")
    lines.append(
        f"    Frontmatter fields missing: {', '.join(report['missing_frontmatter_fields']) or 'none'}"
    )
    lines.append(
        f"    Sections missing:           {', '.join(report['missing_sections']) or 'none'}"
    )
    lines.append(
        f"    Eval scenarios:              {report['eval_scenario_count']} (minimum {MIN_EVAL_SCENARIOS})"
    )
    lines.append(
        f"    Red-team prompts:            {report['redteam_prompt_count']} (minimum {MIN_REDTEAM_PROMPTS})"
    )
    lines.append(f"    Meta version:                {report['meta_version'] or 'N/A'}")
    n_pass = sum(1 for v in report['eval_results'].values() if v == "PASS")
    n_total = len(report['eval_results'])
    lines.append(f"    Live eval results recorded:  {n_pass}/{n_total} PASS")
    lines.append("")
    if report["reasons"]:
        lines.append("  Reason(s) this is BLOCKED:" if not report["passed"] else "  (unreachable)")
        for r in report["reasons"]:
            lines.append(f"    - {r}")
    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check")
    check_p.add_argument("--agents-dir", required=True)
    check_p.add_argument("--agent-name", required=True)
    args = p.parse_args()

    if args.command == "check":
        report = run_agent_checks(Path(args.agents_dir), args.agent_name)
        print(format_report(report))
        return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
