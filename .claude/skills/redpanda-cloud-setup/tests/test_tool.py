import importlib.util as _ilu
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "redpanda_cloud_setup_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_contains_message_and_checkmark(capsys):
    tool.print_success("hello")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "✓" in out


def test_print_error_contains_message_and_x(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "bad thing" in out
    assert "✗" in out


def test_print_info_contains_message(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert "fyi" in out


def test_print_header_contains_arrow_and_message(capsys):
    tool.print_header("Section Title")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section Title" in out


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_returns_real_subprocess_output():
    code, out, err = tool.run_command("echo hi")
    assert code == 0
    assert out.strip() == "hi"
    assert err == ""


def test_run_command_returns_nonzero_on_failing_shell_command():
    code, out, err = tool.run_command("exit 7")
    assert code == 7


def test_run_command_catches_any_exception_and_returns_error_tuple(monkeypatch):
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        raise OSError("boom")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "Error"


def test_run_command_respects_custom_timeout_value(monkeypatch):
    captured = {}

    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        captured["timeout"] = timeout
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi", timeout=42)
    assert captured["timeout"] == 42


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_prints_header_and_success_and_returns_0(capsys):
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Checking Prerequisites" in out
    assert "Prerequisites OK" in out


# ---------------------------------------------------------------------------
# create_topics
# ---------------------------------------------------------------------------

def test_create_topics_uses_default_list_when_topics_is_none(capsys):
    rc = tool.create_topics(_Args(topics=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: task-events" in out
    assert "Created topic: reminders" in out
    assert "Created topic: task-updates" in out


def test_create_topics_uses_default_list_when_topics_is_empty_string(capsys):
    rc = tool.create_topics(_Args(topics=""))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: task-events" in out
    assert "Created topic: reminders" in out
    assert "Created topic: task-updates" in out


def test_create_topics_splits_custom_comma_separated_list(capsys):
    rc = tool.create_topics(_Args(topics="alpha,beta,gamma"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: alpha" in out
    assert "Created topic: beta" in out
    assert "Created topic: gamma" in out
    assert "task-events" not in out


def test_create_topics_handles_single_topic_with_no_comma(capsys):
    rc = tool.create_topics(_Args(topics="solo-topic"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: solo-topic" in out
    assert out.count("Created topic:") == 1


def test_create_topics_preserves_empty_entries_from_trailing_comma(capsys):
    rc = tool.create_topics(_Args(topics="a,,b"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: a" in out
    assert "Created topic: b" in out
    assert out.count("Created topic:") == 3  # "a", "", "b" -- no stripping/filtering in the source


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_dispatches_check_prerequisites_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-prerequisites"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Prerequisites OK" in out


def test_main_dispatches_create_topics_with_default_flag_value(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-topics"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: task-events" in out
    assert "Created topic: reminders" in out
    assert "Created topic: task-updates" in out


def test_main_dispatches_create_topics_with_custom_topics_flag(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-topics", "--topics", "x,y"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created topic: x" in out
    assert "Created topic: y" in out
    assert "task-events" not in out


def test_main_rejects_unknown_subcommand_with_system_exit(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit):
        tool.main()


# ---------------------------------------------------------------------------
# subprocess smoke test (real __main__ entrypoint)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_no_command_prints_usage_and_exits_1():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_create_topics_end_to_end():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "create-topics", "--topics", "one,two"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert "Created topic: one" in proc.stdout
    assert "Created topic: two" in proc.stdout
