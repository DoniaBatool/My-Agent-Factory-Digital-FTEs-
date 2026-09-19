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
