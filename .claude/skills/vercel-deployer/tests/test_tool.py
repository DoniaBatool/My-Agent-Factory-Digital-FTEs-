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
