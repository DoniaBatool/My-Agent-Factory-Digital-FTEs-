import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("conversation_manager_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["conversation_manager_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_assert_owns_conversation_passes_for_owner():
    tool.assert_owns_conversation("u1", "u1")


def test_assert_owns_conversation_rejects_other_user():
    with pytest.raises(PermissionError):
        tool.assert_owns_conversation("u1", "u2")


def test_latest_message_preview_truncates_long_content():
    messages = [{"content": "x" * 200}]
    preview = tool.latest_message_preview(messages, max_len=80)
    assert len(preview) == 80
    assert preview.endswith("…")


def test_latest_message_preview_empty_when_no_messages():
    assert tool.latest_message_preview([]) == ""


def test_build_conversation_list_sorts_by_last_activity_desc():
    conversations = [
        {"id": "c1", "created_at": "2026-01-01"},
        {"id": "c2", "created_at": "2026-01-02"},
    ]
    messages_by_conv = {
        "c1": [{"content": "old", "created_at": "2026-01-01T00:00:00"}],
        "c2": [{"content": "new", "created_at": "2026-02-01T00:00:00"}],
    }
    result = tool.build_conversation_list(conversations, messages_by_conv)
    assert result[0]["id"] == "c2"
    assert result[0]["preview"] == "new"


def test_paginate_messages_returns_last_n_when_no_cursor():
    messages = [{"id": str(i)} for i in range(30)]
    page = tool.paginate_messages(messages, limit=10)
    assert len(page["messages"]) == 10
    assert page["messages"][-1]["id"] == "29"
    assert page["has_more"] is True


def test_paginate_messages_before_id_walks_backward():
    messages = [{"id": str(i)} for i in range(30)]
    page = tool.paginate_messages(messages, limit=5, before_id="20")
    assert [m["id"] for m in page["messages"]] == ["15", "16", "17", "18", "19"]


def test_paginate_messages_unknown_cursor_raises():
    messages = [{"id": "1"}]
    with pytest.raises(ValueError):
        tool.paginate_messages(messages, before_id="nope")


def test_cascade_delete_plan_only_targets_matching_conversation():
    messages = [
        {"id": "m1", "conversation_id": "c1"},
        {"id": "m2", "conversation_id": "c2"},
        {"id": "m3", "conversation_id": "c1"},
    ]
    plan = tool.cascade_delete_plan("c1", messages)
    assert set(plan["delete_message_ids"]) == {"m1", "m3"}
    assert plan["count"] == 2


def test_scoped_conversations_for_user_filters_correctly():
    conversations = [{"id": "c1", "user_id": "u1"}, {"id": "c2", "user_id": "u2"}]
    result = tool.scoped_conversations_for_user(conversations, "u1")
    assert [c["id"] for c in result] == ["c1"]
