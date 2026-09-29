import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("oracle_oke_deploy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    """Minimal stand-in for an argparse.Namespace."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_includes_message(capsys):
    tool.print_success("cluster ready")
    assert "cluster ready" in capsys.readouterr().out


def test_print_error_includes_message(capsys):
    tool.print_error("boom")
    assert "boom" in capsys.readouterr().out


def test_print_info_includes_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_includes_message(capsys):
    tool.print_header("Section")
    assert "Section" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_command: the actual subprocess boundary
# ---------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_command_success_returns_tuple(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: _FakeCompleted(0, "out", "err"))
    assert tool.run_command("echo hi") == (0, "out", "err")


def test_run_command_forwards_shell_capture_output_text_and_timeout(monkeypatch):
    """Kills the mutants that flip any of `shell=True`, `capture_output=True`
    or `text=True` to False in the subprocess.run call: each is asserted
    individually so a mutation of any single one is observable."""
    captured = {}

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured.update(cmd=cmd, shell=shell, capture_output=capture_output, text=text, timeout=timeout)
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi", timeout=17)
    assert captured["cmd"] == "echo hi"
    assert captured["shell"] is True
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["timeout"] == 17


def test_run_command_swallows_any_exception_and_returns_error_tuple(monkeypatch):
    def fake_run(*a, **k):
        raise OSError("no such file")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.run_command("bogus") == (1, "", "Error")


def test_run_command_swallows_timeout_expired_too(monkeypatch):
    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd="sleep 100", timeout=5)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.run_command("sleep 100", timeout=5) == (1, "", "Error")


def test_run_command_default_timeout_is_300(monkeypatch):
    captured = {}

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured["timeout"] = timeout
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi")
    assert captured["timeout"] == 300


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_always_returns_0_and_prints_ok(capsys):
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Prerequisites OK" in out


# ---------------------------------------------------------------------------
# create_cluster
# ---------------------------------------------------------------------------

def test_create_cluster_uses_given_cluster_name(capsys):
    rc = tool.create_cluster(_Args(cluster_name="my-cluster"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "my-cluster" in out
    assert "todo-app" not in out


def test_create_cluster_defaults_to_todo_app_when_name_is_none(capsys):
    rc = tool.create_cluster(_Args(cluster_name=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "todo-app" in out


def test_create_cluster_defaults_to_todo_app_when_name_is_empty_string(capsys):
    """cluster_name uses `or`, so a falsy empty string also falls back to
    the "todo-app" default, not just None."""
    rc = tool.create_cluster(_Args(cluster_name=""))
    out = capsys.readouterr().out
    assert rc == 0
    assert "todo-app" in out


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------

def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_dispatches_check_prerequisites(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Prerequisites OK" in out


def test_main_dispatches_create_cluster_with_defaults(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-cluster"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "todo-app" in out


def test_main_dispatches_create_cluster_with_explicit_args(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "create-cluster",
        "--cluster-name", "prod-cluster",
        "--nodes", "4",
        "--free-tier",
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "prod-cluster" in out


def test_main_rejects_unknown_command(monkeypatch):
    """argparse's subparser `choices` are exactly {check-prerequisites,
    create-cluster}; anything else is rejected before reaching the
    commands dict, so this must exit non-zero rather than dispatch."""
    monkeypatch.setattr(sys, "argv", ["tool.py", "bogus-command"])
    try:
        tool.main()
        assert False, "expected SystemExit for an unrecognized subcommand"
    except SystemExit as e:
        assert e.code != 0


def test_script_runs_as_main_entrypoint_via_subprocess():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "check-prerequisites"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Prerequisites OK" in result.stdout


def test_script_with_no_args_via_subprocess_prints_help_and_exits_1():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()
