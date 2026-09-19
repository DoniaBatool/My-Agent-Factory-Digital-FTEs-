import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("infrastructure_as_code_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_generate_s3_bucket_includes_bucket_name():
    hcl = tool.generate_s3_bucket("data", "my-app-data-bucket")
    assert 'bucket = "my-app-data-bucket"' in hcl


def test_generate_s3_bucket_includes_versioning_when_enabled():
    hcl = tool.generate_s3_bucket("data", "b", versioning=True)
    assert "versioning_configuration" in hcl


def test_generate_s3_bucket_omits_versioning_when_disabled():
    hcl = tool.generate_s3_bucket("data", "b", versioning=False)
    assert "versioning_configuration" not in hcl


def test_generate_s3_bucket_rejects_invalid_resource_name():
    try:
        tool.generate_s3_bucket("123-bad-start", "b")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_generate_vpc_includes_cidr_block():
    hcl = tool.generate_vpc("main", "10.0.0.0/16")
    assert '"10.0.0.0/16"' in hcl


def test_generate_vpc_rejects_invalid_cidr():
    try:
        tool.generate_vpc("main", "not-a-cidr")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validate_required_variables_flags_missing_and_empty():
    missing = tool.validate_required_variables(["region", "project_name", "env"], {"region": "us-east-1", "env": ""})
    assert missing == ["project_name", "env"]

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_validate_hcl_identifier_accepts_valid_names():
    assert tool.validate_hcl_identifier("a") is True
    assert tool.validate_hcl_identifier("my_bucket-01") is True
    assert tool.validate_hcl_identifier("Data2") is True


def test_validate_hcl_identifier_rejects_leading_digit():
    assert tool.validate_hcl_identifier("1bucket") is False


def test_validate_hcl_identifier_rejects_special_characters():
    assert tool.validate_hcl_identifier("bad.name") is False
    assert tool.validate_hcl_identifier("bad name") is False
    assert tool.validate_hcl_identifier("") is False


def test_generate_s3_bucket_includes_encryption_when_enabled():
    hcl = tool.generate_s3_bucket("data", "b", versioning=False, encrypted=True)
    assert "aws_s3_bucket_server_side_encryption_configuration" in hcl
    assert "AES256" in hcl


def test_generate_s3_bucket_omits_encryption_when_disabled():
    hcl = tool.generate_s3_bucket("data", "b", versioning=False, encrypted=False)
    assert "aws_s3_bucket_server_side_encryption_configuration" not in hcl


def test_generate_s3_bucket_both_disabled_produces_minimal_hcl():
    hcl = tool.generate_s3_bucket("data", "b", versioning=False, encrypted=False)
    assert "versioning_configuration" not in hcl
    assert "server_side_encryption" not in hcl
    assert 'resource "aws_s3_bucket" "data"' in hcl


def test_generate_vpc_custom_subnet_count():
    hcl = tool.generate_vpc("main", "10.0.0.0/16", num_public_subnets=5)
    assert "count      = 5" in hcl


def test_generate_vpc_rejects_invalid_resource_name():
    try:
        tool.generate_vpc("9bad", "10.0.0.0/16")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validate_required_variables_all_present_returns_empty_list():
    missing = tool.validate_required_variables(["region"], {"region": "us-east-1"})
    assert missing == []


def test_cmd_generate_s3_bucket_success_returns_0(capsys):
    args = _Args(resource_name="data", bucket_name="my-bucket", no_versioning=False, no_encryption=False)
    rc = tool.cmd_generate_s3_bucket(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "versioning_configuration" in out
    assert "server_side_encryption" in out


def test_cmd_generate_s3_bucket_flags_disable_features(capsys):
    args = _Args(resource_name="data", bucket_name="my-bucket", no_versioning=True, no_encryption=True)
    rc = tool.cmd_generate_s3_bucket(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "versioning_configuration" not in out
    assert "server_side_encryption" not in out


def test_cmd_generate_s3_bucket_invalid_name_returns_1(capsys):
    args = _Args(resource_name="1bad", bucket_name="b", no_versioning=False, no_encryption=False)
    rc = tool.cmd_generate_s3_bucket(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid Terraform resource name" in out


def test_cmd_generate_vpc_success_returns_0(capsys):
    args = _Args(resource_name="main", cidr="10.0.0.0/16", public_subnets=3)
    rc = tool.cmd_generate_vpc(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "count      = 3" in out


def test_cmd_generate_vpc_invalid_cidr_returns_1(capsys):
    args = _Args(resource_name="main", cidr="nope", public_subnets=2)
    rc = tool.cmd_generate_vpc(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid CIDR block" in out


def test_cmd_validate_variables_all_present_returns_0(capsys):
    args = _Args(required="region,project", provided=json.dumps({"region": "x", "project": "y"}))
    rc = tool.cmd_validate_variables(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_validate_variables_missing_returns_1(capsys):
    args = _Args(required="region,project", provided=json.dumps({"region": "x"}))
    rc = tool.cmd_validate_variables(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "MISSING: project" in out


def test_cmd_validate_variables_malformed_json_raises():
    args = _Args(required="region", provided="not-json")
    try:
        tool.cmd_validate_variables(args)
        assert False, "expected a JSON decode error"
    except json.JSONDecodeError:
        pass


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_generate_s3_bucket_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "generate-s3-bucket",
        "--resource-name", "data", "--bucket-name", "my-bucket",
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert 'resource "aws_s3_bucket" "data"' in out


def test_main_generate_vpc_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "generate-vpc", "--resource-name", "main", "--cidr", "10.0.0.0/16",
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert '"10.0.0.0/16"' in out


def test_main_validate_variables_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "validate-variables", "--required", "region", "--provided", json.dumps({"region": "x"}),
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_generate_s3_bucket_missing_required_resource_name_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-s3-bucket", "--bucket-name", "b"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --resource-name"
    except SystemExit as e:
        assert e.code == 2


def test_main_generate_s3_bucket_missing_required_bucket_name_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-s3-bucket", "--resource-name", "data"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --bucket-name"
    except SystemExit as e:
        assert e.code == 2


def test_main_generate_vpc_missing_required_cidr_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-vpc", "--resource-name", "main"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --cidr"
    except SystemExit as e:
        assert e.code == 2


def test_main_validate_variables_missing_required_flag_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-variables", "--provided", "{}"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --required"
    except SystemExit as e:
        assert e.code == 2


def test_main_validate_variables_missing_provided_flag_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-variables", "--required", "region"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --provided"
    except SystemExit as e:
        assert e.code == 2


def test_subprocess_runs_as_script_and_exercises_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "generate-vpc", "--resource-name", "main", "--cidr", "10.0.0.0/16"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert '"10.0.0.0/16"' in result.stdout


def test_generate_s3_bucket_defaults_include_both_versioning_and_encryption():
    # calls with no versioning/encrypted kwargs at all, relying on their
    # True defaults, to pin down the default values themselves (not just
    # explicit True/False call sites).
    hcl = tool.generate_s3_bucket("data", "my-app-data-bucket")
    assert "versioning_configuration" in hcl
    assert "server_side_encryption" in hcl


def test_main_generate_vpc_missing_required_resource_name_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-vpc", "--cidr", "10.0.0.0/16"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --resource-name"
    except SystemExit as e:
        assert e.code == 2
