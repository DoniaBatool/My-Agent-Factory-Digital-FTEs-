import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("new_feature_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_parse_acceptance_criteria_from_bullets():
    result = tool.parse_acceptance_criteria("- one\n- two\n")
    assert result == ["one", "two"]


def test_parse_acceptance_criteria_from_numbered_list():
    result = tool.parse_acceptance_criteria("1. first\n2. second\n")
    assert result == ["first", "second"]


def test_parse_acceptance_criteria_falls_back_to_sentences():
    result = tool.parse_acceptance_criteria("Users can log in. Errors are shown clearly.")
    assert result == ["Users can log in.", "Errors are shown clearly."]


def test_parse_acceptance_criteria_never_empty_for_nonempty_description():
    assert tool.parse_acceptance_criteria("just one plain sentence with no punctuation") != []


def test_scaffold_feature_creates_three_files(tmp_path):
    folder = tool.scaffold_feature(tmp_path, "My Feature", "- does a thing")
    assert (folder / "spec.md").exists()
    assert (folder / "plan.md").exists()
    assert (folder / "tasks.md").exists()


def test_scaffold_feature_slugifies_folder_name(tmp_path):
    folder = tool.scaffold_feature(tmp_path, "My Cool Feature!", "desc")
    assert folder.name == "my-cool-feature"


def test_scaffold_feature_tasks_mirror_acceptance_criteria(tmp_path):
    folder = tool.scaffold_feature(tmp_path, "Feature X", "- criterion one\n- criterion two")
    tasks_text = (folder / "tasks.md").read_text()
    assert "criterion one" in tasks_text
    assert "criterion two" in tasks_text


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys as _sys
import pytest


def test_slugify_collapses_multiple_special_chars_and_strips_edges():
    assert tool.slugify("  Hello!!  World__Foo  ") == "hello-world-foo"


def test_slugify_empty_string_yields_empty_string():
    assert tool.slugify("") == ""


def test_parse_acceptance_criteria_empty_description_returns_empty_list():
    assert tool.parse_acceptance_criteria("") == []


def test_parse_acceptance_criteria_mixed_bullets_and_numbers_both_captured():
    result = tool.parse_acceptance_criteria("- first\n2. second\n* third\n")
    assert result == ["first", "second", "third"]


def test_parse_acceptance_criteria_ignores_blank_lines_between_bullets():
    result = tool.parse_acceptance_criteria("- one\n\n\n- two\n")
    assert result == ["one", "two"]


def test_scaffold_feature_uses_explicit_acceptance_criteria_over_parsed_ones(tmp_path):
    folder = tool.scaffold_feature(
        tmp_path, "Feature Y", "- ignored bullet",
        acceptance_criteria=["explicit one", "explicit two"],
    )
    spec_text = (folder / "spec.md").read_text()
    tasks_text = (folder / "tasks.md").read_text()
    assert "- [ ] explicit one" in spec_text
    assert "- [ ] ignored bullet" not in spec_text
    assert "Implement: explicit one" in tasks_text
    assert "Implement: ignored bullet" not in tasks_text


def test_scaffold_feature_with_no_criteria_defaults_tasks_to_implement_feature(tmp_path):
    folder = tool.scaffold_feature(tmp_path, "Bare Feature", "")
    tasks_text = (folder / "tasks.md").read_text()
    assert "Implement feature" in tasks_text


def test_scaffold_feature_plan_contains_tbd_sections(tmp_path):
    folder = tool.scaffold_feature(tmp_path, "Feature Z", "- a thing")
    plan_text = (folder / "plan.md").read_text()
    assert "Architecture changes" in plan_text
    assert "Rollout/rollback" in plan_text


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_cmd_scaffold_prints_created_folder_and_file_list(tmp_path, capsys):
    args = _Args(features_root=str(tmp_path), name="CLI Feature", description="- does x")
    rc = tool.cmd_scaffold(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created" in out
    assert "spec.md" in out
    assert "plan.md" in out
    assert "tasks.md" in out


def test_cmd_parse_acceptance_criteria_prints_json_list(capsys):
    args = _Args(description="- a\n- b")
    rc = tool.cmd_parse_acceptance_criteria(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out) == ["a", "b"]


def test_cmd_test_self_test_passes(capsys):
    args = _Args()
    rc = tool.cmd_test(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_scaffold_end_to_end(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "scaffold", "--features-root", str(tmp_path),
        "--name", "End To End", "--description", "- works",
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "end-to-end" in out
    assert (tmp_path / "end-to-end" / "spec.md").exists()


def test_main_scaffold_uses_default_features_root(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "scaffold", "--name", "Def Root", "--description", "d"])
    rc = tool.main()
    capsys.readouterr()
    assert rc == 0
    assert (tmp_path / "features" / "def-root" / "spec.md").exists()


def test_main_parse_acceptance_criteria_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "parse-acceptance-criteria", "- x\n- y"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out) == ["x", "y"]


def test_main_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_scaffold_missing_required_name_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "scaffold", "--description", "d"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_scaffold_missing_required_description_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "scaffold", "--name", "x"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_parse_acceptance_criteria_missing_positional_description_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "parse-acceptance-criteria"])
    with pytest.raises(SystemExit):
        tool.main()


def test_cli_subprocess_smoke_test_runs_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "parse-acceptance-criteria", "- a\n- b"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == ["a", "b"]


def test_cli_subprocess_smoke_test_scaffold_writes_files(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "scaffold", "--features-root", str(tmp_path),
         "--name", "Sub Proc", "--description", "- z"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert (tmp_path / "sub-proc" / "spec.md").exists()
