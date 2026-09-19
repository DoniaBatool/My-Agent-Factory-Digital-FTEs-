import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("prompt_analyzer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_detect_intent_single_match():
    assert tool.detect_intent("Please create a new chatbot endpoint") == ["create"]


def test_detect_intent_multiple_matches():
    intents = tool.detect_intent("Fix this bug and add tests before we deploy")
    assert {"debug", "test", "deploy"} <= set(intents)  # "add" also legitimately implies create


def test_detect_intent_unknown_when_nothing_matches():
    assert tool.detect_intent("hello there") == ["unknown"]


def test_extract_keywords_finds_known_terms():
    keywords = tool.extract_keywords("Add JWT auth and a login flow with password hashing")
    assert "jwt" in keywords
    assert "password" in keywords
    assert "login" in keywords


def test_extract_keywords_prefers_longer_match_over_substring():
    keywords = tool.extract_keywords("write an edge case test for this")
    assert "edge case" in keywords


def test_map_to_skills_deduplicates_and_preserves_order():
    skills = tool.map_to_skills(["auth", "login"])
    assert skills[0] == "jwt-authentication"
    assert skills.count("jwt-authentication") == 1
    assert "password-security" in skills


def test_build_execution_plan_shape():
    plan = tool.build_execution_plan("Add JWT authentication to the API")
    assert plan["prompt"] == "Add JWT authentication to the API"
    assert "create" in plan["intents"]
    assert "jwt-authentication" in plan["skills"]


def test_map_to_skills_empty_for_unknown_keywords():
    assert tool.map_to_skills(["totally-unknown-keyword"]) == []

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess as _subprocess
import pytest


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_detect_intent_word_boundary_prevents_substring_false_positive():
    # "recreate" contains the substring "create" but \bcreate\b must not
    # match inside a larger word.
    assert tool.detect_intent("recreate the sandbox") == ["unknown"]


def test_detect_intent_matches_both_optimise_and_optimize_spellings():
    assert "optimize" in tool.detect_intent("please optimise this function")
    assert "optimize" in tool.detect_intent("please optimize this function")


def test_detect_intent_matches_not_working_phrase():
    assert "debug" in tool.detect_intent("the login is not working")


def test_detect_intent_empty_string_returns_unknown():
    assert tool.detect_intent("") == ["unknown"]


def test_extract_keywords_is_case_insensitive():
    assert "jwt" in tool.extract_keywords("Set Up JWT Auth")


def test_extract_keywords_empty_string_returns_empty_list():
    assert tool.extract_keywords("") == []


def test_build_execution_plan_empty_prompt_has_no_intents_keywords_or_skills():
    plan = tool.build_execution_plan("")
    assert plan["intents"] == ["unknown"]
    assert plan["keywords"] == []
    assert plan["skills"] == []


def test_cmd_analyze_returns_0_when_skills_found(capsys):
    rc = tool.cmd_analyze(_Args(prompt="Add JWT auth"))
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_cmd_analyze_returns_0_when_intent_known_but_no_skills():
    # "analyze" is a recognized intent but has no keyword->skill mapping,
    # so skills is empty yet the function must still report success because
    # intents != ["unknown"].
    plan = tool.build_execution_plan("please analyze this codebase")
    assert plan["skills"] == []
    assert plan["intents"] != ["unknown"]
    rc = tool.cmd_analyze(_Args(prompt="please analyze this codebase"))
    assert rc == 0


def test_cmd_analyze_returns_1_when_unknown_and_no_skills(capsys):
    rc = tool.cmd_analyze(_Args(prompt="hello there"))
    assert rc == 1
    assert '"unknown"' in capsys.readouterr().out


def test_cmd_detect_intent_prints_joined_intents(capsys):
    rc = tool.cmd_detect_intent(_Args(prompt="fix this bug"))
    assert rc == 0
    assert "debug" in capsys.readouterr().out


def test_cmd_extract_keywords_prints_none_placeholder_when_empty(capsys):
    rc = tool.cmd_extract_keywords(_Args(prompt="nothing matches here"))
    assert rc == 0
    assert "(none)" in capsys.readouterr().out


def test_cmd_extract_keywords_prints_joined_keywords(capsys):
    rc = tool.cmd_extract_keywords(_Args(prompt="set up jwt auth"))
    assert rc == 0
    assert "jwt" in capsys.readouterr().out


def test_cmd_map_skills_uses_explicit_keywords_arg(capsys):
    rc = tool.cmd_map_skills(_Args(keywords="auth,login", prompt=None))
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_cmd_map_skills_strips_whitespace_in_explicit_keywords(capsys):
    rc = tool.cmd_map_skills(_Args(keywords=" auth , login ", prompt=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "jwt-authentication" in out
    assert "password-security" in out


def test_cmd_map_skills_falls_back_to_prompt_extraction_when_no_keywords_arg(capsys):
    rc = tool.cmd_map_skills(_Args(keywords=None, prompt="set up jwt auth"))
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_cmd_map_skills_prompt_and_keywords_both_none_prints_placeholder(capsys):
    rc = tool.cmd_map_skills(_Args(keywords=None, prompt=None))
    assert rc == 0
    assert "(no mapped skills)" in capsys.readouterr().out


def test_cmd_test_self_test_passes_by_default(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_cmd_test_reports_fail_when_selftest_assertion_fails(monkeypatch, capsys):
    monkeypatch.setattr(
        tool, "build_execution_plan",
        lambda prompt: {"prompt": prompt, "intents": ["unknown"], "keywords": [], "skills": []},
    )
    rc = tool.cmd_test(_Args())
    assert rc == 1
    assert "SELF-TEST FAIL" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_analyze_requires_prompt_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "analyze"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_detect_intent_requires_prompt_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "detect-intent"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_extract_keywords_requires_prompt_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "extract-keywords"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_analyze_end_to_end_success(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "analyze", "Add JWT auth"])
    rc = tool.main()
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_main_analyze_end_to_end_unknown_returns_1(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "analyze", "hello there"])
    rc = tool.main()
    assert rc == 1


def test_main_detect_intent_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "detect-intent", "please create a new thing"])
    rc = tool.main()
    assert rc == 0
    assert "create" in capsys.readouterr().out


def test_main_extract_keywords_end_to_end_none_found(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "extract-keywords", "no matching terms here"])
    rc = tool.main()
    assert rc == 0
    assert "(none)" in capsys.readouterr().out


def test_main_map_skills_end_to_end_with_prompt(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "map-skills", "set up jwt auth"])
    rc = tool.main()
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_main_map_skills_end_to_end_with_explicit_keywords(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "map-skills", "--keywords", "auth, login"])
    rc = tool.main()
    assert rc == 0
    assert "jwt-authentication" in capsys.readouterr().out


def test_main_map_skills_no_args_prints_placeholder(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "map-skills"])
    rc = tool.main()
    assert rc == 0
    assert "(no mapped skills)" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_script_runs_as_main_via_subprocess():
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run(
        [sys.executable, script, "detect-intent", "create a new feature"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "create" in result.stdout


def test_extract_keywords_orders_longest_keyword_before_shorter_substring():
    """Regression for the ordering the docstring promises: 'edge case' must
    be listed before the shorter 'test' keyword it overlaps with, not just
    be present somewhere in the list."""
    keywords = tool.extract_keywords("write an edge case test for this")
    assert "edge case" in keywords and "test" in keywords
    assert keywords.index("edge case") < keywords.index("test")
