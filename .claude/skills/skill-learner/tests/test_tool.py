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


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_find_skill_for_issue_matches_multiple_keywords_in_priority_order():
    # "database" and "migration" both appear; "migration" (longer) should sort first
    result = tool.find_skill_for_issue("ran a database migration that failed")
    assert result[0] == "database-schema-expander"
    assert "database-engineer" in result


def test_find_skill_for_issue_is_case_insensitive():
    assert tool.find_skill_for_issue("JWT ISSUE with tokens") == ["jwt-authentication"]


def test_capture_learning_defaults_edge_case_and_test_case_to_empty_string():
    learning = tool.capture_learning("i", "c", "f")
    assert learning["edge_case"] == ""
    assert learning["test_case"] == ""


def test_append_learning_log_creates_parent_dirs(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "log.json"
    tool.append_learning_log(log_path, tool.capture_learning("a", "b", "c"))
    assert log_path.exists()
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1


def test_cmd_capture_learning_writes_log_and_prints_json(tmp_path, capsys):
    log_path = tmp_path / "log.json"
    args = _Args(issue="i1", root_cause="c1", fix="f1", edge_case="e1", test_case="t1", log=str(log_path))
    rc = tool.cmd_capture_learning(args)
    assert rc == 0
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1
    assert entries[0]["issue"] == "i1"
    printed = json.loads(capsys.readouterr().out)
    assert printed["fix"] == "f1"


def test_cmd_capture_learning_uses_default_log_when_none_given(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tool, "SKILLS_ROOT", tmp_path)
    args = _Args(issue="i2", root_cause="c2", fix="f2", edge_case=None, test_case=None, log=None)
    rc = tool.cmd_capture_learning(args)
    assert rc == 0
    default_log = tmp_path / "_framework" / "learning_log.json"
    assert default_log.exists()
    entries = json.loads(default_log.read_text())
    assert entries[0]["edge_case"] == ""
    assert entries[0]["test_case"] == ""


def test_cmd_find_skill_for_issue_prints_joined_skills_and_returns_0(capsys):
    args = _Args(issue="jwt token refresh bug")
    rc = tool.cmd_find_skill_for_issue(args)
    assert rc == 0
    assert capsys.readouterr().out.strip() == "jwt-authentication"


def test_cmd_find_skill_for_issue_prints_placeholder_and_returns_1_when_no_match(capsys):
    args = _Args(issue="completely unrelated text about weather")
    rc = tool.cmd_find_skill_for_issue(args)
    assert rc == 1
    assert "no matching skill found" in capsys.readouterr().out


def test_cmd_stage_skill_success_prints_next_steps(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tool, "SKILLS_ROOT", tmp_path)
    live = tmp_path / "demo-skill" / "scripts"
    live.mkdir(parents=True)
    (live / "tool.py").write_text("# v1\n")
    args = _Args(skill="demo-skill")
    rc = tool.cmd_stage_skill(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Staged copy ready at" in out
    assert "skill_gate.py promote --skill demo-skill" in out
    assert (tmp_path / "demo-skill.staged" / "scripts" / "tool.py").exists()


def test_cmd_stage_skill_missing_prints_error_and_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tool, "SKILLS_ROOT", tmp_path)
    args = _Args(skill="does-not-exist")
    rc = tool.cmd_stage_skill(args)
    assert rc == 1
    assert "no such skill: does-not-exist" in capsys.readouterr().out


def test_cmd_test_self_test_passes_and_prints_pass(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_capture_learning_end_to_end(monkeypatch, tmp_path, capsys):
    log_path = tmp_path / "log.json"
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "capture-learning",
        "--issue", "issue-e2e", "--root-cause", "cause-e2e", "--fix", "fix-e2e",
        "--log", str(log_path),
    ])
    rc = tool.main()
    assert rc == 0
    entries = json.loads(log_path.read_text())
    assert entries[0]["issue"] == "issue-e2e"


def test_main_find_skill_for_issue_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "find-skill-for-issue", "docker build is broken"])
    rc = tool.main()
    assert rc == 0
    assert "docker-expert" in capsys.readouterr().out


def test_main_stage_skill_end_to_end(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool, "SKILLS_ROOT", tmp_path)
    live = tmp_path / "demo-skill" / "scripts"
    live.mkdir(parents=True)
    (live / "tool.py").write_text("# v1\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "stage-skill", "demo-skill"])
    rc = tool.main()
    assert rc == 0
    assert (tmp_path / "demo-skill.staged").exists()


def test_main_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_capture_learning_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "capture-learning", "--issue", "only-issue"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()


def test_main_find_skill_for_issue_missing_positional_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "find-skill-for-issue"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()


def test_main_stage_skill_missing_positional_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "stage-skill"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_runs_as_script_and_hits_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "test"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "SELF-TEST PASS" in result.stdout


def test_subprocess_no_args_exits_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1


def test_main_capture_learning_missing_only_issue_exits(monkeypatch):
    # supplies --root-cause and --fix but omits --issue specifically, so this
    # test can only pass if --issue's required=True is intact (kills a
    # mutant that flips just --issue to optional while the others stay required).
    monkeypatch.setattr(sys, "argv", ["tool.py", "capture-learning", "--root-cause", "rc", "--fix", "fx"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()


def test_main_capture_learning_missing_only_root_cause_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "capture-learning", "--issue", "iss", "--fix", "fx"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()


def test_main_capture_learning_missing_only_fix_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "capture-learning", "--issue", "iss", "--root-cause", "rc"])
    import pytest
    with pytest.raises(SystemExit):
        tool.main()
