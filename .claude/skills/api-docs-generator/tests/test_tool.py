import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("api_docs_generator_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)

SAMPLE_SOURCE = (
    "@app.get('/tasks')\n"
    "async def list_tasks():\n"
    "    return []\n\n"
    "@app.post('/tasks')\n"
    "async def create_task(payload: TaskCreate):\n"
    "    return payload\n\n"
    "@app.delete('/tasks/{id}')\n"
    "async def delete_task(id: str):\n"
    "    return None\n"
)


def test_extract_routes_finds_all_three_routes():
    routes = tool.extract_routes(SAMPLE_SOURCE)
    assert len(routes) == 3


def test_extract_routes_captures_method_and_path():
    routes = tool.extract_routes(SAMPLE_SOURCE)
    assert routes[0]["method"] == "GET"
    assert routes[0]["path"] == "/tasks"


def test_extract_routes_pairs_decorator_with_handler_name():
    routes = tool.extract_routes(SAMPLE_SOURCE)
    assert routes[1]["handler"] == "create_task"


def test_extract_routes_handles_path_params():
    routes = tool.extract_routes(SAMPLE_SOURCE)
    delete_route = next(r for r in routes if r["method"] == "DELETE")
    assert delete_route["path"] == "/tasks/{id}"


def test_extract_routes_empty_source_returns_empty_list():
    assert tool.extract_routes("x = 1\n") == []


def test_generate_markdown_docs_produces_table_with_all_routes():
    routes = tool.extract_routes(SAMPLE_SOURCE)
    docs = tool.generate_markdown_docs(routes)
    assert docs.count("|") > 0
    assert "list_tasks" in docs
    assert "create_task" in docs
    assert "delete_task" in docs


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys
from types import SimpleNamespace
import pytest


def test_extract_routes_handler_none_when_no_def_follows():
    source = "@app.get('/tasks')\nx = 1\ny = 2\nz = 3\nw = 4\n"
    routes = tool.extract_routes(source)
    assert routes == [{"method": "GET", "path": "/tasks", "handler": None}]


def test_extract_routes_finds_handler_at_boundary_of_search_window():
    # decorator on line 0; def on line 4 (i+4) is the last line the search
    # window checks (range(i+1, min(i+5, len(lines))) -> j up to i+4).
    source = "@app.get('/tasks')\n#c1\n#c2\n#c3\ndef list_tasks():\n    return []\n"
    routes = tool.extract_routes(source)
    assert routes[0]["handler"] == "list_tasks"


def test_extract_routes_misses_handler_just_outside_search_window():
    # def on line 5 (i+5) is one line past what the window checks -> handler
    # must come back None even though a def does eventually follow.
    source = "@app.get('/tasks')\n#c1\n#c2\n#c3\n#c4\ndef list_tasks():\n    return []\n"
    routes = tool.extract_routes(source)
    assert routes[0]["handler"] is None


def test_extract_routes_supports_double_quoted_decorator():
    source = '@app.get("/tasks")\ndef list_tasks():\n    return []\n'
    routes = tool.extract_routes(source)
    assert routes == [{"method": "GET", "path": "/tasks", "handler": "list_tasks"}]


def test_extract_routes_supports_sync_def():
    source = "@app.put('/tasks/{id}')\ndef update_task(id):\n    return None\n"
    routes = tool.extract_routes(source)
    assert routes[0]["handler"] == "update_task"


def test_extract_routes_supports_patch_method():
    source = "@app.patch('/tasks/{id}')\nasync def patch_task(id):\n    return None\n"
    routes = tool.extract_routes(source)
    assert routes[0]["method"] == "PATCH"


def test_generate_markdown_docs_shows_unknown_for_missing_handler():
    routes = [{"method": "GET", "path": "/tasks", "handler": None}]
    docs = tool.generate_markdown_docs(routes)
    assert "(unknown)" in docs


def test_generate_markdown_docs_empty_routes_still_has_header():
    docs = tool.generate_markdown_docs([])
    assert docs.startswith("# API Reference")
    assert docs.endswith("\n")


def test_cmd_extract_routes_returns_zero_when_routes_found(tmp_path, capsys):
    src_file = tmp_path / "app.py"
    src_file.write_text("@app.get('/tasks')\ndef list_tasks():\n    return []\n")
    args = SimpleNamespace(path=str(src_file))
    rc = tool.cmd_extract_routes(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data[0]["handler"] == "list_tasks"


def test_cmd_extract_routes_returns_one_when_no_routes_found(tmp_path, capsys):
    src_file = tmp_path / "app.py"
    src_file.write_text("x = 1\n")
    args = SimpleNamespace(path=str(src_file))
    rc = tool.cmd_extract_routes(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert json.loads(out) == []


def test_cmd_extract_routes_missing_file_raises_file_not_found():
    args = SimpleNamespace(path="/no/such/file/app.py")
    with pytest.raises(FileNotFoundError):
        tool.cmd_extract_routes(args)


def test_cmd_generate_docs_without_output_prints_docs(tmp_path, capsys):
    src_file = tmp_path / "app.py"
    src_file.write_text("@app.get('/tasks')\ndef list_tasks():\n    return []\n")
    args = SimpleNamespace(path=str(src_file), output=None)
    rc = tool.cmd_generate_docs(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "list_tasks" in out
    assert "# API Reference" in out


def test_cmd_generate_docs_with_output_writes_file_and_reports_count(tmp_path, capsys):
    src_file = tmp_path / "app.py"
    src_file.write_text("@app.get('/tasks')\ndef list_tasks():\n    return []\n")
    out_file = tmp_path / "docs.md"
    args = SimpleNamespace(path=str(src_file), output=str(out_file))
    rc = tool.cmd_generate_docs(args)
    printed = capsys.readouterr().out
    assert rc == 0
    assert "Wrote" in printed
    assert "1 routes" in printed
    assert out_file.exists()
    assert "list_tasks" in out_file.read_text()


def test_cmd_test_returns_zero_and_prints_pass(capsys):
    rc = tool.cmd_test(SimpleNamespace())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_dispatches_extract_routes_end_to_end(monkeypatch, capsys, tmp_path):
    src_file = tmp_path / "app.py"
    src_file.write_text("@app.get('/tasks')\ndef list_tasks():\n    return []\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "extract-routes", str(src_file)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out)[0]["handler"] == "list_tasks"


def test_main_dispatches_generate_docs_end_to_end(monkeypatch, capsys, tmp_path):
    src_file = tmp_path / "app.py"
    src_file.write_text("@app.get('/tasks')\ndef list_tasks():\n    return []\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-docs", str(src_file)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "list_tasks" in out


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


def test_main_extract_routes_missing_positional_path_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "extract-routes"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_generate_docs_missing_positional_path_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-docs"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    from pathlib import Path as _Path
    script = _Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([sys.executable, str(script), "test"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "SELF-TEST PASS" in proc.stdout
