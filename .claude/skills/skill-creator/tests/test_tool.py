import os
import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "skill_creator_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"


# --------------------------------------------------------------------------
# print helpers
# --------------------------------------------------------------------------

def test_print_success_prints_message_with_checkmark(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "all good" in out
    assert "✓" in out  # checkmark


def test_print_error_prints_message_with_x(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "bad thing" in out
    assert "✗" in out


def test_print_warning_prints_message_with_warn_symbol(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert "careful" in out
    assert "⚠" in out


def test_print_info_prints_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_prints_arrow_prefixed_message(capsys):
    tool.print_header("Section")
    out = capsys.readouterr().out
    assert "==> Section" in out


# --------------------------------------------------------------------------
# run_command
# --------------------------------------------------------------------------

def test_run_command_success_returns_code_and_stdout():
    code, out, err = tool.run_command("echo hello")
    assert code == 0
    assert out.strip() == "hello"
    assert err == ""


def test_run_command_nonzero_exit_returns_code():
    code, out, err = tool.run_command("exit 3")
    assert code == 3


def test_run_command_bad_input_hits_except_and_returns_1():
    # cmd=None makes subprocess.run raise, exercising the bare except branch
    code, out, err = tool.run_command(None)
    assert code == 1
    assert out == ""
    assert err == "Error"


# --------------------------------------------------------------------------
# create_new_skill
# --------------------------------------------------------------------------

def test_create_new_skill_creates_full_structure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(name="my-cool-skill")

    rc = tool.create_new_skill(args)

    assert rc == 0
    skill_dir = tmp_path / ".claude" / "skills" / "my-cool-skill"
    assert skill_dir.is_dir()
    assert (skill_dir / "scripts").is_dir()

    tool_py = skill_dir / "scripts" / "tool.py"
    assert tool_py.exists()
    assert os.access(tool_py, os.X_OK)

    content = tool_py.read_text()
    assert "My Cool Skill Tool" in content
    assert "def check_prerequisites(args):" in content
    assert "def run_tests(args):" in content
    assert "def main():" in content
    compile(content, str(tool_py), "exec")  # generated file must be syntactically valid

    skill_md = (skill_dir / "SKILL.md").read_text()
    assert skill_md.startswith("---\nname: my-cool-skill\n")
    assert "# My Cool Skill" in skill_md

    readme = (skill_dir / "README.md").read_text()
    assert readme.startswith("---\nname: my-cool-skill\n")
    assert "Last Updated:" in readme

    out = capsys.readouterr().out
    assert "Creating New Skill: my-cool-skill" in out
    assert "Next Steps" in out


def test_create_new_skill_already_exists_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "dupe"
    skill_dir.mkdir(parents=True)

    rc = tool.create_new_skill(_Args(name="dupe"))

    assert rc == 1
    out = capsys.readouterr().out
    assert "Skill already exists: dupe" in out
    assert "upgrade-existing-skill" in out


def test_create_new_skill_title_cases_multiword_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_new_skill(_Args(name="foo-bar-baz"))
    tool_py = tmp_path / ".claude" / "skills" / "foo-bar-baz" / "scripts" / "tool.py"
    assert "Foo Bar Baz Tool" in tool_py.read_text()


def test_create_new_skill_generated_tool_runs_check_prerequisites(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_new_skill(_Args(name="runnable-skill"))
    tool_py = tmp_path / ".claude" / "skills" / "runnable-skill" / "scripts" / "tool.py"

    result = subprocess.run(
        [sys.executable, str(tool_py), "check-prerequisites"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Prerequisites OK" in result.stdout


def test_create_new_skill_generated_tool_runs_test_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_new_skill(_Args(name="runnable-skill-2"))
    tool_py = tmp_path / ".claude" / "skills" / "runnable-skill-2" / "scripts" / "tool.py"

    result = subprocess.run(
        [sys.executable, str(tool_py), "test"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "All tests passed" in result.stdout


def test_create_new_skill_generated_tool_no_args_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool.create_new_skill(_Args(name="runnable-skill-3"))
    tool_py = tmp_path / ".claude" / "skills" / "runnable-skill-3" / "scripts" / "tool.py"

    result = subprocess.run(
        [sys.executable, str(tool_py)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()


# --------------------------------------------------------------------------
# upgrade_existing_skill
# --------------------------------------------------------------------------

def test_upgrade_skill_not_found_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.upgrade_existing_skill(_Args(name="nope", commands=None))
    assert rc == 1
    assert "Skill not found: nope" in capsys.readouterr().out


def test_upgrade_skill_already_has_tool_py_skips(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "existing"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "scripts" / "tool.py").write_text("# already here\n")

    rc = tool.upgrade_existing_skill(_Args(name="existing", commands=None))

    assert rc == 0
    assert "Skipping upgrade (already expert-level)" in capsys.readouterr().out
    # must not have been overwritten
    assert (skill_dir / "scripts" / "tool.py").read_text() == "# already here\n"


def test_upgrade_skill_missing_skill_md_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "nomd"
    skill_dir.mkdir(parents=True)

    rc = tool.upgrade_existing_skill(_Args(name="nomd", commands=None))

    assert rc == 1
    assert "SKILL.md not found" in capsys.readouterr().out


def test_upgrade_skill_default_commands_generates_eight_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: up1\n---\nSome content\n")

    rc = tool.upgrade_existing_skill(_Args(name="up1", commands=None))

    assert rc == 0
    tool_py = skill_dir / "scripts" / "tool.py"
    assert os.access(tool_py, os.X_OK)
    content = tool_py.read_text()
    compile(content, str(tool_py), "exec")

    default_cmds = [
        "check-prerequisites", "setup", "configure", "deploy",
        "test", "health-check", "troubleshoot", "cleanup",
    ]
    assert content.count("subparsers.add_parser(") == 8
    for cmd in default_cmds:
        assert f"subparsers.add_parser('{cmd}')" in content
    for cmd in default_cmds:
        func_name = cmd.replace('-', '_')
        assert f"def {func_name}(args):" in content
        assert f"'{cmd}': {func_name}," in content


def test_upgrade_skill_custom_commands_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up2"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: up2\n---\nbody\n")

    rc = tool.upgrade_existing_skill(_Args(name="up2", commands=["foo", "bar-baz"]))

    assert rc == 0
    content = (skill_dir / "scripts" / "tool.py").read_text()
    assert content.count("subparsers.add_parser(") == 2
    assert "def foo(args):" in content
    assert "def bar_baz(args):" in content
    assert "'foo': foo," in content
    assert "'bar-baz': bar_baz," in content


def test_upgrade_skill_inserts_notice_right_after_frontmatter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up3"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: up3\n---\nOriginal body line\n")

    tool.upgrade_existing_skill(_Args(name="up3", commands=None))

    updated = (skill_dir / "SKILL.md").read_text()
    assert "Expert-Level Automation (Upgraded)" in updated
    # the notice must land after the closing '---' and before the original body
    notice_pos = updated.index("Expert-Level Automation")
    body_pos = updated.index("Original body line")
    fm_close_pos = updated.index("---\n", updated.index("---\n") + 1)
    assert fm_close_pos < notice_pos < body_pos


def test_upgrade_skill_skips_notice_when_already_present(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up4"
    skill_dir.mkdir(parents=True)
    original = "---\nname: up4\n---\nAlready has Expert-Level Automation text\n"
    (skill_dir / "SKILL.md").write_text(original)

    rc = tool.upgrade_existing_skill(_Args(name="up4", commands=None))

    assert rc == 0
    assert "Updated SKILL.md with upgrade notice" not in capsys.readouterr().out
    assert (skill_dir / "SKILL.md").read_text() == original


def test_upgrade_skill_generated_tool_is_runnable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up5"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: up5\n---\nbody\n")
    tool.upgrade_existing_skill(_Args(name="up5", commands=["ping"]))

    tool_py = skill_dir / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(tool_py), "ping"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "ping complete" in result.stdout


# --------------------------------------------------------------------------
# validate_skill
# --------------------------------------------------------------------------

def test_validate_skill_not_found_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.validate_skill(_Args(name="ghost"))
    assert rc == 1
    assert "Skill not found: ghost" in capsys.readouterr().out


def test_validate_skill_missing_everything_reports_issues_and_warnings(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "bare"
    skill_dir.mkdir(parents=True)

    rc = tool.validate_skill(_Args(name="bare"))

    assert rc == 1
    out = capsys.readouterr().out
    assert "Issues found: 1" in out
    assert "SKILL.md not found" in out
    assert "Warnings: 2" in out
    assert "README.md not found (recommended)" in out
    assert "scripts/tool.py not found (documentation-only skill)" in out


def test_validate_skill_bad_frontmatter_flagged_as_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "badfm"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Not frontmatter\nTODO fill this in\n")

    rc = tool.validate_skill(_Args(name="badfm"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "SKILL.md missing YAML frontmatter" in out
    assert "SKILL.md contains TODO items" in out


def test_validate_skill_bad_readme_frontmatter_is_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "badreadme"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: badreadme\n---\nok\n")
    (skill_dir / "README.md").write_text("# no frontmatter here\n")

    rc = tool.validate_skill(_Args(name="badreadme"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "README.md missing YAML frontmatter" in out


def test_validate_skill_tool_not_executable_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "noexec"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: noexec\n---\nok\n")
    tool_py = skill_dir / "scripts" / "tool.py"
    tool_py.write_text(
        "subparsers.add_parser('a')\nsubparsers.add_parser('b')\n"
        "subparsers.add_parser('c')\nsubparsers.add_parser('d')\n"
    )
    os.chmod(tool_py, 0o644)

    rc = tool.validate_skill(_Args(name="noexec"))

    out = capsys.readouterr().out
    assert "scripts/tool.py not executable" in out
    # 4 commands is the recommended minimum, so no low-command-count warning
    assert "recommended: 4-8" not in out
    assert rc == 0  # only a warning, no issues


def test_validate_skill_low_command_count_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "fewcmds"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: fewcmds\n---\nok\n")
    tool_py = skill_dir / "scripts" / "tool.py"
    tool_py.write_text("subparsers.add_parser('a')\nsubparsers.add_parser('b')\n")
    os.chmod(tool_py, 0o755)

    rc = tool.validate_skill(_Args(name="fewcmds"))

    out = capsys.readouterr().out
    assert "Commands implemented: 2" in out
    assert "Only 2 commands (recommended: 4-8)" in out
    assert rc == 0


def test_validate_skill_fully_clean_is_production_ready(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "clean"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: clean\n---\nAll good, no todo markers.\n")
    (skill_dir / "README.md").write_text("---\nname: clean\n---\nQuick start\n")
    tool_py = skill_dir / "scripts" / "tool.py"
    tool_py.write_text(
        "".join(f"subparsers.add_parser('cmd{i}')\n" for i in range(5))
    )
    os.chmod(tool_py, 0o755)

    rc = tool.validate_skill(_Args(name="clean"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "No critical issues" in out
    assert "Skill is production-ready" in out
    assert "Issues found" not in out
    assert "Warnings:" not in out


def test_validate_skill_only_warnings_still_returns_0(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "warnonly"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: warnonly\n---\nno todos here\n")
    # no README, no tool.py -> warnings only, no issues

    rc = tool.validate_skill(_Args(name="warnonly"))

    assert rc == 0


# --------------------------------------------------------------------------
# list_skills
# --------------------------------------------------------------------------

def test_list_skills_missing_dir_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.list_skills(_Args(verbose=False))
    assert rc == 1
    assert "Skills directory not found" in capsys.readouterr().out


def test_list_skills_counts_expert_and_docs_and_excludes_hidden_and_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    alpha = skills_dir / "alpha"
    (alpha / "scripts").mkdir(parents=True)
    (alpha / "scripts" / "tool.py").write_text("# tool\n")
    (alpha / "SKILL.md").write_text("skill md\n")
    (alpha / "README.md").write_text("readme\n")

    beta = skills_dir / "beta"
    beta.mkdir()
    (beta / "SKILL.md").write_text("skill md\n")

    (skills_dir / ".hidden").mkdir()
    (skills_dir / "not_a_dir.txt").write_text("stray file\n")

    rc = tool.list_skills(_Args(verbose=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Total skills: 2" in out
    assert "✅ Expert" in out  # alpha
    assert "\U0001F4D6 Docs" in out  # beta
    assert "alpha" in out
    assert "beta" in out
    assert ".hidden" not in out
    assert "not_a_dir.txt" not in out
    assert "Expert-level (with tool.py): 1" in out
    assert "Documentation-only: 1" in out
    assert "Tip: Upgrade documentation-only skills" in out


def test_list_skills_verbose_shows_file_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    alpha = skills_dir / "alpha"
    (alpha / "scripts").mkdir(parents=True)
    (alpha / "scripts" / "tool.py").write_text("# tool\n")
    (alpha / "SKILL.md").write_text("skill md\n")
    (alpha / "README.md").write_text("readme\n")

    rc = tool.list_skills(_Args(verbose=True))

    out = capsys.readouterr().out
    assert rc == 0
    assert "SKILL.md" in out
    assert "README.md" in out
    assert "scripts/tool.py" in out


def test_list_skills_no_tip_when_all_expert(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    alpha = skills_dir / "alpha"
    (alpha / "scripts").mkdir(parents=True)
    (alpha / "scripts" / "tool.py").write_text("# tool\n")

    rc = tool.list_skills(_Args(verbose=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Documentation-only: 0" in out
    assert "Tip: Upgrade documentation-only skills" not in out


# --------------------------------------------------------------------------
# analyze_skill
# --------------------------------------------------------------------------

def test_analyze_skill_not_found_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.analyze_skill(_Args(name="ghost"))
    assert rc == 1
    assert "Skill not found: ghost" in capsys.readouterr().out


def test_analyze_skill_reports_sizes_and_suggests_everything_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "sparse"
    skill_dir.mkdir(parents=True)
    skill_md_content = "# Title\nTODO fill this in\n"
    (skill_dir / "SKILL.md").write_text(skill_md_content)
    expected_lines = len(skill_md_content.splitlines())
    expected_size = len(skill_md_content.encode())

    rc = tool.analyze_skill(_Args(name="sparse"))

    out = capsys.readouterr().out
    assert rc == 0
    assert f"SKILL.md: {expected_lines} lines, {expected_size} bytes" in out
    assert "Add scripts/tool.py for automation (80-90% time savings)" in out
    assert "Complete TODO items in SKILL.md" in out
    assert "Add YAML frontmatter to SKILL.md" in out
    assert "Create README.md with quick start guide" in out
    assert "  1. " in out


def test_analyze_skill_with_tool_reports_command_list_and_todo_suggestion(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "withtool"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: withtool\n---\nno todos\n")
    (skill_dir / "README.md").write_text("readme\n")
    tool_py_content = (
        "# TODO finish this\n"
        "subparsers.add_parser('alpha')\n"
        "subparsers.add_parser('beta')\n"
    )
    (skill_dir / "scripts" / "tool.py").write_text(tool_py_content)

    rc = tool.analyze_skill(_Args(name="withtool"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Commands (2):" in out
    assert "- alpha" in out
    assert "- beta" in out
    assert "Complete TODO items in tool.py" in out
    assert "Add more commands (current: 2, recommended: 4-8)" in out
    assert "Create README.md" not in out  # README exists, no suggestion


def test_analyze_skill_fully_clean_has_no_suggestions(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "pristine"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: pristine\n---\nall good\n")
    (skill_dir / "README.md").write_text("readme\n")
    tool_py = skill_dir / "scripts" / "tool.py"
    tool_py.write_text("".join(f"subparsers.add_parser('c{i}')\n" for i in range(5)))

    rc = tool.analyze_skill(_Args(name="pristine"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "No improvement suggestions - skill is well-structured!" in out


# --------------------------------------------------------------------------
# main() dispatch
# --------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_dispatches_create_new_skill(monkeypatch):
    called = {}
    def fake(args):
        called["name"] = args.name
        return 0
    monkeypatch.setattr(tool, "create_new_skill", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-new-skill", "--name", "abc"])
    rc = tool.main()
    assert rc == 0
    assert called["name"] == "abc"


def test_main_dispatches_upgrade_existing_skill_with_commands(monkeypatch):
    captured = {}
    def fake(args):
        captured["name"] = args.name
        captured["commands"] = args.commands
        return 0
    monkeypatch.setattr(tool, "upgrade_existing_skill", fake)
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "upgrade-existing-skill", "--name", "xyz", "--commands", "one", "two",
    ])
    rc = tool.main()
    assert rc == 0
    assert captured["name"] == "xyz"
    assert captured["commands"] == ["one", "two"]


def test_main_dispatches_validate_skill(monkeypatch):
    called = []
    monkeypatch.setattr(tool, "validate_skill", lambda a: called.append(a.name) or 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-skill", "--name", "q"])
    rc = tool.main()
    assert rc == 0
    assert called == ["q"]


def test_main_dispatches_list_skills_with_verbose_shorthand(monkeypatch):
    captured = {}
    def fake(args):
        captured["verbose"] = args.verbose
        return 0
    monkeypatch.setattr(tool, "list_skills", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "list-skills", "-v"])
    rc = tool.main()
    assert rc == 0
    assert captured["verbose"] is True


def test_main_dispatches_list_skills_default_verbose_false(monkeypatch):
    captured = {}
    def fake(args):
        captured["verbose"] = args.verbose
        return 0
    monkeypatch.setattr(tool, "list_skills", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "list-skills"])
    rc = tool.main()
    assert rc == 0
    assert captured["verbose"] is False


def test_main_dispatches_analyze_skill(monkeypatch):
    called = []
    monkeypatch.setattr(tool, "analyze_skill", lambda a: called.append(a.name) or 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "analyze-skill", "--name", "z"])
    rc = tool.main()
    assert rc == 0
    assert called == ["z"]


def test_main_missing_required_name_exits_for_each_name_requiring_command(monkeypatch):
    import pytest
    for cmd in ["create-new-skill", "upgrade-existing-skill", "validate-skill", "analyze-skill"]:
        monkeypatch.setattr(sys, "argv", ["tool.py", cmd])
        with pytest.raises(SystemExit):
            tool.main()


def test_subprocess_end_to_end_list_skills(tmp_path):
    skills_dir = tmp_path / ".claude" / "skills" / "demo"
    (skills_dir / "scripts").mkdir(parents=True)
    (skills_dir / "scripts" / "tool.py").write_text("# demo\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "list-skills"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Total skills: 1" in result.stdout


def test_subprocess_no_args_exits_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1


def test_upgrade_skill_scripts_dir_preexisting_still_succeeds(tmp_path, monkeypatch):
    # scripts/ dir can already exist (e.g. holding other helper files) even
    # though tool.py itself does not -- mkdir(exist_ok=True) must tolerate that.
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "up6"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "scripts" / "helper.txt").write_text("keep me\n")
    (skill_dir / "SKILL.md").write_text("---\nname: up6\n---\nbody\n")

    rc = tool.upgrade_existing_skill(_Args(name="up6", commands=None))

    assert rc == 0
    assert (skill_dir / "scripts" / "tool.py").exists()
    assert (skill_dir / "scripts" / "helper.txt").exists()


def test_create_new_skill_mkdir_calls_tolerate_dirs_that_already_exist(tmp_path, monkeypatch):
    # Simulate a stale/raced existence check: skill_dir (and its scripts/
    # subdir) already physically exist on disk, but create_new_skill's own
    # guard is fooled into thinking they don't. This proves mkdir(...,
    # exist_ok=True) on both the skill dir and the scripts dir is load
    # bearing -- exist_ok=False would raise FileExistsError here.
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "raced"
    (skill_dir / "scripts").mkdir(parents=True)
    monkeypatch.setattr(Path, "exists", lambda self: False)

    rc = tool.create_new_skill(_Args(name="raced"))

    assert rc == 0
    tool_py = skill_dir / "scripts" / "tool.py"
    assert tool_py.is_file()
    assert "Raced Tool" in tool_py.read_text()
