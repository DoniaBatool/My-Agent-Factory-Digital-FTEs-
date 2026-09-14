import json
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("skill_learner_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_find_skill_for_issue_matches_jwt():
    assert tool.find_skill_for_issue("JWT token expired but no refresh") == ["jwt-authentication"]


def test_find_skill_for_issue_matches_multiword_keyword_over_substring():
    result = tool.find_skill_for_issue("found an edge case in date handling, need more test coverage")
    assert result[0] == "edge-case-tester"  # "edge case" (longer) beats bare "test"


def test_find_skill_for_issue_returns_empty_for_unrelated_text():
    assert tool.find_skill_for_issue("the sky is blue today") == []


def test_capture_learning_records_all_fields():
    learning = tool.capture_learning("issue-x", "cause-x", "fix-x", "edge-x", "test-x")
    assert learning["issue"] == "issue-x"
    assert learning["fix"] == "fix-x"
    assert "captured_at" in learning


def test_append_learning_log_accumulates_entries(tmp_path):
    log_path = tmp_path / "log.json"
    tool.append_learning_log(log_path, tool.capture_learning("a", "b", "c"))
    tool.append_learning_log(log_path, tool.capture_learning("d", "e", "f"))
    entries = json.loads(log_path.read_text())
    assert len(entries) == 2
    assert entries[1]["issue"] == "d"


def test_stage_skill_copies_live_dir_without_touching_it(tmp_path):
    skills_root = tmp_path / "skills"
    live = skills_root / "demo-skill"
    (live / "scripts").mkdir(parents=True)
    (live / "scripts" / "tool.py").write_text("# original\n")

    staged = tool.stage_skill("demo-skill", skills_root=skills_root)

    assert staged == skills_root / "demo-skill.staged"
    assert (staged / "scripts" / "tool.py").read_text() == "# original\n"
    assert (live / "scripts" / "tool.py").read_text() == "# original\n"  # live untouched


def test_stage_skill_raises_for_unknown_skill(tmp_path):
    try:
        tool.stage_skill("nonexistent", skills_root=tmp_path)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_stage_skill_overwrites_stale_staged_copy(tmp_path):
    skills_root = tmp_path / "skills"
    live = skills_root / "demo-skill"
    (live / "scripts").mkdir(parents=True)
    (live / "scripts" / "tool.py").write_text("# v1\n")
    tool.stage_skill("demo-skill", skills_root=skills_root)

    (live / "scripts" / "tool.py").write_text("# v2\n")
    staged = tool.stage_skill("demo-skill", skills_root=skills_root)
    assert (staged / "scripts" / "tool.py").read_text() == "# v2\n"
