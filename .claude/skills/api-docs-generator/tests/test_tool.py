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
