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
