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


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys
from types import SimpleNamespace
import pytest


def test_error_description_unknown_code_returns_generic_error():
    assert tool._error_description("999") == "Error"


def test_error_description_known_codes():
    assert tool._error_description("403") == "Forbidden"
    assert tool._error_description("500") == "Internal Server Error"


def test_build_path_spec_uppercase_method_is_normalized_to_lowercase():
    spec = tool.build_path_spec("GET", "/tasks", "List tasks")
    assert "get" in spec["/tasks"]
    assert "200" in spec["/tasks"]["get"]["responses"]


def test_build_path_spec_unknown_method_defaults_to_200():
    spec = tool.build_path_spec("patch", "/tasks", "Patch task")
    assert "200" in spec["/tasks"]["patch"]["responses"]


def test_build_path_spec_delete_requires_204():
    spec = tool.build_path_spec("delete", "/tasks/1", "Delete task")
    assert "204" in spec["/tasks/1"]["delete"]["responses"]


def test_build_path_spec_put_requires_200():
    spec = tool.build_path_spec("put", "/tasks/1", "Update task")
    assert "200" in spec["/tasks/1"]["put"]["responses"]


def test_build_path_spec_embeds_custom_response_schema():
    schema = {"type": "object", "properties": {"id": {"type": "string"}}}
    spec = tool.build_path_spec("get", "/tasks", "List tasks", response_schema=schema)
    assert spec["/tasks"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == schema


def test_build_path_spec_defaults_schema_to_empty_dict():
    spec = tool.build_path_spec("get", "/tasks", "List tasks")
    assert spec["/tasks"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {}


def test_build_path_spec_custom_error_codes_replace_defaults():
    spec = tool.build_path_spec("get", "/tasks", "List tasks", error_codes=("403", "500"))
    responses = spec["/tasks"]["get"]["responses"]
    assert "403" in responses and "500" in responses
    assert "401" not in responses


def test_validate_contract_empty_spec_has_no_violations():
    assert tool.validate_contract({}) == []


def test_validate_contract_unknown_method_defaults_to_200_requirement():
    spec = {"paths": {"/tasks": {"patch": {"responses": {"404": {}}}}}}
    violations = tool.validate_contract(spec)
    assert any("missing success response" in v for v in violations)


def test_check_breaking_change_detects_removed_method_on_kept_path():
    old_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}, "post": {"responses": {"201": {}}}}}}
    new_spec = {"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}
    breaking = tool.check_breaking_change(old_spec, new_spec)
    assert breaking == ["removed: POST /tasks"]


def test_check_breaking_change_empty_old_spec_is_clean():
    assert tool.check_breaking_change({}, {"paths": {"/tasks": {"get": {"responses": {}}}}}) == []


def test_cmd_build_path_spec_prints_json(capsys):
    args = SimpleNamespace(method="get", path="/tasks", summary="List tasks")
    rc = tool.cmd_build_path_spec(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert "200" in data["/tasks"]["get"]["responses"]


def test_cmd_validate_contract_complete_spec_returns_zero(tmp_path, capsys):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"paths": tool.build_path_spec("get", "/tasks", "List tasks")}))
    args = SimpleNamespace(spec_file=str(spec_file))
    rc = tool.cmd_validate_contract(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_validate_contract_with_violations_prints_them_and_returns_one(tmp_path, capsys):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}}))
    args = SimpleNamespace(spec_file=str(spec_file))
    rc = tool.cmd_validate_contract(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "4xx" in out


def test_cmd_validate_contract_malformed_json_raises(tmp_path):
    spec_file = tmp_path / "bad.json"
    spec_file.write_text("not json")
    args = SimpleNamespace(spec_file=str(spec_file))
    with pytest.raises(json.JSONDecodeError):
        tool.cmd_validate_contract(args)


def test_cmd_check_breaking_change_detects_and_returns_one(tmp_path, capsys):
    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    old_file.write_text(json.dumps({"paths": {"/tasks": {"get": {"responses": {"200": {}, "404": {}}}}}}))
    new_file.write_text(json.dumps({"paths": {}}))
    args = SimpleNamespace(old=str(old_file), new=str(new_file))
    rc = tool.cmd_check_breaking_change(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "removed" in out


def test_cmd_check_breaking_change_no_changes_returns_zero(tmp_path, capsys):
    content = json.dumps({"paths": {"/tasks": {"get": {"responses": {"200": {}}}}}})
    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    old_file.write_text(content)
    new_file.write_text(content)
    args = SimpleNamespace(old=str(old_file), new=str(new_file))
    rc = tool.cmd_check_breaking_change(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_test_returns_zero_and_prints_pass(capsys):
    rc = tool.cmd_test(SimpleNamespace())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_dispatches_build_path_spec_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "build-path-spec", "--method", "get", "--path", "/tasks", "--summary", "List tasks"],
    )
    rc = tool.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert "200" in data["/tasks"]["get"]["responses"]


def test_main_dispatches_validate_contract_end_to_end(monkeypatch, capsys, tmp_path):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"paths": tool.build_path_spec("get", "/tasks", "List tasks")}))
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-contract", str(spec_file)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_main_dispatches_check_breaking_change_end_to_end(monkeypatch, capsys, tmp_path):
    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    old_file.write_text(json.dumps({"paths": {"/tasks": {"get": {"responses": {"200": {}, "404": {}}}}}}))
    new_file.write_text(json.dumps({"paths": {}}))
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-breaking-change", "--old", str(old_file), "--new", str(new_file)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "removed" in out


def test_main_dispatches_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_one(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage" in captured.out.lower()


def test_main_build_path_spec_missing_required_method_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-path-spec", "--path", "/tasks", "--summary", "List tasks"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_build_path_spec_missing_required_path_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-path-spec", "--method", "get", "--summary", "List tasks"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_build_path_spec_missing_required_summary_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-path-spec", "--method", "get", "--path", "/tasks"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_validate_contract_missing_positional_spec_file_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-contract"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_breaking_change_missing_required_old_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-breaking-change", "--new", "new.json"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_breaking_change_missing_required_new_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-breaking-change", "--old", "old.json"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    from pathlib import Path as _Path
    script = _Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([sys.executable, str(script), "test"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "SELF-TEST PASS" in proc.stdout
