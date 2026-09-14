"""
Fixed regression tests for skill_gate.py itself.

These tests are the baseline the gate's own future changes get checked
against -- if someone "improves" skill_gate.py in a way that lets a weaker
skill through, one of these should fail.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skill_gate  # noqa: E402


def _make_skill(root: Path, name: str, test_body: str, version="1.0.0"):
    skill_dir = root / name
    (skill_dir / "tests").mkdir(parents=True)
    (skill_dir / "tool.py").write_text("# placeholder tool\n")
    (skill_dir / "version.json").write_text(json.dumps({"version": version, "history": []}))
    (skill_dir / "tests" / "test_tool.py").write_text(test_body)
    return skill_dir


GOOD_TESTS = """
def test_one():
    assert 1 + 1 == 2

def test_two():
    assert "a" + "b" == "ab"
"""

REGRESSED_TESTS = """
def test_one():
    assert 1 + 1 == 2

def test_two():
    assert False, "this used to pass, now it does not"
"""

SHRUNK_TESTS = """
def test_one():
    assert 1 + 1 == 2
"""

IMPROVED_TESTS = """
def test_one():
    assert 1 + 1 == 2

def test_two():
    assert "a" + "b" == "ab"

def test_three_new_edge_case():
    assert len([]) == 0
"""


def test_gate_rejects_when_staged_suite_deletes_a_baseline_test(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_gate, "SKILLS_ROOT", tmp_path)
    _make_skill(tmp_path, "demo-skill", GOOD_TESTS)
    staged = tmp_path / "demo-skill.staged"
    (staged / "tests").mkdir(parents=True)
    (staged / "tool.py").write_text("# weaker tool\n")
    (staged / "tests" / "test_tool.py").write_text(SHRUNK_TESTS)

    rc = skill_gate.promote("demo-skill", staged, reason="test")

    assert rc == 1
    live_version = json.loads((tmp_path / "demo-skill" / "version.json").read_text())
    assert live_version["version"] == "1.0.0"  # unchanged
    assert (tmp_path / "_archive" / "demo-skill" / "REJECTED.log").exists()


def test_gate_rejects_when_a_previously_passing_test_now_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_gate, "SKILLS_ROOT", tmp_path)
    _make_skill(tmp_path, "demo-skill", GOOD_TESTS)
    staged = tmp_path / "demo-skill.staged"
    (staged / "tests").mkdir(parents=True)
    (staged / "tool.py").write_text("# regressed tool\n")
    (staged / "tests" / "test_tool.py").write_text(REGRESSED_TESTS)

    rc = skill_gate.promote("demo-skill", staged, reason="test")

    assert rc == 1
    live_version = json.loads((tmp_path / "demo-skill" / "version.json").read_text())
    assert live_version["version"] == "1.0.0"


def test_gate_promotes_when_all_baseline_tests_still_pass_and_new_ones_are_added(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_gate, "SKILLS_ROOT", tmp_path)
    _make_skill(tmp_path, "demo-skill", GOOD_TESTS)
    staged = tmp_path / "demo-skill.staged"
    (staged / "tests").mkdir(parents=True)
    (staged / "tool.py").write_text("# improved tool\n")
    (staged / "tests" / "test_tool.py").write_text(IMPROVED_TESTS)

    rc = skill_gate.promote("demo-skill", staged, bump_part="minor", reason="test")

    assert rc == 0
    live_version = json.loads((tmp_path / "demo-skill" / "version.json").read_text())
    assert live_version["version"] == "1.1.0"
    assert (tmp_path / "_archive" / "demo-skill" / f"v1.0.0-{live_version['history'][-1]['date']}").exists()
    assert (tmp_path / "demo-skill" / "CHANGELOG.md").exists()


def test_bump_helper():
    assert skill_gate.bump("1.2.3", "patch") == "1.2.4"
    assert skill_gate.bump("1.2.3", "minor") == "1.3.0"
    assert skill_gate.bump("1.2.3", "major") == "2.0.0"

def test_gate_rejects_staged_copy_that_accidentally_drops_a_live_file(tmp_path, monkeypatch):
    """Regression test for a real near-miss during this framework's own
    rollout: a staged copy was hand-built by cherry-picking SKILL.md +
    scripts/ and silently dropped a pre-existing README.md."""
    monkeypatch.setattr(skill_gate, "SKILLS_ROOT", tmp_path)
    live = _make_skill(tmp_path, "demo-skill", GOOD_TESTS)
    (live / "README.md").write_text("important pre-existing docs")

    staged = tmp_path / "demo-skill.staged"
    (staged / "tests").mkdir(parents=True)
    (staged / "tool.py").write_text("# improved tool\n")
    (staged / "tests" / "test_tool.py").write_text(IMPROVED_TESTS)
    # README.md deliberately NOT copied into staged -- this must be caught

    rc = skill_gate.promote("demo-skill", staged, reason="test")

    assert rc == 1
    assert (live / "README.md").exists()  # live untouched
    live_version = json.loads((tmp_path / "demo-skill" / "version.json").read_text())
    assert live_version["version"] == "1.0.0"


def test_gate_allows_promotion_when_file_removal_is_explicitly_acknowledged(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_gate, "SKILLS_ROOT", tmp_path)
    live = _make_skill(tmp_path, "demo-skill", GOOD_TESTS)
    (live / "OLD_NOTES.md").write_text("stale notes, fine to remove")

    staged = tmp_path / "demo-skill.staged"
    (staged / "tests").mkdir(parents=True)
    (staged / "tool.py").write_text("# improved tool\n")
    (staged / "tests" / "test_tool.py").write_text(IMPROVED_TESTS)

    rc = skill_gate.promote("demo-skill", staged, reason="test", allow_file_removal=True)

    assert rc == 0
