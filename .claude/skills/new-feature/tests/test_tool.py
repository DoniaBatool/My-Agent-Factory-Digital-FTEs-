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
