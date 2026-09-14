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
