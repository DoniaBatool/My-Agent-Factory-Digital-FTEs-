import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("change_management_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_slugify():
    assert tool.slugify("Add Priority Field!") == "add-priority-field"


def test_next_change_number_starts_at_one(tmp_path):
    assert tool.next_change_number(tmp_path / "changes") == 1


def test_next_change_number_increments_past_existing(tmp_path):
    root = tmp_path / "changes"
    (root / "001-first").mkdir(parents=True)
    (root / "002-second").mkdir(parents=True)
    assert tool.next_change_number(root) == 3


def test_create_change_spec_writes_three_files(tmp_path):
    folder = tool.create_change_spec(tmp_path / "changes", "Add priority", "add column", "users need it")
    assert (folder / "spec.md").exists()
    assert (folder / "plan.md").exists()
    assert (folder / "tasks.md").exists()
    assert "add column" in (folder / "spec.md").read_text()


def test_create_change_spec_numbers_sequentially(tmp_path):
    root = tmp_path / "changes"
    f1 = tool.create_change_spec(root, "First change", "x", "y")
    f2 = tool.create_change_spec(root, "Second change", "x", "y")
    assert f1.name.startswith("001-")
    assert f2.name.startswith("002-")


def test_scan_impact_finds_only_matching_files(tmp_path):
    (tmp_path / "a.py").write_text("priority = 1")
    (tmp_path / "b.py").write_text("nothing here")
    (tmp_path / "c.txt").write_text("priority mentioned but wrong extension")
    hits = tool.scan_impact(tmp_path, "priority")
    assert hits == ["a.py"]


def test_build_rollback_note_includes_migration_and_flag_when_given():
    steps = tool.build_rollback_note("x", migration_name="0001_x", feature_flag="new_x")
    assert any("0001_x" in s for s in steps)
    assert any("new_x" in s for s in steps)


def test_build_rollback_note_always_includes_revert_step():
    steps = tool.build_rollback_note("simple change")
    assert any("Revert" in s for s in steps)


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import os
import subprocess
import sys
from pathlib import Path as _P
from types import SimpleNamespace
import pytest


def test_slugify_collapses_repeated_punctuation_and_strips_edges():
    assert tool.slugify("--Add!!  Priority---Field--") == "add-priority-field"


def test_slugify_empty_string_returns_empty():
    assert tool.slugify("") == ""


def test_next_change_number_ignores_folders_without_numeric_prefix(tmp_path):
    root = tmp_path / "changes"
    (root / "no-number-here").mkdir(parents=True)
    (root / "002-second").mkdir(parents=True)
    assert tool.next_change_number(root) == 3


def test_create_change_spec_uses_custom_non_goals(tmp_path):
    folder = tool.create_change_spec(tmp_path / "changes", "Feature", "what", "why", non_goals=["not this", "not that"])
    content = (folder / "spec.md").read_text()
    assert "- not this" in content
    assert "- not that" in content


def test_create_change_spec_default_non_goals_placeholder(tmp_path):
    folder = tool.create_change_spec(tmp_path / "changes", "Feature", "what", "why")
    content = (folder / "spec.md").read_text()
    assert "(none specified)" in content


def test_create_change_spec_plan_and_tasks_content(tmp_path):
    folder = tool.create_change_spec(tmp_path / "changes", "Feature", "what", "why")
    assert "Impacted areas" in (folder / "plan.md").read_text()
    tasks = (folder / "tasks.md").read_text()
    assert "Implement change" in tasks
    assert "Update tests" in tasks
    assert "Update docs" in tasks


def test_scan_impact_matches_across_supported_extensions(tmp_path):
    (tmp_path / "a.ts").write_text("priority")
    (tmp_path / "b.tsx").write_text("priority")
    (tmp_path / "c.js").write_text("priority")
    (tmp_path / "d.md").write_text("priority")
    (tmp_path / "e.rb").write_text("priority")
    hits = tool.scan_impact(tmp_path, "priority")
    assert hits == ["a.ts", "b.tsx", "c.js", "d.md"]


def test_scan_impact_with_custom_extensions_argument(tmp_path):
    (tmp_path / "a.rb").write_text("priority")
    (tmp_path / "b.py").write_text("priority")
    hits = tool.scan_impact(tmp_path, "priority", extensions=(".rb",))
    assert hits == ["a.rb"]


def test_scan_impact_returns_sorted_results(tmp_path):
    (tmp_path / "z.py").write_text("priority")
    (tmp_path / "a.py").write_text("priority")
    (tmp_path / "m.py").write_text("priority")
    hits = tool.scan_impact(tmp_path, "priority")
    assert hits == sorted(hits)
    assert hits == ["a.py", "m.py", "z.py"]


def test_scan_impact_skips_unreadable_file_without_crashing(tmp_path):
    readable = tmp_path / "ok.py"
    readable.write_text("priority")
    blocked = tmp_path / "blocked.py"
    blocked.write_text("priority")
    os.chmod(blocked, 0o000)
    try:
        hits = tool.scan_impact(tmp_path, "priority")
    finally:
        os.chmod(blocked, 0o644)
    # Root can read a 0o000 file, so only assert the readable one is
    # present and the call didn't raise -- the important behavior under
    # test is that an OSError never propagates out of scan_impact.
    assert "ok.py" in hits


def test_build_rollback_note_feature_flag_only_orders_before_revert():
    steps = tool.build_rollback_note("x", feature_flag="new_x")
    assert steps[0] == "Disable feature flag 'new_x'"
    assert steps[1] == "Revert the commit(s) implementing 'x'"


def test_build_rollback_note_migration_only_orders_before_revert():
    steps = tool.build_rollback_note("x", migration_name="0001_x")
    assert steps[0] == "Run downgrade for migration '0001_x'"
    assert steps[1] == "Revert the commit(s) implementing 'x'"


def test_build_rollback_note_neither_migration_nor_flag_is_just_revert():
    steps = tool.build_rollback_note("x")
    assert steps == ["Revert the commit(s) implementing 'x'"]


def test_cmd_create_change_spec_prints_created_path(tmp_path, capsys):
    args = SimpleNamespace(
        changes_root=str(tmp_path / "changes"), feature="My Feature", what="what", why="why", non_goals=None,
    )
    rc = tool.cmd_create_change_spec(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created" in out
    assert "001-my-feature" in out


def test_cmd_create_change_spec_splits_non_goals_on_semicolon(tmp_path):
    args = SimpleNamespace(
        changes_root=str(tmp_path / "changes"), feature="Feature", what="w", why="y", non_goals="a;b;c",
    )
    tool.cmd_create_change_spec(args)
    spec = (tmp_path / "changes" / "001-feature" / "spec.md").read_text()
    assert "- a" in spec and "- b" in spec and "- c" in spec


def test_cmd_scan_impact_no_hits_prints_message(tmp_path, capsys):
    args = SimpleNamespace(project_root=str(tmp_path), term="nope")
    rc = tool.cmd_scan_impact(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "No references to 'nope' found" in out


def test_cmd_scan_impact_with_hits_prints_each_indented(tmp_path, capsys):
    (tmp_path / "a.py").write_text("priority")
    args = SimpleNamespace(project_root=str(tmp_path), term="priority")
    rc = tool.cmd_scan_impact(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "  a.py" in out


def test_cmd_rollback_note_prints_json(capsys):
    args = SimpleNamespace(change_name="x", migration=None, feature_flag=None)
    rc = tool.cmd_rollback_note(args)
    out = capsys.readouterr().out
    steps = json.loads(out)
    assert rc == 0
    assert steps == ["Revert the commit(s) implementing 'x'"]


def test_cmd_test_returns_zero_and_prints_pass(capsys):
    rc = tool.cmd_test(SimpleNamespace())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_dispatches_create_change_spec_end_to_end(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "create-change-spec", "--changes-root", str(tmp_path / "changes"),
         "--feature", "Feature", "--what", "w", "--why", "y"],
    )
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created" in out


def test_main_dispatches_scan_impact_end_to_end_using_default_project_root(monkeypatch, capsys, tmp_path):
    (tmp_path / "a.py").write_text("priority")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-impact", "--term", "priority"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.py" in out


def test_main_dispatches_rollback_note_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "rollback-note", "--change-name", "x"])
    rc = tool.main()
    out = capsys.readouterr().out
    steps = json.loads(out)
    assert rc == 0
    assert steps == ["Revert the commit(s) implementing 'x'"]


def test_main_dispatches_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage" in captured.out.lower()


def test_main_create_change_spec_missing_required_feature_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-change-spec", "--what", "w", "--why", "y"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_change_spec_missing_required_what_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-change-spec", "--feature", "f", "--why", "y"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_create_change_spec_missing_required_why_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-change-spec", "--feature", "f", "--what", "w"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_scan_impact_missing_required_term_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-impact"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_rollback_note_missing_required_change_name_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "rollback-note"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    script = _P(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([sys.executable, str(script), "test"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "SELF-TEST PASS" in proc.stdout


def test_create_change_spec_creates_missing_intermediate_directories(tmp_path):
    # changes_root's own parent doesn't exist yet -- this only succeeds if
    # changes_root.mkdir is called with parents=True.
    root = tmp_path / "deeply" / "nested" / "changes"
    folder = tool.create_change_spec(root, "Feature", "w", "y")
    assert folder.exists()
    assert folder.parent == root
