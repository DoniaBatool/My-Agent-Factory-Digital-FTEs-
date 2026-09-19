import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("vercel_deployer_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["vercel_deployer_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_parse_vercel_json_accepts_valid_config():
    assert tool.parse_vercel_json({"version": 2, "builds": [], "routes": []}) == []


def test_parse_vercel_json_rejects_bad_version():
    errors = tool.parse_vercel_json({"version": 5})
    assert any("version" in e for e in errors)


def test_parse_vercel_json_rejects_non_list_builds():
    errors = tool.parse_vercel_json({"builds": "not-a-list"})
    assert any("builds" in e for e in errors)


def test_build_env_var_diff_detects_add_remove_update():
    current = {"A": "1", "B": "2"}
    desired = {"A": "1", "B": "3", "C": "4"}
    diff = tool.build_env_var_diff(current, desired)
    assert diff["add"] == {"C": "4"}
    assert diff["remove"] == []
    assert diff["update"] == {"B": "3"}


def test_build_env_var_diff_detects_removal():
    current = {"A": "1", "STALE": "x"}
    desired = {"A": "1"}
    diff = tool.build_env_var_diff(current, desired)
    assert diff["remove"] == ["STALE"]


def test_generate_deploy_command_prod_flag():
    cmd = tool.generate_deploy_command("my-app", prod=True)
    assert "--prod" in cmd
    assert "my-app" in cmd


def test_generate_deploy_command_rejects_bad_project_name():
    with pytest.raises(ValueError):
        tool.generate_deploy_command("bad name; rm -rf /")


def test_check_build_output_dir_detects_nextjs_output():
    assert tool.check_build_output_dir([".next/server", "package.json"], "nextjs") is True


def test_check_build_output_dir_missing_output():
    assert tool.check_build_output_dir(["package.json"], "vite") is False


def test_check_build_output_dir_rejects_unknown_framework():
    with pytest.raises(ValueError):
        tool.check_build_output_dir([], "cobol-web")


def test_validate_domain_name_accepts_valid():
    assert tool.validate_domain_name("example.com") is True
    assert tool.validate_domain_name("sub.example.co.uk") is True


def test_validate_domain_name_rejects_invalid():
    assert tool.validate_domain_name("-bad.com") is False
    assert tool.validate_domain_name("no_tld") is False


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess as _subprocess_module
from pathlib import Path


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_parse_vercel_json_rejects_non_list_routes():
    errors = tool.parse_vercel_json({"routes": "not-a-list"})
    assert any("routes" in e for e in errors)


def test_parse_vercel_json_rejects_non_dict_env():
    errors = tool.parse_vercel_json({"env": ["not", "a", "dict"]})
    assert any("env" in e for e in errors)


def test_parse_vercel_json_accepts_version_boundaries_1_and_3():
    assert tool.parse_vercel_json({"version": 1}) == []
    assert tool.parse_vercel_json({"version": 3}) == []


def test_parse_vercel_json_accumulates_all_errors_at_once():
    errors = tool.parse_vercel_json({
        "version": 99, "builds": "x", "routes": "y", "env": "z",
    })
    assert len(errors) == 4


def test_parse_vercel_json_empty_config_has_no_errors():
    assert tool.parse_vercel_json({}) == []


def test_build_env_var_diff_empty_dicts_produce_empty_diff():
    diff = tool.build_env_var_diff({}, {})
    assert diff == {"add": {}, "remove": [], "update": {}}


def test_generate_deploy_command_default_has_no_prod_or_env_flag():
    cmd = tool.generate_deploy_command("my-app")
    assert "--prod" not in cmd
    assert "--env-file" not in cmd
    assert cmd == "vercel deploy --yes --name my-app"


def test_generate_deploy_command_includes_env_file_flag():
    cmd = tool.generate_deploy_command("my-app", env_file=".env.production")
    assert "--env-file .env.production" in cmd


def test_generate_deploy_command_rejects_empty_project_name():
    with pytest.raises(ValueError):
        tool.generate_deploy_command("")


def test_check_build_output_dir_detects_vite_cra_and_static():
    assert tool.check_build_output_dir(["dist/index.html"], "vite") is True
    assert tool.check_build_output_dir(["build/index.html"], "create-react-app") is True
    assert tool.check_build_output_dir(["public/index.html"], "static") is True


def test_check_build_output_dir_exact_match_without_trailing_slash():
    assert tool.check_build_output_dir([".next"], "nextjs") is True


def test_check_build_output_dir_does_not_match_partial_prefix():
    # "distant" starts with "dist" as a string but not as "dist" or "dist/..."
    assert tool.check_build_output_dir(["distant/file.js"], "vite") is False


def test_validate_domain_name_rejects_leading_or_trailing_dot():
    assert tool.validate_domain_name(".example.com") is False
    assert tool.validate_domain_name("example.com.") is False


def test_validate_domain_name_rejects_label_with_trailing_hyphen():
    assert tool.validate_domain_name("example-.com") is False


def test_validate_domain_name_rejects_label_with_leading_hyphen():
    assert tool.validate_domain_name("example.-com") is False


def test_print_success_outputs_checkmark_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_outputs_cross_and_message(capsys):
    tool.print_error("broken")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "broken" in out


def test_cmd_test_invokes_pytest_with_expected_args_and_returns_its_code(monkeypatch):
    captured = {}

    class _FakeCompletedProcess:
        returncode = 7

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return _FakeCompletedProcess()

    monkeypatch.setattr(_subprocess_module, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 7
    cmd = captured["cmd"]
    assert cmd[0] == sys.executable
    assert "-m" in cmd and "pytest" in cmd
    assert cmd[-1] == "-q"
    expected_tests_dir = str(Path(tool.__file__).resolve().parent.parent / "tests")
    assert expected_tests_dir in cmd


def test_main_test_command_dispatches_via_func_and_exits_with_code(monkeypatch):
    class _FakeCompletedProcess:
        returncode = 5

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: _FakeCompletedProcess())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 5


def test_main_missing_command_is_required_and_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_no_args_hits_main_guard_and_exits_nonzero():
    script = Path(tool.__file__).resolve()
    result = _subprocess_module.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "command" in result.stderr.lower() or "required" in result.stderr.lower()
