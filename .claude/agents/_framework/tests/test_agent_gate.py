"""
Genuine regression tests for agent_gate.py -- the structural QA gate for
.claude/agents/*.md Digital FTE agent definitions.

Every test asserts real, computed output (report dicts, exit codes, exact
missing-field/section lists) -- never a bare "doesn't crash" check.
"""
import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pytest

_THIS_DIR = Path(__file__).parent
_MODULE_PATH = _THIS_DIR.parent / "agent_gate.py"
_spec = _ilu.spec_from_file_location("agent_gate", _MODULE_PATH)
agent_gate = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(agent_gate)


VALID_BODY_SECTIONS = """# Some Agent

## Role
Does things.

## Scope
In scope stuff.

## Tools Allowed
May use X.

## Guardrails
Never do Y.

## Escalation Rules
Escalate on Z.

## Out of Scope
Does not do W.
"""

VALID_FRONTMATTER = """---
name: sample-agent
role: Sample Role
description: A sample agent for testing
version: "1.0.0"
---
"""


def _write_agent_md(agents_dir: Path, name: str, frontmatter: str, body: str):
    (agents_dir / f"{name}.md").write_text(frontmatter + body)


def _write_meta(agents_dir: Path, name: str, *, evals=None, redteam=None, version=None, eval_results=None):
    meta_dir = agents_dir / agent_gate.META_DIRNAME / name
    meta_dir.mkdir(parents=True, exist_ok=True)
    if evals is not None:
        (meta_dir / "eval_scenarios.yaml").write_text(evals)
    if redteam is not None:
        (meta_dir / "redteam_prompts.yaml").write_text(redteam)
    if version is not None:
        (meta_dir / "version.json").write_text(version)
    if eval_results is not None:
        (meta_dir / "eval_results.json").write_text(eval_results)
    return meta_dir


def _all_pass_eval_results_json(n_evals=5, n_redteam=5):
    results = [{"id": f"eval_scenarios#{i}", "verdict": "PASS"} for i in range(1, n_evals + 1)]
    results += [{"id": f"redteam_prompts#{i}", "verdict": "PASS"} for i in range(1, n_redteam + 1)]
    return json.dumps({"results": results})


VALID_EVAL_YAML = "\n".join(
    f"- scenario: \"Scenario {i}\"\n  expected_behavior: \"Behavior {i}\"" for i in range(1, 6)
)
VALID_REDTEAM_YAML = "\n".join(
    f"- prompt: \"Prompt {i}\"\n  expected_behavior: \"Refuse {i}\"" for i in range(1, 6)
)
VALID_VERSION_JSON = json.dumps({"version": "1.0.0", "history": []})


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

def test_parse_frontmatter_extracts_fields_and_body():
    text = VALID_FRONTMATTER + "\n# Body\nHello\n"
    fm, body = agent_gate.parse_frontmatter(text)
    assert fm["name"] == "sample-agent"
    assert fm["role"] == "Sample Role"
    assert fm["version"] == "1.0.0"
    assert body.strip() == "# Body\nHello"


def test_parse_frontmatter_returns_empty_dict_when_no_frontmatter_block():
    text = "# Just a body\nNo frontmatter here.\n"
    fm, body = agent_gate.parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_returns_empty_dict_on_malformed_yaml():
    text = "---\nname: [unclosed\n---\nBody text\n"
    fm, body = agent_gate.parse_frontmatter(text)
    assert fm == {}
    assert body == "Body text\n"


def test_parse_frontmatter_returns_empty_dict_when_yaml_parses_to_non_dict():
    # Valid YAML, but its top-level value is a list, not a mapping -- the
    # frontmatter block is present and well-formed YAML, just not shaped
    # like frontmatter.
    text = "---\n- one\n- two\n---\nBody text\n"
    fm, body = agent_gate.parse_frontmatter(text)
    assert fm == {}
    assert body == "Body text\n"


def test_parse_frontmatter_fallback_extracts_flat_keys(monkeypatch):
    monkeypatch.setattr(agent_gate, "yaml", None)
    text = "---\nname: fallback-agent\nrole: Fallback Role\nskills:\n  - one\n  - two\n---\nBody\n"
    fm, body = agent_gate.parse_frontmatter(text)
    assert fm["name"] == "fallback-agent"
    assert fm["role"] == "Fallback Role"
    # list-valued keys are not captured by the flat fallback parser
    assert "skills" not in fm
    assert body == "Body\n"


# ---------------------------------------------------------------------------
# missing_frontmatter_fields
# ---------------------------------------------------------------------------

def test_missing_frontmatter_fields_none_missing():
    fm = {"name": "a", "role": "b", "description": "c", "version": "1.0.0"}
    assert agent_gate.missing_frontmatter_fields(fm) == []


def test_missing_frontmatter_fields_reports_each_missing_one():
    fm = {"name": "a", "description": "c"}
    missing = agent_gate.missing_frontmatter_fields(fm)
    assert missing == ["role", "version"]


def test_missing_frontmatter_fields_treats_empty_string_as_missing():
    fm = {"name": "a", "role": "", "description": "c", "version": "1.0.0"}
    assert agent_gate.missing_frontmatter_fields(fm) == ["role"]


# ---------------------------------------------------------------------------
# missing_sections
# ---------------------------------------------------------------------------

def test_missing_sections_none_missing_for_full_body():
    assert agent_gate.missing_sections(VALID_BODY_SECTIONS) == []


def test_missing_sections_detects_each_absent_section():
    body = "# Agent\n\n## Role\nDoes things.\n"
    missing = agent_gate.missing_sections(body)
    assert missing == ["Scope", "Tools Allowed", "Guardrails", "Escalation Rules", "Out of Scope"]


def test_missing_sections_accepts_heading_variants():
    body = (
        "## Role\nx\n"
        "## In Scope\nx\n"
        "## Allowed Tools\nx\n"
        "## Guardrail\nx\n"
        "## Escalation\nx\n"
        "## Out-of-Scope\nx\n"
    )
    assert agent_gate.missing_sections(body) == []


def test_missing_sections_is_case_insensitive():
    body = "## ROLE\nx\n## scope\nx\n## TOOLS & PERMISSIONS\nx\n## GUARDRAILS\nx\n## escalation rules\nx\n## OUT OF SCOPE\nx\n"
    assert agent_gate.missing_sections(body) == []


def test_missing_sections_does_not_match_heading_substring_mid_word():
    # "Roleplay" should NOT satisfy the "Role" section requirement.
    body = "## Roleplay Guidelines\nx\n"
    missing = agent_gate.missing_sections(body)
    assert "Role" in missing


# ---------------------------------------------------------------------------
# _load_yaml_list
# ---------------------------------------------------------------------------

def test_load_yaml_list_missing_file(tmp_path):
    data, err = agent_gate._load_yaml_list(tmp_path / "nope.yaml")
    assert data is None
    assert "not found" in err


def test_load_yaml_list_invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("- prompt: [unclosed\n")
    data, err = agent_gate._load_yaml_list(p)
    assert data is None
    assert "not valid YAML" in err


def test_load_yaml_list_not_a_list(tmp_path):
    p = tmp_path / "notlist.yaml"
    p.write_text("prompt: hello\n")
    data, err = agent_gate._load_yaml_list(p)
    assert data is None
    assert "must be a YAML list" in err


def test_load_yaml_list_empty_file_yields_empty_list(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    data, err = agent_gate._load_yaml_list(p)
    assert err is None
    assert data == []


def test_load_yaml_list_valid(tmp_path):
    p = tmp_path / "good.yaml"
    p.write_text(VALID_EVAL_YAML)
    data, err = agent_gate._load_yaml_list(p)
    assert err is None
    assert len(data) == 5


def test_load_yaml_list_fallback_json_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_gate, "yaml", None)
    p = tmp_path / "fallback.yaml"
    p.write_text(json.dumps([{"prompt": "p", "expected_behavior": "b"}]))
    data, err = agent_gate._load_yaml_list(p)
    assert err is None
    assert data == [{"prompt": "p", "expected_behavior": "b"}]


def test_load_yaml_list_fallback_bad_json_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_gate, "yaml", None)
    p = tmp_path / "fallback_bad.yaml"
    p.write_text("not json and not yaml: [")
    data, err = agent_gate._load_yaml_list(p)
    assert data is None
    assert "could not be parsed" in err


# ---------------------------------------------------------------------------
# _valid_eval_scenario / _valid_redteam_prompt
# ---------------------------------------------------------------------------

def test_valid_eval_scenario_true_for_well_formed_entry():
    assert agent_gate._valid_eval_scenario({"scenario": "s", "expected_behavior": "b"}) is True


def test_valid_eval_scenario_false_missing_expected_behavior():
    assert agent_gate._valid_eval_scenario({"scenario": "s"}) is False


def test_valid_eval_scenario_false_for_blank_scenario():
    assert agent_gate._valid_eval_scenario({"scenario": "   ", "expected_behavior": "b"}) is False


def test_valid_eval_scenario_false_for_non_dict():
    assert agent_gate._valid_eval_scenario("not a dict") is False


def test_valid_redteam_prompt_true_for_well_formed_entry():
    assert agent_gate._valid_redteam_prompt({"prompt": "p", "expected_behavior": "b"}) is True


def test_valid_redteam_prompt_false_missing_prompt():
    assert agent_gate._valid_redteam_prompt({"expected_behavior": "b"}) is False


# ---------------------------------------------------------------------------
# check_eval_scenarios / check_redteam_prompts
# ---------------------------------------------------------------------------

def test_check_eval_scenarios_passes_with_enough_valid_entries(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "eval_scenarios.yaml").write_text(VALID_EVAL_YAML)
    count, reasons = agent_gate.check_eval_scenarios(meta_dir)
    assert count == 5
    assert reasons == []


def test_check_eval_scenarios_fails_with_too_few(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "eval_scenarios.yaml").write_text(
        "- scenario: \"only one\"\n  expected_behavior: \"b\""
    )
    count, reasons = agent_gate.check_eval_scenarios(meta_dir)
    assert count == 1
    assert any("minimum required is 5" in r for r in reasons)


def test_check_eval_scenarios_reports_invalid_entries_separately(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    yaml_text = VALID_EVAL_YAML + "\n- scenario: \"missing behavior\"\n"
    (meta_dir / "eval_scenarios.yaml").write_text(yaml_text)
    count, reasons = agent_gate.check_eval_scenarios(meta_dir)
    assert count == 5
    assert any("missing 'scenario' or 'expected_behavior'" in r for r in reasons)


def test_check_eval_scenarios_missing_file(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    count, reasons = agent_gate.check_eval_scenarios(meta_dir)
    assert count == 0
    assert any("not found" in r for r in reasons)


def test_check_redteam_prompts_passes_with_enough_valid_entries(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "redteam_prompts.yaml").write_text(VALID_REDTEAM_YAML)
    count, reasons = agent_gate.check_redteam_prompts(meta_dir)
    assert count == 5
    assert reasons == []


def test_check_redteam_prompts_fails_with_too_few(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "redteam_prompts.yaml").write_text(
        "- prompt: \"only one\"\n  expected_behavior: \"b\""
    )
    count, reasons = agent_gate.check_redteam_prompts(meta_dir)
    assert count == 1
    assert any("minimum required is 5" in r for r in reasons)


def test_check_redteam_prompts_reports_invalid_entries_separately(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    yaml_text = VALID_REDTEAM_YAML + "\n- prompt: \"missing behavior\"\n"
    (meta_dir / "redteam_prompts.yaml").write_text(yaml_text)
    count, reasons = agent_gate.check_redteam_prompts(meta_dir)
    assert count == 5
    assert any("missing 'prompt' or 'expected_behavior'" in r for r in reasons)


# ---------------------------------------------------------------------------
# check_agent_version_file
# ---------------------------------------------------------------------------

def test_check_agent_version_file_missing(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    version, reasons = agent_gate.check_agent_version_file(meta_dir)
    assert version is None
    assert any("not found" in r for r in reasons)


def test_check_agent_version_file_invalid_json(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "version.json").write_text("{not json")
    version, reasons = agent_gate.check_agent_version_file(meta_dir)
    assert version is None
    assert any("not valid JSON" in r for r in reasons)


def test_check_agent_version_file_missing_version_field(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "version.json").write_text(json.dumps({"history": []}))
    version, reasons = agent_gate.check_agent_version_file(meta_dir)
    assert version is None
    assert any("non-empty 'version' field" in r for r in reasons)


def test_check_agent_version_file_valid(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "version.json").write_text(VALID_VERSION_JSON)
    version, reasons = agent_gate.check_agent_version_file(meta_dir)
    assert version == "1.0.0"
    assert reasons == []


# ---------------------------------------------------------------------------
# check_eval_results
# ---------------------------------------------------------------------------

def test_check_eval_results_missing_file(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    results, reasons = agent_gate.check_eval_results(meta_dir, 5, 5)
    assert results == {}
    assert any("has not been run" in r for r in reasons)


def test_check_eval_results_invalid_json(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "eval_results.json").write_text("{not json")
    results, reasons = agent_gate.check_eval_results(meta_dir, 5, 5)
    assert results == {}
    assert any("not valid JSON" in r for r in reasons)


def test_check_eval_results_missing_results_key(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "eval_results.json").write_text(json.dumps({"foo": "bar"}))
    results, reasons = agent_gate.check_eval_results(meta_dir, 5, 5)
    assert results == {}
    assert any("must be an object with a 'results' list" in r for r in reasons)


def test_check_eval_results_all_pass(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    (meta_dir / "eval_results.json").write_text(_all_pass_eval_results_json(3, 2))
    results, reasons = agent_gate.check_eval_results(meta_dir, 3, 2)
    assert reasons == []
    assert len(results) == 5
    assert all(v == "PASS" for v in results.values())


def test_check_eval_results_missing_some_ids(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    # Only 2 of the 3 expected eval_scenarios results recorded.
    partial = json.dumps({"results": [
        {"id": "eval_scenarios#1", "verdict": "PASS"},
        {"id": "eval_scenarios#2", "verdict": "PASS"},
    ]})
    (meta_dir / "eval_results.json").write_text(partial)
    results, reasons = agent_gate.check_eval_results(meta_dir, 3, 0)
    assert any("missing result(s) for: eval_scenarios#3" in r for r in reasons)


def test_check_eval_results_reports_failing_verdict(tmp_path):
    meta_dir = tmp_path / "agentx"
    meta_dir.mkdir()
    mixed = json.dumps({"results": [
        {"id": "eval_scenarios#1", "verdict": "PASS"},
        {"id": "eval_scenarios#2", "verdict": "FAIL"},
        {"id": "redteam_prompts#1", "verdict": "CONCERN"},
    ]})
    (meta_dir / "eval_results.json").write_text(mixed)
    results, reasons = agent_gate.check_eval_results(meta_dir, 2, 1)
    assert any("eval_scenarios#2=FAIL" in r for r in reasons)
    assert any("redteam_prompts#1=CONCERN" in r for r in reasons)


# ---------------------------------------------------------------------------
# run_agent_checks (full integration of the report)
# ---------------------------------------------------------------------------

def test_run_agent_checks_passes_for_fully_onboarded_agent(tmp_path):
    agents_dir = tmp_path
    _write_agent_md(agents_dir, "goodagent", VALID_FRONTMATTER, VALID_BODY_SECTIONS)
    _write_meta(
        agents_dir, "goodagent",
        evals=VALID_EVAL_YAML, redteam=VALID_REDTEAM_YAML, version=VALID_VERSION_JSON,
        eval_results=_all_pass_eval_results_json(),
    )
    report = agent_gate.run_agent_checks(agents_dir, "goodagent")
    assert report["passed"] is True
    assert report["reasons"] == []
    assert report["eval_scenario_count"] == 5
    assert report["redteam_prompt_count"] == 5
    assert report["meta_version"] == "1.0.0"
    assert len(report["eval_results"]) == 10


def test_run_agent_checks_fails_when_md_file_missing(tmp_path):
    report = agent_gate.run_agent_checks(tmp_path, "ghost-agent")
    assert report["passed"] is False
    assert "ghost-agent.md not found" in report["reasons"]


def test_run_agent_checks_reports_every_category_of_failure(tmp_path):
    agents_dir = tmp_path
    # Frontmatter with no version, body with no required sections, no meta dir at all.
    fm = "---\nname: partial\nrole: X\ndescription: Y\n---\n"
    _write_agent_md(agents_dir, "partial", fm, "# Partial\nNo required sections here.\n")
    report = agent_gate.run_agent_checks(agents_dir, "partial")
    assert report["passed"] is False
    assert report["missing_frontmatter_fields"] == ["version"]
    assert report["missing_sections"] == ["Role", "Scope", "Tools Allowed", "Guardrails", "Escalation Rules", "Out of Scope"]
    assert report["eval_scenario_count"] == 0
    assert report["redteam_prompt_count"] == 0
    assert report["meta_version"] is None


def test_run_agent_checks_fails_when_eval_scenarios_too_few(tmp_path):
    agents_dir = tmp_path
    _write_agent_md(agents_dir, "thin", VALID_FRONTMATTER, VALID_BODY_SECTIONS)
    _write_meta(
        agents_dir, "thin",
        evals="- scenario: \"one\"\n  expected_behavior: \"b\"",
        redteam=VALID_REDTEAM_YAML,
        version=VALID_VERSION_JSON,
    )
    report = agent_gate.run_agent_checks(agents_dir, "thin")
    assert report["passed"] is False
    assert report["eval_scenario_count"] == 1


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

def test_format_report_pass_message():
    rep = {
        "agent": "goodagent", "passed": True, "reasons": [],
        "missing_frontmatter_fields": [], "missing_sections": [],
        "eval_scenario_count": 5, "redteam_prompt_count": 5, "meta_version": "1.0.0",
        "eval_results": {f"eval_scenarios#{i}": "PASS" for i in range(1, 6)},
    }
    out = agent_gate.format_report(rep)
    assert "PASS -- 'goodagent' meets the agent QA bar." in out
    assert "Eval scenarios:              5 (minimum 5)" in out
    assert "Live eval results recorded:  5/5 PASS" in out


def test_format_report_blocked_message_lists_reasons():
    rep = {
        "agent": "badagent", "passed": False,
        "reasons": ["Missing required section(s): Scope"],
        "missing_frontmatter_fields": ["version"], "missing_sections": ["Scope"],
        "eval_scenario_count": 0, "redteam_prompt_count": 0, "meta_version": None,
        "eval_results": {},
    }
    out = agent_gate.format_report(rep)
    assert "BLOCKED -- 'badagent' does NOT meet the agent QA bar yet." in out
    assert "Missing required section(s): Scope" in out
    assert "Frontmatter fields missing: version" in out


# ---------------------------------------------------------------------------
# main() / CLI plumbing
# ---------------------------------------------------------------------------

def test_main_returns_0_and_prints_pass_for_good_agent(tmp_path, capsys, monkeypatch):
    agents_dir = tmp_path
    _write_agent_md(agents_dir, "cliagent", VALID_FRONTMATTER, VALID_BODY_SECTIONS)
    _write_meta(
        agents_dir, "cliagent",
        evals=VALID_EVAL_YAML, redteam=VALID_REDTEAM_YAML, version=VALID_VERSION_JSON,
        eval_results=_all_pass_eval_results_json(),
    )
    monkeypatch.setattr(sys, "argv", ["agent_gate.py", "check", "--agents-dir", str(agents_dir), "--agent-name", "cliagent"])
    ret = agent_gate.main()
    assert ret == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_main_returns_1_for_blocked_agent(tmp_path, capsys, monkeypatch):
    agents_dir = tmp_path
    monkeypatch.setattr(sys, "argv", ["agent_gate.py", "check", "--agents-dir", str(agents_dir), "--agent-name", "missing-agent"])
    ret = agent_gate.main()
    assert ret == 1
    out = capsys.readouterr().out
    assert "BLOCKED" in out


def test_main_requires_a_subcommand(monkeypatch):
    # add_subparsers(..., required=True): omitting "check" entirely must be
    # a hard CLI usage error (argparse exits via SystemExit), not a silent
    # no-op.
    monkeypatch.setattr(sys, "argv", ["agent_gate.py"])
    with pytest.raises(SystemExit):
        agent_gate.main()


def test_main_requires_agents_dir_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agent_gate.py", "check", "--agent-name", "someagent"])
    with pytest.raises(SystemExit):
        agent_gate.main()


def test_main_requires_agent_name_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agent_gate.py", "check", "--agents-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        agent_gate.main()
