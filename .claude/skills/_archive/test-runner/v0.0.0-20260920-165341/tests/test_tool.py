import subprocess
import sys
from pathlib import Path

import pytest

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("test_runner_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_exact_format(capsys):
    tool.print_success("ok")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.GREEN}✓{tool.Colors.END} ok\n"


def test_print_error_exact_format(capsys):
    tool.print_error("bad")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.RED}✗{tool.Colors.END} bad\n"


def test_print_warning_exact_format(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.YELLOW}⚠{tool.Colors.END} careful\n"


def test_print_info_exact_format(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert out == f"{tool.Colors.BLUE}ℹ{tool.Colors.END} fyi\n"


def test_print_header_exact_format(capsys):
    tool.print_header("Section")
    out = capsys.readouterr().out
    assert out == f"\n{tool.Colors.BOLD}==> Section{tool.Colors.END}\n"


# ---------------------------------------------------------------------------
# run_command -- the ONLY function that ever touches subprocess.run. Every
# test here mocks subprocess.run directly: no test in this file ever spawns
# a real nested pytest process.
# ---------------------------------------------------------------------------

def test_run_command_success_returns_code_stdout_stderr(monkeypatch):
    captured = {}

    def fake_run(cmd, shell=None, capture_output=None, text=None, timeout=None):
        captured['cmd'] = cmd
        captured['shell'] = shell
        captured['capture_output'] = capture_output
        captured['text'] = text
        captured['timeout'] = timeout
        return _FakeCompleted(returncode=0, stdout="all good\n", stderr="")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("echo hi")
    assert code == 0
    assert out == "all good\n"
    assert err == ""
    assert captured['cmd'] == "echo hi"
    assert captured['shell'] is True
    assert captured['capture_output'] is True
    assert captured['text'] is True
    assert captured['timeout'] == 600


def test_run_command_passes_custom_timeout(monkeypatch):
    captured = {}

    def fake_run(cmd, shell=None, capture_output=None, text=None, timeout=None):
        captured['timeout'] = timeout
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi", timeout=42)
    assert captured['timeout'] == 42


def test_run_command_nonzero_exit_propagates(monkeypatch):
    monkeypatch.setattr(
        tool.subprocess, "run",
        lambda *a, **k: _FakeCompleted(returncode=3, stdout="", stderr="boom"),
    )
    code, out, err = tool.run_command("false")
    assert code == 3
    assert err == "boom"


def test_run_command_timeout_expired_returns_1_with_message(monkeypatch):
    def fake_run(cmd, shell=None, capture_output=None, text=None, timeout=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("sleep 999", timeout=5)
    assert code == 1
    assert out == ""
    assert err == "Command timed out after 5s"


def test_run_command_generic_exception_returns_1_with_str(monkeypatch):
    def fake_run(cmd, shell=None, capture_output=None, text=None, timeout=None):
        raise OSError("no such command")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "no such command"


# ---------------------------------------------------------------------------
# check_tool
# ---------------------------------------------------------------------------

def test_check_tool_success_prints_first_line_of_version(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "pytest 7.4.0\nextra line\n", ""))
    result = tool.check_tool("pytest", "pytest --version")
    out = capsys.readouterr().out
    assert result is True
    assert f"{tool.Colors.GREEN}✓{tool.Colors.END} pytest: pytest 7.4.0" in out


def test_check_tool_success_with_empty_stdout_reports_installed(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", ""))
    result = tool.check_tool("thing", "check-thing")
    out = capsys.readouterr().out
    assert result is True
    assert "thing: installed" in out


def test_check_tool_failure_prints_not_found(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (1, "", "err"))
    result = tool.check_tool("pytest", "pytest --version")
    out = capsys.readouterr().out
    assert result is False
    assert f"{tool.Colors.RED}✗{tool.Colors.END} pytest: Not found" in out


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def _make_run_command(responses):
    """responses: list of (substring, (code, out, err)); first match wins;
    default (0, "installed", "") if nothing matches."""
    def fake(cmd, timeout=600):
        for substr, resp in responses:
            if substr in cmd:
                return resp
        return (0, "installed", "")
    return fake


def test_check_prerequisites_all_good_returns_0(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "run_command", _make_run_command([
        ("python3 --version", (0, "Python 3.11.5", "")),
        ("pytest --version", (0, "pytest 7.4.0", "")),
        ("pytest-xdist", (0, "installed", "")),
    ]))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    result = tool.check_prerequisites(_Args())
    assert result == 0


def test_check_prerequisites_python_missing_returns_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool, "run_command", _make_run_command([
        ("python3 --version", (1, "", "not found")),
        ("pytest --version", (0, "pytest 7.4.0", "")),
    ]))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    result = tool.check_prerequisites(_Args())
    assert result == 1
    out = capsys.readouterr().out
    assert "Some prerequisites missing" in out


def test_check_prerequisites_pytest_missing_returns_1(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "run_command", _make_run_command([
        ("python3 --version", (0, "Python 3.11.5", "")),
        ("pytest --version", (1, "", "not found")),
    ]))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    result = tool.check_prerequisites(_Args())
    assert result == 1


def test_check_prerequisites_optional_tools_missing_only_warns(monkeypatch, tmp_path, capsys):
    # pytest-cov / pytest-xdist missing must NOT flip the overall result to 1
    monkeypatch.setattr(tool, "run_command", _make_run_command([
        ("pytest-cov", (1, "", "")),
        ("pytest-xdist", (1, "", "")),
        ("python3 --version", (0, "Python 3.11.5", "")),
        ("pytest --version", (0, "pytest 7.4.0", "")),
    ]))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    result = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert result == 0
    assert "pytest-cov not found" in out
    assert "pytest-xdist not found" in out


def test_check_prerequisites_missing_tests_dir_returns_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool, "run_command", _make_run_command([
        ("python3 --version", (0, "Python 3.11.5", "")),
        ("pytest --version", (0, "pytest 7.4.0", "")),
    ]))
    monkeypatch.chdir(tmp_path)  # no tests/ dir created
    result = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert result == 1
    assert "tests/ directory not found" in out


# ---------------------------------------------------------------------------
# run_all / run_unit / run_integration / run_e2e -- command assembly + flags
# ---------------------------------------------------------------------------

def test_run_all_default_command_and_success(monkeypatch, capsys):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout))[0:0] or (0, "1 passed", ""))
    result = tool.run_all(_Args(verbose=False, show_output=False, stop_on_first=False))
    assert captured['cmd'] == "pytest tests/ -v"
    assert captured['timeout'] == 600
    assert result == 0
    out = capsys.readouterr().out
    assert "All tests passed" in out


def test_run_all_all_flags_appended(monkeypatch):
    captured = {}

    def fake(cmd, timeout=600):
        captured['cmd'] = cmd
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_all(_Args(verbose=True, show_output=True, stop_on_first=True))
    assert captured['cmd'] == "pytest tests/ -v -vv -s -x"


def test_run_all_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "warn on stderr"))
    tool.run_all(_Args(verbose=False, show_output=False, stop_on_first=False))
    out = capsys.readouterr().out
    assert "warn on stderr" in out


def test_run_all_failure_returns_nonzero_code(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (5, "boom out", "boom err"))
    result = tool.run_all(_Args(verbose=False, show_output=False, stop_on_first=False))
    assert result == 5
    out = capsys.readouterr().out
    assert "Some tests failed" in out
    assert "boom out" in out
    assert "boom err" in out


def test_run_unit_default_command(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout)) and (0, "", ""))
    tool.run_unit(_Args(verbose=False, show_output=False))
    assert captured['cmd'] == "pytest tests/unit/ -v"
    assert captured['timeout'] == 300


def test_run_unit_flags_appended_and_success_message(monkeypatch, capsys):
    captured = {}

    def fake(cmd, timeout=600):
        captured['cmd'] = cmd
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    result = tool.run_unit(_Args(verbose=True, show_output=True))
    assert captured['cmd'] == "pytest tests/unit/ -v -vv -s"
    assert result == 0
    out = capsys.readouterr().out
    assert "Unit tests passed" in out


def test_run_unit_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "unit stderr text"))
    tool.run_unit(_Args(verbose=False, show_output=False))
    out = capsys.readouterr().out
    assert "unit stderr text" in out


def test_run_unit_failure_message(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (1, "", ""))
    result = tool.run_unit(_Args(verbose=False, show_output=False))
    assert result == 1
    out = capsys.readouterr().out
    assert "Unit tests failed" in out


def test_run_integration_default_command_and_timeout(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout)) and (0, "", ""))
    tool.run_integration(_Args(verbose=False, show_output=False))
    assert captured['cmd'] == "pytest tests/integration/ -v"
    assert captured['timeout'] == 600


def test_run_integration_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "integration stderr text"))
    tool.run_integration(_Args(verbose=False, show_output=False))
    out = capsys.readouterr().out
    assert "integration stderr text" in out


def test_run_integration_flags_and_failure(monkeypatch, capsys):
    captured = {}

    def fake(cmd, timeout=600):
        captured['cmd'] = cmd
        return (2, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    result = tool.run_integration(_Args(verbose=True, show_output=True))
    assert captured['cmd'] == "pytest tests/integration/ -v -vv -s"
    assert result == 2
    out = capsys.readouterr().out
    assert "Integration tests failed" in out


def test_run_e2e_default_command(monkeypatch, capsys):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout)) and (0, "", ""))
    result = tool.run_e2e(_Args(verbose=False, show_output=False))
    assert captured['cmd'] == "pytest tests/e2e/ -v"
    assert captured['timeout'] == 600
    assert result == 0
    out = capsys.readouterr().out
    assert "E2E tests passed" in out


def test_run_e2e_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "e2e stderr text"))
    tool.run_e2e(_Args(verbose=False, show_output=False))
    out = capsys.readouterr().out
    assert "e2e stderr text" in out


def test_run_e2e_flags_and_failure(monkeypatch, capsys):
    captured = {}

    def fake(cmd, timeout=600):
        captured['cmd'] = cmd
        return (1, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    result = tool.run_e2e(_Args(verbose=True, show_output=True))
    assert captured['cmd'] == "pytest tests/e2e/ -v -vv -s"
    assert result == 1
    out = capsys.readouterr().out
    assert "E2E tests failed" in out


# ---------------------------------------------------------------------------
# run_coverage
# ---------------------------------------------------------------------------

def test_run_coverage_default_command_no_min(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout)) and (0, "", ""))
    tool.run_coverage(_Args(min_coverage=None))
    assert captured['cmd'] == "pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v"
    assert captured['timeout'] == 600


def test_run_coverage_with_min_coverage_appends_flag(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd)) and (0, "", ""))
    tool.run_coverage(_Args(min_coverage=80))
    assert captured['cmd'] == "pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v --cov-fail-under=80"


def test_run_coverage_min_coverage_zero_is_falsy_and_omitted(monkeypatch):
    # min_coverage=0 is falsy in Python, so `if args.min_coverage:` skips it
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd)) and (0, "", ""))
    tool.run_coverage(_Args(min_coverage=0))
    assert "--cov-fail-under" not in captured['cmd']


def test_run_coverage_success_prints_html_report_path(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", ""))
    result = tool.run_coverage(_Args(min_coverage=None))
    assert result == 0
    out = capsys.readouterr().out
    assert "Tests passed with coverage" in out
    assert "htmlcov/index.html" in out


def test_run_coverage_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "coverage stderr text"))
    tool.run_coverage(_Args(min_coverage=None))
    out = capsys.readouterr().out
    assert "coverage stderr text" in out


def test_run_coverage_failure_message(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (1, "", ""))
    result = tool.run_coverage(_Args(min_coverage=None))
    assert result == 1
    out = capsys.readouterr().out
    assert "below threshold" in out


# ---------------------------------------------------------------------------
# run_specific
# ---------------------------------------------------------------------------

def test_run_specific_builds_command_with_test_path(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (captured.setdefault('cmd', cmd), captured.setdefault('timeout', timeout)) and (0, "", ""))
    tool.run_specific(_Args(test_path="tests/test_x.py::test_thing", verbose=False, show_output=False))
    assert captured['cmd'] == "pytest tests/test_x.py::test_thing -v"
    assert captured['timeout'] == 300


def test_run_specific_flags_and_success(monkeypatch, capsys):
    captured = {}

    def fake(cmd, timeout=600):
        captured['cmd'] = cmd
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    result = tool.run_specific(_Args(test_path="tests/test_x.py", verbose=True, show_output=True))
    assert captured['cmd'] == "pytest tests/test_x.py -v -vv -s"
    assert result == 0
    out = capsys.readouterr().out
    assert "Test(s) passed" in out


def test_run_specific_prints_stderr_when_present(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", "specific stderr text"))
    tool.run_specific(_Args(test_path="tests/test_x.py", verbose=False, show_output=False))
    out = capsys.readouterr().out
    assert "specific stderr text" in out


def test_run_specific_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (1, "", ""))
    result = tool.run_specific(_Args(test_path="tests/test_x.py", verbose=False, show_output=False))
    assert result == 1
    out = capsys.readouterr().out
    assert "Test(s) failed" in out


# ---------------------------------------------------------------------------
# run_parallel
# ---------------------------------------------------------------------------

def test_run_parallel_xdist_missing_returns_1_without_second_call(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=600):
        calls.append(cmd)
        return (1, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    result = tool.run_parallel(_Args(workers=None, verbose=False))
    assert result == 1
    assert len(calls) == 1
    out = capsys.readouterr().out
    assert "pytest-xdist not installed" in out


def test_run_parallel_default_workers_is_auto(monkeypatch):
    calls = []

    def fake(cmd, timeout=600):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_parallel(_Args(workers=None, verbose=False))
    assert len(calls) == 2
    assert calls[1] == "pytest tests/ -n auto -v"


def test_run_parallel_explicit_workers_used(monkeypatch):
    calls = []

    def fake(cmd, timeout=600):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_parallel(_Args(workers="4", verbose=False))
    assert calls[1] == "pytest tests/ -n 4 -v"


def test_run_parallel_verbose_flag_appended(monkeypatch):
    calls = []

    def fake(cmd, timeout=600):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_parallel(_Args(workers=None, verbose=True))
    assert calls[1] == "pytest tests/ -n auto -v -vv"


def test_run_parallel_prints_stderr_when_present(monkeypatch, capsys):
    def fake(cmd, timeout=600):
        return (0, "", "") if "pip show" in cmd else (0, "", "parallel stderr text")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_parallel(_Args(workers=None, verbose=False))
    out = capsys.readouterr().out
    assert "parallel stderr text" in out


def test_run_parallel_success_and_failure_messages(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", ""))
    result = tool.run_parallel(_Args(workers=None, verbose=False))
    assert result == 0
    out = capsys.readouterr().out
    assert "parallel execution" in out

    def fake_fail(cmd, timeout=600):
        return (0, "", "") if "pip show" in cmd else (7, "", "")

    monkeypatch.setattr(tool, "run_command", fake_fail)
    result2 = tool.run_parallel(_Args(workers=None, verbose=False))
    assert result2 == 7
    out2 = capsys.readouterr().out
    assert "Some tests failed" in out2


# ---------------------------------------------------------------------------
# watch -- both branches exercised without ever really watching/looping
# forever or invoking a real interactive process.
# ---------------------------------------------------------------------------

def test_watch_pytest_watch_missing_uses_simple_loop_and_stops_on_interrupt(monkeypatch, capsys):
    calls = []

    def fake_run_command(cmd, timeout=600):
        calls.append(cmd)
        if "pytest-watch" in cmd:
            return (1, "", "")  # pytest-watch NOT installed
        return (0, "1 passed", "")

    def fake_sleep(seconds):
        raise KeyboardInterrupt()

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    # Defensive: never let a real "ptw" invocation happen even if a mutated
    # comparison sends this test down the wrong (os.system) branch.
    monkeypatch.setattr(tool.os, "system", lambda cmd: (_ for _ in ()).throw(AssertionError(f"unexpected os.system call: {cmd}")))
    import time as _time
    monkeypatch.setattr(_time, "sleep", fake_sleep)
    result = tool.watch(_Args())
    assert result == 0
    # first call checks pytest-watch, second is the one test run before interrupt
    assert any("pip show pytest-watch" in c for c in calls)
    assert any(c == "pytest tests/ -v --tb=short" for c in calls)
    out = capsys.readouterr().out
    assert "pytest-watch not installed" in out
    assert "Stopped watching" in out


def test_watch_simple_loop_prints_stderr_when_present(monkeypatch, capsys):
    def fake_run_command(cmd, timeout=600):
        if "pytest-watch" in cmd:
            return (1, "", "")
        return (0, "", "watch loop stderr text")

    def fake_sleep(seconds):
        raise KeyboardInterrupt()

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    monkeypatch.setattr(tool.os, "system", lambda cmd: (_ for _ in ()).throw(AssertionError(f"unexpected os.system call: {cmd}")))
    import time as _time
    monkeypatch.setattr(_time, "sleep", fake_sleep)
    result = tool.watch(_Args())
    assert result == 0
    out = capsys.readouterr().out
    assert "watch loop stderr text" in out


def test_watch_pytest_watch_installed_uses_os_system(monkeypatch, capsys):
    calls = []

    def fake_run_command(cmd, timeout=600):
        calls.append(cmd)
        return (0, "", "")  # pip show succeeds -> pytest-watch "installed"

    def fake_sleep(seconds):
        # Safety net only: correct behavior never reaches the simple-loop
        # branch here (code == 0 means installed), so this should never
        # fire. If it ever does (e.g. under a mutated comparison), raising
        # KeyboardInterrupt guarantees the test still terminates instead of
        # spinning in watch()'s `while True:` loop forever -- the assertions
        # below will then correctly fail instead of the test hanging.
        raise KeyboardInterrupt()

    system_calls = []
    monkeypatch.setattr(tool, "run_command", fake_run_command)
    monkeypatch.setattr(tool.os, "system", lambda cmd: system_calls.append(cmd))
    import time as _time
    monkeypatch.setattr(_time, "sleep", fake_sleep)
    result = tool.watch(_Args())
    assert result == 0
    assert system_calls == ["ptw tests/ -- -v"]
    out = capsys.readouterr().out
    assert "Press Ctrl+C to stop" in out


# ---------------------------------------------------------------------------
# run_tests ("test" command): thin orchestrator over check_prerequisites +
# run_all. Both are monkeypatched directly here, since their own bodies are
# already covered by the dedicated tests above -- this isolates run_tests'
# own short-circuit logic.
# ---------------------------------------------------------------------------

def test_run_tests_short_circuits_when_prerequisites_fail(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda args: 1)

    def fail_if_called(args):
        raise AssertionError("run_all should not be called when prerequisites fail")

    monkeypatch.setattr(tool, "run_all", fail_if_called)
    result = tool.run_tests(_Args())
    assert result == 1
    out = capsys.readouterr().out
    assert "Prerequisites check failed" in out


def test_run_tests_runs_all_when_prerequisites_pass(monkeypatch):
    monkeypatch.setattr(tool, "check_prerequisites", lambda args: 0)
    monkeypatch.setattr(tool, "run_all", lambda args: 42)
    result = tool.run_tests(_Args())
    assert result == 42


# ---------------------------------------------------------------------------
# main() CLI dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    result = tool.main()
    assert result == 1
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_main_check_prerequisites_dispatch(monkeypatch):
    captured = {}

    def fake_check_prerequisites(args):
        captured['called'] = True
        return 0

    monkeypatch.setattr(tool, "check_prerequisites", fake_check_prerequisites)
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    result = tool.main()
    assert result == 0
    assert captured['called'] is True


def test_main_run_all_dispatch_with_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_all", lambda args: captured.setdefault('args', args) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-all", "--verbose", "--show-output", "--stop-on-first"])
    result = tool.main()
    assert result == 0
    assert captured['args'].verbose is True
    assert captured['args'].show_output is True
    assert captured['args'].stop_on_first is True


def test_main_run_unit_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_unit", lambda args: captured.setdefault('args', args) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-unit"])
    tool.main()
    assert captured['args'].verbose is False
    assert captured['args'].show_output is False


def test_main_run_integration_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_integration", lambda args: captured.setdefault('called', True) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-integration"])
    tool.main()
    assert captured['called'] is True


def test_main_run_e2e_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_e2e", lambda args: captured.setdefault('called', True) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-e2e"])
    tool.main()
    assert captured['called'] is True


def test_main_run_coverage_dispatch_with_min_coverage(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_coverage", lambda args: captured.setdefault('args', args) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-coverage", "--min-coverage", "85"])
    tool.main()
    assert captured['args'].min_coverage == 85


def test_main_run_specific_dispatch_with_positional(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_specific", lambda args: captured.setdefault('args', args) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-specific", "tests/test_x.py::test_y"])
    tool.main()
    assert captured['args'].test_path == "tests/test_x.py::test_y"


def test_main_run_specific_missing_positional_raises_systemexit_2(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-specific"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 2


def test_main_run_parallel_dispatch_with_workers(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_parallel", lambda args: captured.setdefault('args', args) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-parallel", "--workers", "8"])
    tool.main()
    assert captured['args'].workers == "8"


def test_main_watch_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "watch", lambda args: captured.setdefault('called', True) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "watch"])
    tool.main()
    assert captured['called'] is True


def test_main_test_dispatch(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "run_tests", lambda args: captured.setdefault('called', True) and 0)
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    tool.main()
    assert captured['called'] is True


def test_main_unrecognized_command_raises_systemexit_2(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 2


def test_main_returns_command_functions_return_value(monkeypatch):
    monkeypatch.setattr(tool, "run_unit", lambda args: 99)
    monkeypatch.setattr(sys, "argv", ["tool.py", "run-unit"])
    assert tool.main() == 99


# ---------------------------------------------------------------------------
# Real subprocess smoke test: invokes the script's __main__ entrypoint
# end-to-end via a subcommand ('check-prerequisites') that never runs the
# actual project test suite -- only cheap version-check shell commands
# ('python3 --version', 'pytest --version', etc.) -- so this never spawns a
# real nested/recursive pytest test RUN, only a `pytest --version` check.
# ---------------------------------------------------------------------------

def test_subprocess_runs_as_script_and_exercises_main_guard():
    # Deliberately invoked with NO subcommand: this exercises the real
    # `if __name__ == '__main__': sys.exit(main())` entrypoint end-to-end
    # in a genuine child process, while guaranteeing that tool.py itself
    # never shells out to a real (nested) command -- the no-command path
    # only calls parser.print_help() and returns before any run_command/
    # subprocess.run call is reached. This avoids ANY real nested pytest
    # (or other) subprocess spawn, including under mutation testing, where
    # a mutated comparison/boolean elsewhere in the file could otherwise
    # change an unrelated code path's behavior in ways that risk a hung
    # grandchild process across two layers of real subprocess calls.
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()
