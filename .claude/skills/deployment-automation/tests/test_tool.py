import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("deployment_automation_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_check_env_vars_flags_missing():
    missing = tool.check_env_vars(["A", "B"], {"A": "x"})
    assert missing == ["B"]


def test_check_env_vars_flags_empty_string_as_missing():
    missing = tool.check_env_vars(["A"], {"A": ""})
    assert missing == ["A"]


def test_check_env_vars_ok_when_all_present():
    assert tool.check_env_vars(["A", "B"], {"A": "1", "B": "2"}) == []


def test_check_env_vars_never_leaks_values_in_result():
    missing = tool.check_env_vars(["SECRET_KEY"], {})
    assert missing == ["SECRET_KEY"]  # only the name, never a value


def test_build_rollback_plan_always_includes_redeploy_step():
    steps = tool.build_rollback_plan("v1.0.0")
    assert any("v1.0.0" in s for s in steps)


def test_build_rollback_plan_includes_migration_and_flag_when_given():
    steps = tool.build_rollback_plan("v1.0.0", migration_name="0005_x", feature_flag="new_thing")
    assert any("0005_x" in s for s in steps)
    assert any("new_thing" in s for s in steps)


def test_run_smoke_check_reports_failure_for_unreachable_host():
    ok, detail = tool.run_smoke_check("http://localhost:1/definitely-not-running", timeout=2)
    assert ok is False

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json as _json
import subprocess as _subprocess_mod
import sys as _sys
import pytest


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_run_smoke_check_ok_on_http_200(monkeypatch):
    class _FakeCompleted:
        stdout = "200"

    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: _FakeCompleted())
    ok, code = tool.run_smoke_check("http://example.test/health")
    assert ok is True
    assert code == "200"


def test_run_smoke_check_fails_on_non_200_code(monkeypatch):
    class _FakeCompleted:
        stdout = "503"

    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: _FakeCompleted())
    ok, code = tool.run_smoke_check("http://example.test/health")
    assert ok is False
    assert code == "503"


def test_run_smoke_check_handles_timeout_expired(monkeypatch):
    def _raise_timeout(*a, **kw):
        raise tool.subprocess.TimeoutExpired(cmd="curl", timeout=2)

    monkeypatch.setattr(tool.subprocess, "run", _raise_timeout)
    ok, detail = tool.run_smoke_check("http://example.test/health", timeout=2)
    assert ok is False
    assert "curl" in detail or "timed out" in detail.lower() or detail


def test_run_smoke_check_handles_missing_curl_binary(monkeypatch):
    def _raise_not_found(*a, **kw):
        raise FileNotFoundError("curl not found")

    monkeypatch.setattr(tool.subprocess, "run", _raise_not_found)
    ok, detail = tool.run_smoke_check("http://example.test/health")
    assert ok is False
    assert "curl not found" in detail


def test_cmd_check_env_vars_ok_when_all_present(monkeypatch, capsys):
    monkeypatch.setenv("FOO_VAR_TEST", "value")
    rc = tool.cmd_check_env_vars(_Args(required="FOO_VAR_TEST"))
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cmd_check_env_vars_reports_missing(monkeypatch, capsys):
    monkeypatch.delenv("SOME_MISSING_VAR_TEST", raising=False)
    rc = tool.cmd_check_env_vars(_Args(required="SOME_MISSING_VAR_TEST"))
    assert rc == 1
    out = capsys.readouterr().out
    assert "MISSING" in out
    assert "SOME_MISSING_VAR_TEST" in out


def test_cmd_smoke_check_success(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_smoke_check", lambda url, timeout=10: (True, "200"))
    rc = tool.cmd_smoke_check(_Args(url="http://x", timeout=5))
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("OK")


def test_cmd_smoke_check_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_smoke_check", lambda url, timeout=10: (False, "500"))
    rc = tool.cmd_smoke_check(_Args(url="http://x", timeout=5))
    assert rc == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL")


def test_cmd_rollback_plan_prints_json_steps(capsys):
    args = _Args(previous_version="v1.0.0", migration=None, feature_flag=None)
    rc = tool.cmd_rollback_plan(args)
    assert rc == 0
    steps = _json.loads(capsys.readouterr().out)
    assert any("v1.0.0" in s for s in steps)


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_check_env_vars_end_to_end(monkeypatch, capsys):
    monkeypatch.setenv("FOO_VAR_TEST2", "value")
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-env-vars", "--required", "FOO_VAR_TEST2"])
    rc = tool.main()
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_smoke_check_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_smoke_check", lambda url, timeout=10: (True, "200"))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "smoke-check", "--url", "http://x"])
    rc = tool.main()
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_rollback_plan_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "rollback-plan", "--previous-version", "v2.0.0",
                                        "--migration", "0007_x", "--feature-flag", "flag_x"])
    rc = tool.main()
    assert rc == 0
    steps = _json.loads(capsys.readouterr().out)
    assert any("0007_x" in s for s in steps)
    assert any("flag_x" in s for s in steps)


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_missing_required_required_arg_for_check_env_vars_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-env-vars"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_url_arg_for_smoke_check_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "smoke-check"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_previous_version_arg_for_rollback_plan_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "rollback-plan"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = _subprocess_mod.run(
        [_sys.executable, str(script), "rollback-plan", "--previous-version", "v1.0.0"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "v1.0.0" in proc.stdout


def test_run_smoke_check_invokes_curl_with_text_mode_and_capture_output(monkeypatch):
    captured = {}

    class _FakeCompleted:
        stdout = "200"

    def _fake_run(cmd, capture_output=None, text=None, timeout=None):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        return _FakeCompleted()

    monkeypatch.setattr(tool.subprocess, "run", _fake_run)
    tool.run_smoke_check("http://example.test/health", timeout=7)
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["timeout"] == 7
    assert captured["cmd"][0] == "curl"
    assert captured["cmd"][-1] == "http://example.test/health"
