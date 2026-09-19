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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_build_type_sdl_empty_fields_produces_empty_body():
    sdl = tool.build_type_sdl("Empty", {})
    assert sdl == "type Empty {\n}"


def test_build_schema_sdl_multiple_types_and_empty_query_fields():
    sdl = tool.build_schema_sdl({"A": {"x": "Int"}, "B": {"y": "String"}}, {})
    assert "type A {" in sdl
    assert "type B {" in sdl
    assert sdl.endswith("type Query {\n}\n")


def test_check_n_plus_one_is_case_sensitive_uppercase_call_not_flagged():
    source = "def resolve_tasks(root):\n    result = []\n    for uid in user_ids:\n        result.append(user_service.GET(uid))\n    return result\n"
    assert tool.check_n_plus_one_risk(source) == []


def test_check_n_plus_one_matches_query_and_fetch_verbs_too():
    query_source = "def r(root):\n    for x in xs:\n        y = svc.query(x)\n"
    fetch_source = "def r(root):\n    for x in xs:\n        y = svc.fetch(x)\n"
    assert len(tool.check_n_plus_one_risk(query_source)) == 1
    assert len(tool.check_n_plus_one_risk(fetch_source)) == 1


def test_check_n_plus_one_detects_multiple_separate_loops():
    # loops separated by a non-indented line (a fresh def) so the
    # regex body-capture does not greedily merge them into one match
    source = (
        "def r(root):\n"
        "    for a in a_ids:\n"
        "        x = a_service.get(a)\n"
        "\n"
        "def r2(root):\n"
        "    for b in b_ids:\n"
        "        y = b_service.get(b)\n"
    )
    findings = tool.check_n_plus_one_risk(source)
    assert len(findings) == 2


def test_check_n_plus_one_adjacent_same_indent_loops_merge_into_one_match():
    # documents the real (greedy) behavior of the body-capture group: two
    # for-loops back-to-back at the same indent with no separating
    # non-indented line are swallowed into a single regex match, so this
    # heuristic reports one finding, not two, for that shape.
    source = (
        "def r(root):\n"
        "    for a in a_ids:\n"
        "        x = a_service.get(a)\n"
        "    for b in b_ids:\n"
        "        y = b_service.get(b)\n"
    )
    findings = tool.check_n_plus_one_risk(source)
    assert len(findings) == 1


def test_check_n_plus_one_word_boundary_getxyz_still_matches_get_prefix():
    # \w* after (get|query|fetch) means a longer method name like get_by_id
    # must still be caught, not just an exact "get(" call.
    source = "def r(root):\n    for x in xs:\n        y = svc.get_by_id(x)\n"
    assert len(tool.check_n_plus_one_risk(source)) == 1


def test_cmd_build_sdl_prints_schema_and_returns_0(capsys):
    args = _Args(types=json.dumps({"Task": {"id": "ID!"}}), query_fields=json.dumps({"tasks": "[Task!]!"}))
    rc = tool.cmd_build_sdl(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "type Task {" in out
    assert "tasks: [Task!]!" in out


def test_cmd_build_sdl_malformed_types_json_raises():
    args = _Args(types="not-json", query_fields="{}")
    try:
        tool.cmd_build_sdl(args)
        assert False, "expected a JSON decode error"
    except json.JSONDecodeError:
        pass


def test_cmd_check_n_plus_one_reports_findings_and_returns_1(tmp_path, capsys):
    src = tmp_path / "resolver.py"
    src.write_text("def r(root):\n    for uid in ids:\n        x = svc.get(uid)\n")
    args = _Args(path=str(src))
    rc = tool.cmd_check_n_plus_one(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "possible N+1" in out


def test_cmd_check_n_plus_one_clean_file_returns_0(tmp_path, capsys):
    src = tmp_path / "resolver.py"
    src.write_text("def r(root):\n    return svc.get_all(ids)\n")
    args = _Args(path=str(src))
    rc = tool.cmd_check_n_plus_one(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK: no obvious N+1" in out


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


def test_main_build_sdl_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "build-sdl",
        "--types", json.dumps({"Task": {"id": "ID!"}}),
        "--query-fields", json.dumps({"tasks": "[Task!]!"}),
    ])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "type Task {" in out


def test_main_check_n_plus_one_end_to_end(monkeypatch, tmp_path, capsys):
    src = tmp_path / "resolver.py"
    src.write_text("def r(root):\n    return svc.get_all(ids)\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-n-plus-one", str(src)])
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


def test_main_build_sdl_missing_required_types_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-sdl", "--query-fields", "{}"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --types"
    except SystemExit as e:
        assert e.code == 2


def test_main_build_sdl_missing_required_query_fields_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-sdl", "--types", "{}"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --query-fields"
    except SystemExit as e:
        assert e.code == 2


def test_main_check_n_plus_one_missing_positional_path_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-n-plus-one"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing positional path"
    except SystemExit as e:
        assert e.code == 2


def test_subprocess_runs_as_script_and_exercises_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "build-sdl", "--types", json.dumps({"Task": {"id": "ID!"}}), "--query-fields", json.dumps({"tasks": "[Task!]!"})],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "type Task {" in result.stdout
