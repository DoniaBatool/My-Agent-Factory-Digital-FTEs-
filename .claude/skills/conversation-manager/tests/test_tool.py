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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import sys as _sys


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_print_success_writes_checkmark_and_message(capsys):
    tool.print_success("saved conversation")
    out = capsys.readouterr().out
    assert "saved conversation" in out
    assert "✓" in out


def test_print_error_writes_cross_and_message(capsys):
    tool.print_error("delete failed")
    out = capsys.readouterr().out
    assert "delete failed" in out
    assert "✗" in out


def test_latest_message_preview_exact_boundary_length_not_truncated():
    messages = [{"content": "x" * 80}]
    preview = tool.latest_message_preview(messages, max_len=80)
    assert preview == "x" * 80
    assert not preview.endswith("…")


def test_latest_message_preview_collapses_internal_whitespace():
    messages = [{"content": "hello   \n\n  world"}]
    assert tool.latest_message_preview(messages) == "hello world"


def test_build_conversation_list_falls_back_to_conv_created_at_when_no_messages():
    conversations = [{"id": "c1", "created_at": "2026-03-01T00:00:00"}]
    result = tool.build_conversation_list(conversations, {})
    assert result[0]["last_activity_at"] == "2026-03-01T00:00:00"
    assert result[0]["message_count"] == 0
    assert result[0]["preview"] == ""


def test_paginate_messages_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        tool.paginate_messages([{"id": "1"}], limit=0)


def test_paginate_messages_returns_full_list_when_limit_exceeds_length():
    messages = [{"id": str(i)} for i in range(3)]
    page = tool.paginate_messages(messages, limit=10)
    assert len(page["messages"]) == 3
    assert page["has_more"] is False


def test_paginate_messages_before_earliest_id_returns_empty_page_no_more():
    messages = [{"id": str(i)} for i in range(5)]
    page = tool.paginate_messages(messages, limit=2, before_id="0")
    assert page["messages"] == []
    assert page["has_more"] is False


def test_cascade_delete_plan_no_matches_returns_empty():
    messages = [{"id": "m1", "conversation_id": "other"}]
    plan = tool.cascade_delete_plan("c1", messages)
    assert plan["delete_message_ids"] == []
    assert plan["count"] == 0


def test_scoped_conversations_for_user_excludes_missing_user_id_key():
    conversations = [{"id": "c1"}, {"id": "c2", "user_id": "u1"}]
    result = tool.scoped_conversations_for_user(conversations, "u1")
    assert [c["id"] for c in result] == ["c2"]


def test_cmd_test_forwards_pytest_returncode_and_invokes_subprocess(monkeypatch):
    calls = {}

    class _FakeCompleted:
        def __init__(self, returncode):
            self.returncode = returncode

    def _fake_run(cmd, *a, **kw):
        calls["cmd"] = cmd
        return _FakeCompleted(0)

    import subprocess as _subprocess_mod
    monkeypatch.setattr(_subprocess_mod, "run", _fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert calls["cmd"][0] == _sys.executable
    assert "-m" in calls["cmd"] and "pytest" in calls["cmd"]
    assert "--import-mode=importlib" in calls["cmd"]


def test_cmd_test_forwards_nonzero_returncode_on_failure(monkeypatch):
    class _FakeCompleted:
        def __init__(self, returncode):
            self.returncode = returncode

    import subprocess as _subprocess_mod
    monkeypatch.setattr(_subprocess_mod, "run", lambda cmd, *a, **kw: _FakeCompleted(1))
    rc = tool.cmd_test(_Args())
    assert rc == 1


def test_main_requires_command_argument_and_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_test_command_and_propagates_returncode(monkeypatch):
    monkeypatch.setattr(tool, "cmd_test", lambda args: 42)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as exc_info:
        tool.main()
    assert exc_info.value.code == 42


def test_main_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "bogus-command"])
    with pytest.raises(SystemExit):
        tool.main()
