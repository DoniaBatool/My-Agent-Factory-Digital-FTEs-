import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("production_checklist_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_check_env_gitignored_true(tmp_path):
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n")
    ok, _ = tool.check_env_gitignored(tmp_path)
    assert ok is True


def test_check_env_gitignored_false_when_missing(tmp_path):
    ok, detail = tool.check_env_gitignored(tmp_path)
    assert ok is False
    assert "no .gitignore" in detail


def test_check_no_hardcoded_secrets_flags_offender(tmp_path):
    (tmp_path / "app.py").write_text("api_key = 'sk_live_1234567890'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is False
    assert "app.py" in offenders


def test_check_no_hardcoded_secrets_ignores_test_files(tmp_path):
    (tmp_path / "test_app.py").write_text("api_key = 'sk_live_1234567890'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is True
    assert offenders == []


def test_check_tests_exist_true(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    ok, _ = tool.check_tests_exist(tmp_path)
    assert ok is True


def test_check_tests_exist_false_when_absent(tmp_path):
    ok, _ = tool.check_tests_exist(tmp_path)
    assert ok is False


def test_check_health_endpoint_found(tmp_path):
    (tmp_path / "main.py").write_text("@app.get('/health')\ndef health(): return 'ok'\n")
    ok, _ = tool.check_health_endpoint(tmp_path)
    assert ok is True


def test_run_checklist_returns_all_four_checks(tmp_path):
    results = tool.run_checklist(tmp_path)
    assert set(results.keys()) == {"env_gitignored", "no_hardcoded_secrets", "tests_exist", "health_endpoint"}


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys as _sys
import pytest


def test_check_env_gitignored_true_via_wildcard_pattern(tmp_path):
    (tmp_path / ".gitignore").write_text("*.env\nnode_modules\n")
    ok, detail = tool.check_env_gitignored(tmp_path)
    assert ok is True
    assert "is git-ignored" in detail


def test_check_env_gitignored_false_when_gitignore_exists_but_lacks_env(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules\n__pycache__\n")
    ok, detail = tool.check_env_gitignored(tmp_path)
    assert ok is False
    assert "not listed" in detail


def test_check_no_hardcoded_secrets_case_insensitive_key_name(tmp_path):
    (tmp_path / "app.py").write_text("API_KEY: 'sk_live_1234567890'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is False
    assert "app.py" in offenders


def test_check_no_hardcoded_secrets_short_value_not_flagged(tmp_path):
    # SECRET_LIKE requires {6,} chars inside the quotes -- a 4-char value must not match
    (tmp_path / "app.py").write_text("password = 'ab12'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is True
    assert offenders == []


def test_check_no_hardcoded_secrets_no_files_at_all_passes(tmp_path):
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is True
    assert offenders == []


def test_check_no_hardcoded_secrets_ignores_extensions_outside_allowlist(tmp_path):
    (tmp_path / "notes.txt").write_text("password = 'realsecret123'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is True
    assert offenders == []


def test_check_no_hardcoded_secrets_reports_multiple_offenders(tmp_path):
    (tmp_path / "a.py").write_text("secret = 'aaaaaaaaaa'\n")
    (tmp_path / "b.js").write_text("secret = 'bbbbbbbbbb'\n")
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is False
    assert sorted(offenders) == ["a.py", "b.js"]


def test_check_tests_exist_true_with_singular_test_dir(tmp_path):
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test_x.py").write_text("def test_x(): pass\n")
    ok, detail = tool.check_tests_exist(tmp_path)
    assert ok is True
    assert "tests/" in detail


def test_check_tests_exist_false_detail_message(tmp_path):
    ok, detail = tool.check_tests_exist(tmp_path)
    assert ok is False
    assert "no tests/" in detail


def test_check_health_endpoint_case_insensitive_and_no_leading_slash(tmp_path):
    (tmp_path / "main.py").write_text("route = \"HEALTH\"\n")
    ok, detail = tool.check_health_endpoint(tmp_path)
    assert ok is True
    assert detail.endswith("main.py")


def test_check_health_endpoint_not_found_detail_message(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    ok, detail = tool.check_health_endpoint(tmp_path)
    assert ok is False
    assert "no /health route found" == detail


def test_run_checklist_all_pass(tmp_path):
    (tmp_path / ".gitignore").write_text(".env\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "app.py").write_text("@app.get('/health')\ndef health(): pass\n")
    results = tool.run_checklist(tmp_path)
    assert all(r["pass"] for r in results.values())


def test_run_checklist_reports_offenders_list_for_secrets(tmp_path):
    (tmp_path / "app.py").write_text("secret = 'reallylongvalue123'\n")
    results = tool.run_checklist(tmp_path)
    assert results["no_hardcoded_secrets"]["pass"] is False
    assert "app.py" in results["no_hardcoded_secrets"]["detail"]


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_cmd_run_checklist_ready_when_all_pass(tmp_path, capsys):
    (tmp_path / ".gitignore").write_text(".env\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "app.py").write_text("'/health'\n")
    args = _Args(project_root=str(tmp_path))
    rc = tool.cmd_run_checklist(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "GO-LIVE: READY" in out


def test_cmd_run_checklist_not_ready_when_any_fail(tmp_path, capsys):
    args = _Args(project_root=str(tmp_path))
    rc = tool.cmd_run_checklist(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "GO-LIVE: NOT READY" in out
    payload_start = out.index("{")
    payload_end = out.rindex("}") + 1
    json.loads(out[payload_start:payload_end])  # printed JSON must actually be valid JSON


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


def test_main_run_checklist_end_to_end(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "run-checklist", str(tmp_path)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "GO-LIVE: NOT READY" in out


def test_main_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_run_checklist_missing_positional_project_root_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "run-checklist"])
    with pytest.raises(SystemExit):
        tool.main()


def test_cli_subprocess_smoke_test_runs_main_guard(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "run-checklist", str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 1
    assert "GO-LIVE: NOT READY" in proc.stdout


def test_cli_subprocess_smoke_test_all_pass_exits_zero(tmp_path):
    (tmp_path / ".gitignore").write_text(".env\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    (tmp_path / "app.py").write_text("'/health'\n")
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "run-checklist", str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert "GO-LIVE: READY" in proc.stdout


def test_check_no_hardcoded_secrets_skips_file_that_raises_oserror_on_read(tmp_path, monkeypatch):
    # is_file() must be True for the file to even be considered, so a
    # dangling symlink (is_file() -> False) never reaches the try/except --
    # simulate a real-world unreadable file (permission denied, I/O error)
    # by making read_text() itself raise for this one path.
    offending = tmp_path / "app.py"
    offending.write_text("password = 'wouldhavematchedabc'\n")
    real_read_text = Path.read_text

    def flaky_read_text(self, *a, **kw):
        if self == offending:
            raise OSError("simulated unreadable file")
        return real_read_text(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)
    ok, offenders = tool.check_no_hardcoded_secrets(tmp_path)
    assert ok is True
    assert offenders == []


def test_check_health_endpoint_skips_unreadable_file_via_dangling_symlink(tmp_path):
    import os
    target = tmp_path / "missing_target.py"
    link = tmp_path / "broken_link.py"
    os.symlink(target, link)
    ok, detail = tool.check_health_endpoint(tmp_path)
    assert ok is False
    assert detail == "no /health route found"
