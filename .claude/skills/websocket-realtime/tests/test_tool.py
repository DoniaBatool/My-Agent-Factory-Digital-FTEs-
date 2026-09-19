import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("websocket_realtime_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["websocket_realtime_tool"] = tool
_spec.loader.exec_module(tool)

import pytest
import json


def test_build_room_key_basic():
    assert tool.build_room_key("chat", "room1") == "chat:room1"


def test_build_room_key_rejects_empty():
    with pytest.raises(ValueError):
        tool.build_room_key("", "room1")


def test_broadcast_targets_filters_by_room_and_excludes_sender():
    connections = {
        "c1": {"room_id": "r1"},
        "c2": {"room_id": "r1"},
        "c3": {"room_id": "r2"},
    }
    targets = tool.broadcast_targets(connections, "r1", exclude_conn_id="c1")
    assert targets == ["c2"]


def test_validate_ws_message_detects_missing_fields():
    errors = tool.validate_ws_message({"type": "chat"})
    assert any("data" in e for e in errors)


def test_validate_ws_message_rejects_unknown_type():
    errors = tool.validate_ws_message({"type": "hack", "data": {}})
    assert any("unknown message type" in e for e in errors)


def test_validate_ws_message_accepts_valid():
    assert tool.validate_ws_message({"type": "chat", "data": {"text": "hi"}}) == []


def test_heartbeat_expired_true_after_timeout():
    assert tool.heartbeat_expired(last_ping_ts=0.0, now_ts=40.0, timeout=30.0) is True


def test_heartbeat_expired_false_within_timeout():
    assert tool.heartbeat_expired(last_ping_ts=0.0, now_ts=10.0, timeout=30.0) is False


def test_rate_limit_check_allows_up_to_max():
    state = {}
    results = [tool.rate_limit_check(state, "c1", now=1.0, max_msgs=5, window=1.0) for _ in range(5)]
    assert all(results)


def test_rate_limit_check_blocks_beyond_max():
    state = {}
    for _ in range(5):
        tool.rate_limit_check(state, "c1", now=1.0, max_msgs=5, window=1.0)
    assert tool.rate_limit_check(state, "c1", now=1.2, max_msgs=5, window=1.0) is False


def test_rate_limit_check_resets_after_window():
    state = {}
    for _ in range(5):
        tool.rate_limit_check(state, "c1", now=1.0, max_msgs=5, window=1.0)
    assert tool.rate_limit_check(state, "c1", now=3.0, max_msgs=5, window=1.0) is True


def test_serialize_event_produces_valid_json():
    line = tool.serialize_event("chat", {"text": "hi"})
    parsed = json.loads(line)
    assert parsed["type"] == "chat"
    assert parsed["data"]["text"] == "hi"


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess as _subprocess_module
from pathlib import Path


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_build_room_key_rejects_empty_room_id():
    with pytest.raises(ValueError):
        tool.build_room_key("chat", "")


def test_broadcast_targets_no_exclude_includes_everyone_in_room():
    connections = {"c1": {"room_id": "r1"}, "c2": {"room_id": "r1"}}
    targets = tool.broadcast_targets(connections, "r1")
    assert sorted(targets) == ["c1", "c2"]


def test_broadcast_targets_empty_connections_returns_empty_list():
    assert tool.broadcast_targets({}, "r1") == []


def test_broadcast_targets_no_match_in_room_returns_empty_list():
    connections = {"c1": {"room_id": "other"}}
    assert tool.broadcast_targets(connections, "r1") == []


def test_validate_ws_message_rejects_non_dict_payload():
    assert tool.validate_ws_message(["not", "a", "dict"]) == ["payload must be a JSON object"]


def test_validate_ws_message_reports_both_missing_fields():
    errors = tool.validate_ws_message({})
    assert any("type" in e for e in errors)
    assert any("data" in e for e in errors)
    assert len(errors) == 2


def test_validate_ws_message_explicit_none_type_is_not_flagged_as_unknown():
    # type present but None: `msg_type is not None` guards the unknown-type
    # check, so this is a missing-field error, never an "unknown type" one.
    errors = tool.validate_ws_message({"type": None, "data": {}})
    assert errors == []  # "type" key exists (even if None), "data" exists


def test_validate_ws_message_absent_type_key_reports_missing_not_unknown():
    errors = tool.validate_ws_message({"data": {}})
    assert errors == ["missing required field: type"]


def test_heartbeat_expired_exact_boundary_is_not_expired():
    # strictly greater-than: exactly at the timeout should NOT count as expired
    assert tool.heartbeat_expired(last_ping_ts=0.0, now_ts=30.0, timeout=30.0) is False


def test_heartbeat_expired_one_unit_past_boundary_is_expired():
    assert tool.heartbeat_expired(last_ping_ts=0.0, now_ts=30.0001, timeout=30.0) is True


def test_rate_limit_check_entry_exactly_at_window_cutoff_is_dropped():
    state = {"c1": [0.0]}
    # now=1.0, window=1.0 -> cutoff=0.0; the existing entry at t=0.0 is NOT > cutoff
    # so it must be evicted, freeing capacity even though max_msgs=1
    allowed = tool.rate_limit_check(state, "c1", now=1.0, max_msgs=1, window=1.0)
    assert allowed is True
    assert state["c1"] == [1.0]


def test_rate_limit_check_different_connections_have_independent_buckets():
    state = {}
    for _ in range(5):
        tool.rate_limit_check(state, "c1", now=1.0, max_msgs=5, window=1.0)
    assert tool.rate_limit_check(state, "c2", now=1.0, max_msgs=5, window=1.0) is True


def test_serialize_event_with_none_data():
    line = tool.serialize_event("ping", None)
    parsed = json.loads(line)
    assert parsed == {"type": "ping", "data": None}


def test_print_success_outputs_checkmark_and_message(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_outputs_cross_and_message(capsys):
    tool.print_error("broken")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "broken" in out


def test_cmd_test_invokes_pytest_with_expected_args_and_returns_its_code(monkeypatch):
    captured = {}

    class _FakeCompletedProcess:
        returncode = 7

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return _FakeCompletedProcess()

    monkeypatch.setattr(_subprocess_module, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 7
    cmd = captured["cmd"]
    assert cmd[0] == sys.executable
    assert "-m" in cmd and "pytest" in cmd
    assert cmd[-1] == "-q"
    expected_tests_dir = str(Path(tool.__file__).resolve().parent.parent / "tests")
    assert expected_tests_dir in cmd


def test_main_test_command_dispatches_via_func_and_exits_with_code(monkeypatch):
    class _FakeCompletedProcess:
        returncode = 5

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: _FakeCompletedProcess())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 5


def test_main_missing_command_is_required_and_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_no_args_hits_main_guard_and_exits_nonzero():
    script = Path(tool.__file__).resolve()
    result = _subprocess_module.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "command" in result.stderr.lower() or "required" in result.stderr.lower()
