import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("api_contract_design_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_build_path_spec_includes_success_and_error_codes():
    spec = tool.build_path_spec("get", "/tasks", "List tasks")
    responses = spec["/tasks"]["get"]["responses"]
    assert "200" in responses
    assert "404" in responses


def test_build_path_spec_post_requires_201():
    spec = tool.build_path_spec("post", "/tasks", "Create task")
    assert "201" in spec["/tasks"]["post"]["responses"]


def test_validate_contract_passes_for_complete_spec():
    spec = {"paths": tool.build_path_spec("get", "/tasks", "List tasks")}
    assert tool.validate_contract(spec) == []


def test_validate_contract_flags_missing_success_response():
    spec = {"paths": {"/tasks": {"post": {"responses": {"404": {}}}}}}
    violations = tool.validate_contract(spec)
    assert any("missing success response" in v for v in violations)


def test_validate_contract_flags_missing_error_response():
    spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}
    violations = tool.validate_contract(spec)
    assert any("4xx" in v for v in violations)


def test_check_breaking_change_detects_removed_endpoint():
    old_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}, "404": {}}}}}}
    new_spec = {"paths": {}}
    assert tool.check_breaking_change(old_spec, new_spec) == ["removed: GET /tasks"]


def test_check_breaking_change_detects_removed_response_code():
    old_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}, "404": {}}}}}}
    new_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}
    breaking = tool.check_breaking_change(old_spec, new_spec)
    assert any("404" in b for b in breaking)


def test_check_breaking_change_no_change_is_clean():
    spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}
    assert tool.check_breaking_change(spec, spec) == []
