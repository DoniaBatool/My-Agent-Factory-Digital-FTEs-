import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("graphql_api_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_build_type_sdl_produces_valid_shape():
    sdl = tool.build_type_sdl("Task", {"id": "ID!", "title": "String!"})
    assert sdl == "type Task {\n  id: ID!\n  title: String!\n}"


def test_build_schema_sdl_includes_all_types_and_query():
    sdl = tool.build_schema_sdl({"Task": {"id": "ID!"}}, {"tasks": "[Task!]!"})
    assert "type Task {" in sdl
    assert "type Query {" in sdl
    assert "tasks: [Task!]!" in sdl


def test_check_n_plus_one_detects_service_call_in_loop():
    source = "def resolve_tasks(root):\n    result = []\n    for uid in user_ids:\n        result.append(user_service.get(uid))\n    return result\n"
    findings = tool.check_n_plus_one_risk(source)
    assert len(findings) == 1


def test_check_n_plus_one_clean_for_batched_query():
    source = "def resolve_tasks(root):\n    return task_service.get_all(user_ids)\n"
    assert tool.check_n_plus_one_risk(source) == []


def test_check_n_plus_one_ignores_loop_without_service_call():
    source = "def total(items):\n    s = 0\n    for x in items:\n        s += x\n    return s\n"
    assert tool.check_n_plus_one_risk(source) == []
