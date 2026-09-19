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
