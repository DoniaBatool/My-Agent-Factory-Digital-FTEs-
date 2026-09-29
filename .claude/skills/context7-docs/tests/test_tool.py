import importlib.util as _ilu
import json
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "context7_docs_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def _isolate_config_paths(monkeypatch, tmp_path):
    """Point both candidate .mcp.json locations at a fresh, empty tmp_path
    tree so _load_api_key never accidentally reads this repo's own
    .claude/.mcp.json or the real user's home directory."""
    fake_module_path = tmp_path / "fake_repo" / ".claude" / "skills" / "context7-docs" / "scripts" / "tool.py"
    monkeypatch.setattr(tool, "__file__", str(fake_module_path))
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tool.Path, "home", classmethod(lambda cls: fake_home))
    return fake_module_path, fake_home


# ---------------------------------------------------------------------------
# Context7Client.__init__
# ---------------------------------------------------------------------------

def test_init_uses_explicit_api_key_without_touching_disk(monkeypatch):
    def boom():
        raise AssertionError("_load_api_key should not be called when api_key is given")

    monkeypatch.setattr(tool.Context7Client, "_load_api_key", lambda self: boom())
    client = tool.Context7Client(api_key="explicit-key-123")
    assert client.api_key == "explicit-key-123"


def test_init_raises_value_error_when_no_config_found_anywhere(monkeypatch, tmp_path):
    _isolate_config_paths(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


# ---------------------------------------------------------------------------
# Context7Client._load_api_key
# ---------------------------------------------------------------------------

def test_load_api_key_reads_from_first_candidate_path(monkeypatch, tmp_path):
    fake_module_path, fake_home = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["-y", "@upstash/context7-mcp", "--api-key", "KEY-FROM-FIRST"]}}
    }))
    client = tool.Context7Client(api_key=None)
    assert client.api_key == "KEY-FROM-FIRST"


def test_load_api_key_falls_back_to_home_candidate_when_first_missing(monkeypatch, tmp_path):
    _isolate_config_paths(monkeypatch, tmp_path)  # first candidate's dir is never created
    home_candidate = tool.Path.home() / ".claude" / ".mcp.json"
    home_candidate.parent.mkdir(parents=True, exist_ok=True)
    home_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["--api-key", "KEY-FROM-HOME"]}}
    }))
    client = tool.Context7Client(api_key=None)
    assert client.api_key == "KEY-FROM-HOME"


def test_load_api_key_skips_invalid_json_and_falls_through_to_next_candidate(monkeypatch, tmp_path):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text("{not valid json::")
    home_candidate = tool.Path.home() / ".claude" / ".mcp.json"
    home_candidate.parent.mkdir(parents=True, exist_ok=True)
    home_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["--api-key", "KEY-FROM-HOME-AFTER-BAD-JSON"]}}
    }))
    client = tool.Context7Client(api_key=None)
    assert client.api_key == "KEY-FROM-HOME-AFTER-BAD-JSON"


def test_load_api_key_raises_when_args_missing_api_key_flag(monkeypatch, tmp_path):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["-y", "@upstash/context7-mcp"]}}
    }))
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def test_load_api_key_raises_when_api_key_flag_is_last_arg_with_no_value(monkeypatch, tmp_path):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["-y", "--api-key"]}}
    }))
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def test_load_api_key_raises_when_context7_server_not_configured(monkeypatch, tmp_path):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({"mcpServers": {"other-server": {"args": []}}}))
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def _write_malformed_mcp_servers_and_home_fallback(monkeypatch, tmp_path, bad_mcp_servers):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({"mcpServers": bad_mcp_servers}))
    home_candidate = tool.Path.home() / ".claude" / ".mcp.json"
    home_candidate.parent.mkdir(parents=True, exist_ok=True)
    home_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["--api-key", "KEY-FROM-HOME-AFTER-MALFORMED"]}}
    }))
    return tool.Context7Client(api_key=None)


# Regression tests for a real bug: the except clause used to only catch
# (json.JSONDecodeError, KeyError), so a config file whose "mcpServers" value
# is present but not a dict (a list, a string, or null/None) made
# `.get("context7", {})` raise an uncaught AttributeError instead of falling
# through to the next candidate path. The except clause now also catches
# AttributeError, so each malformed candidate below is skipped and the next
# candidate (here, the home one) is tried instead.

def test_load_api_key_falls_through_when_mcp_servers_is_a_list(monkeypatch, tmp_path):
    client = _write_malformed_mcp_servers_and_home_fallback(monkeypatch, tmp_path, ["not", "a", "dict"])
    assert client.api_key == "KEY-FROM-HOME-AFTER-MALFORMED"


def test_load_api_key_falls_through_when_mcp_servers_is_a_string(monkeypatch, tmp_path):
    client = _write_malformed_mcp_servers_and_home_fallback(monkeypatch, tmp_path, "not-a-dict")
    assert client.api_key == "KEY-FROM-HOME-AFTER-MALFORMED"


def test_load_api_key_falls_through_when_mcp_servers_is_null(monkeypatch, tmp_path):
    client = _write_malformed_mcp_servers_and_home_fallback(monkeypatch, tmp_path, None)
    assert client.api_key == "KEY-FROM-HOME-AFTER-MALFORMED"


def _write_only_malformed_mcp_servers(monkeypatch, tmp_path, bad_mcp_servers):
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({"mcpServers": bad_mcp_servers}))


# Same malformed shapes as above, but with no other candidate path to fall
# through to: this must end in the tool's own clean ValueError, never an
# uncaught AttributeError.

def test_load_api_key_raises_clean_value_error_when_only_malformed_list_found(monkeypatch, tmp_path):
    _write_only_malformed_mcp_servers(monkeypatch, tmp_path, ["not", "a", "dict"])
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def test_load_api_key_raises_clean_value_error_when_only_malformed_string_found(monkeypatch, tmp_path):
    _write_only_malformed_mcp_servers(monkeypatch, tmp_path, "not-a-dict")
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def test_load_api_key_raises_clean_value_error_when_only_malformed_null_found(monkeypatch, tmp_path):
    _write_only_malformed_mcp_servers(monkeypatch, tmp_path, None)
    with pytest.raises(ValueError, match="Context7 API key not found"):
        tool.Context7Client(api_key=None)


def test_load_api_key_still_extracts_key_from_well_formed_mcp_servers_dict(monkeypatch, tmp_path):
    # Confirms the normal, well-formed case is unaffected by the added
    # AttributeError handling: a proper dict "mcpServers" value still
    # extracts the API key directly, with no fallthrough needed.
    fake_module_path, _ = _isolate_config_paths(monkeypatch, tmp_path)
    first_candidate = fake_module_path.parent.parent.parent.parent / ".mcp.json"
    first_candidate.parent.mkdir(parents=True, exist_ok=True)
    first_candidate.write_text(json.dumps({
        "mcpServers": {"context7": {"args": ["--api-key", "KEY-FROM-WELL-FORMED-DICT"]}}
    }))
    client = tool.Context7Client(api_key=None)
    assert client.api_key == "KEY-FROM-WELL-FORMED-DICT"


# ---------------------------------------------------------------------------
# Context7Client.resolve_library
# ---------------------------------------------------------------------------

def test_resolve_library_returns_expected_structure():
    client = tool.Context7Client(api_key="k")
    result = client.resolve_library("fastapi")
    assert result == {
        "library": "fastapi",
        "status": "resolved",
        "message": "Ready to search fastapi documentation",
    }


def test_resolve_library_handles_empty_string_name():
    client = tool.Context7Client(api_key="k")
    result = client.resolve_library("")
    assert result["library"] == ""
    assert result["status"] == "resolved"
    assert "Ready to search  documentation" in result["message"]


# ---------------------------------------------------------------------------
# Context7Client.search_docs
# ---------------------------------------------------------------------------

def test_search_docs_returns_expected_structure_with_default_max_tokens():
    client = tool.Context7Client(api_key="k")
    result = client.search_docs("nextjs", "app router")
    assert result["library"] == "nextjs"
    assert result["query"] == "app router"
    assert result["max_tokens"] == 5000
    assert result["mcp_tool"] == "get-library-docs"
    assert "resolve-library-id" in result["instructions"]
    assert "get-library-docs" in result["instructions"]
    assert '"libraryName": "nextjs"' in result["instructions"]
    assert '"topic": "app router"' in result["instructions"]
    assert '"tokens": 5000' in result["instructions"]


def test_search_docs_honors_custom_max_tokens():
    client = tool.Context7Client(api_key="k")
    result = client.search_docs("helm", "charts", max_tokens=1234)
    assert result["max_tokens"] == 1234
    assert '"tokens": 1234' in result["instructions"]


def test_search_docs_handles_empty_query():
    client = tool.Context7Client(api_key="k")
    result = client.search_docs("django", "")
    assert result["query"] == ""
    assert '"topic": ""' in result["instructions"]


# ---------------------------------------------------------------------------
# main() / CLI
# ---------------------------------------------------------------------------

def test_main_missing_required_library_arg_exits(monkeypatch):
    # --api-key is supplied so a real run (if argparse's required=True were
    # somehow disabled) would complete normally instead of failing for an
    # unrelated reason (missing API key) -- this isolates the assertion to
    # argparse's own required-argument enforcement for --library. Exit code
    # 2 is argparse's own usage-error code (distinct from the tool's own
    # error handling, which always exits 1), so this pins the failure to
    # argument parsing rather than some downstream crash coincidentally
    # also raising SystemExit.
    monkeypatch.setattr(_sys, "argv", ["tool.py", "--query", "q", "--api-key", "k"])
    with pytest.raises(SystemExit) as exc_info:
        tool.main()
    assert exc_info.value.code == 2


def test_main_missing_required_query_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "--library", "fastapi", "--api-key", "k"])
    with pytest.raises(SystemExit) as exc_info:
        tool.main()
    assert exc_info.value.code == 2


def test_main_prints_human_readable_box_by_default(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "--library", "fastapi", "--query", "dependency injection", "--api-key", "explicit-key",
    ])
    tool.main()
    out = capsys.readouterr().out
    assert "Context7 Documentation Lookup" in out
    assert "Library: fastapi" in out
    assert "Query: dependency injection" in out
    assert "Max Tokens: 5000" in out
    assert "resolve-library-id" in out


def test_main_prints_json_when_json_flag_set(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "--library", "helm", "--query", "chart templates", "--api-key", "k", "--json",
    ])
    tool.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["library"] == "helm"
    assert payload["query"] == "chart templates"
    assert payload["resolve"]["status"] == "resolved"
    assert payload["search"]["mcp_tool"] == "get-library-docs"


def test_main_honors_custom_max_tokens_flag(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "-l", "kubernetes", "-q", "deployment yaml", "-k", "k", "-t", "9999", "-j",
    ])
    tool.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["search"]["max_tokens"] == 9999


def test_main_short_flags_behave_like_long_flags(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "-l", "react", "-q", "hooks", "-k", "k"])
    tool.main()
    out = capsys.readouterr().out
    assert "Library: react" in out
    assert "Query: hooks" in out


def test_main_reports_value_error_and_exits_1_when_api_key_missing(monkeypatch, tmp_path, capsys):
    _isolate_config_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "--library", "fastapi", "--query", "q"])
    with pytest.raises(SystemExit) as exc_info:
        tool.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "Context7 API key not found" in err


def test_main_reports_unexpected_error_and_exits_1(monkeypatch, capsys):
    class ExplodingClient:
        def __init__(self, api_key=None):
            raise RuntimeError("kaboom")

    monkeypatch.setattr(tool, "Context7Client", ExplodingClient)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "--library", "fastapi", "--query", "q", "--api-key", "k"])
    with pytest.raises(SystemExit) as exc_info:
        tool.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "Unexpected error:" in err
    assert "kaboom" in err


# ---------------------------------------------------------------------------
# subprocess smoke test (real __main__ entrypoint; --api-key given explicitly
# so nothing touches this repo's or the user's real .mcp.json)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_end_to_end(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "--library", "fastapi", "--query", "routing", "--api-key", "k", "--json"],
        capture_output=True, text=True, timeout=30, cwd=str(tmp_path),
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["library"] == "fastapi"
    assert payload["query"] == "routing"


def test_cli_subprocess_smoke_missing_required_args_exits_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode != 0
