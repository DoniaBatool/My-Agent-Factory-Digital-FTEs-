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
