import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("chatbot_endpoint_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["chatbot_endpoint_tool"] = tool
_spec.loader.exec_module(tool)


def test_new_conversation_id_is_unique():
    a = tool.new_conversation_id()
    b = tool.new_conversation_id()
    assert a != b
    assert len(a) == 36


def test_validate_message_payload_accepts_valid():
    tool.validate_message_payload({"message": "hello there"})


def test_validate_message_payload_rejects_empty_message():
    import pytest
    with pytest.raises(ValueError):
        tool.validate_message_payload({"message": "   "})


def test_validate_message_payload_rejects_non_string_conversation_id():
    import pytest
    with pytest.raises(ValueError):
        tool.validate_message_payload({"message": "hi", "conversation_id": 123})


def test_classify_action_intent_detects_delete_all_needs_confirmation():
    result = tool.classify_action_intent("delete all my tasks")
    assert result["action"] == "delete"
    assert result["needs_confirmation"] is True


def test_classify_action_intent_detects_delete_specific_no_confirmation():
    result = tool.classify_action_intent("delete 'buy milk'")
    assert result["action"] == "delete"
    assert result["target_hint"] == "buy milk"
    assert result["needs_confirmation"] is False


def test_classify_action_intent_defaults_to_chat():
    result = tool.classify_action_intent("how is the weather today")
    assert result["action"] == "chat"
    assert result["needs_confirmation"] is False


def test_build_response_envelope_shape():
    env = tool.build_response_envelope("conv-1", "assistant", "hello")
    assert env["conversation_id"] == "conv-1"
    assert env["role"] == "assistant"
    assert env["tool_calls"] == []
    assert "created_at" in env


def test_build_response_envelope_rejects_bad_role():
    import pytest
    with pytest.raises(ValueError):
        tool.build_response_envelope("conv-1", "narrator", "hello")


def test_trim_history_for_context_keeps_last_n():
    messages = [{"i": i} for i in range(15)]
    trimmed = tool.trim_history_for_context(messages, max_messages=5)
    assert len(trimmed) == 5
    assert trimmed[-1]["i"] == 14


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess as _subprocess_module
import sys
from types import SimpleNamespace
import pytest


def test_validate_message_payload_rejects_non_dict_payload():
    with pytest.raises(ValueError):
        tool.validate_message_payload(["not", "a", "dict"])


def test_validate_message_payload_rejects_missing_message_key():
    with pytest.raises(ValueError):
        tool.validate_message_payload({})


def test_validate_message_payload_rejects_non_string_message():
    with pytest.raises(ValueError):
        tool.validate_message_payload({"message": 123})


def test_validate_message_payload_accepts_message_at_exactly_8000_chars():
    tool.validate_message_payload({"message": "x" * 8000})  # must not raise


def test_validate_message_payload_rejects_message_at_8001_chars():
    with pytest.raises(ValueError):
        tool.validate_message_payload({"message": "x" * 8001})


def test_validate_message_payload_accepts_valid_conversation_id():
    tool.validate_message_payload({"message": "hi", "conversation_id": "conv-1"})  # must not raise


def test_classify_action_intent_rejects_non_string_message():
    with pytest.raises(ValueError):
        tool.classify_action_intent(None)


def test_classify_action_intent_detects_complete_action():
    result = tool.classify_action_intent("mark 'buy milk' as done")
    assert result["action"] == "complete"


def test_classify_action_intent_detects_update_action():
    result = tool.classify_action_intent("update 'buy milk' to buy oat milk")
    assert result["action"] == "update"


def test_classify_action_intent_detects_add_action():
    result = tool.classify_action_intent("add a new task to buy milk")
    assert result["action"] == "add"


def test_classify_action_intent_detects_list_action():
    result = tool.classify_action_intent("show me my tasks")
    assert result["action"] == "list"


def test_classify_action_intent_complete_without_target_needs_confirmation():
    result = tool.classify_action_intent("mark it complete")
    assert result["action"] == "complete"
    assert result["target_hint"] is None
    assert result["needs_confirmation"] is True


def test_classify_action_intent_non_destructive_bulk_action_never_needs_confirmation():
    result = tool.classify_action_intent("update all my tasks")
    assert result["action"] == "update"
    assert result["is_bulk"] is True
    assert result["needs_confirmation"] is False


def test_classify_action_intent_detects_everything_bulk_word():
    result = tool.classify_action_intent("delete everything")
    assert result["is_bulk"] is True
    assert result["needs_confirmation"] is True


def test_classify_action_intent_extracts_double_quoted_target():
    result = tool.classify_action_intent('delete "the quarterly report"')
    assert result["target_hint"] == "the quarterly report"


def test_classify_action_intent_bulk_and_quoted_target_still_needs_confirmation():
    result = tool.classify_action_intent("delete all 'my tasks'")
    assert result["target_hint"] == "my tasks"
    assert result["is_bulk"] is True
    assert result["needs_confirmation"] is True


def test_build_response_envelope_preserves_provided_tool_calls():
    calls = [{"name": "delete_task", "args": {"id": 1}}]
    env = tool.build_response_envelope("conv-1", "assistant", "done", tool_calls=calls)
    assert env["tool_calls"] == calls


def test_trim_history_for_context_zero_max_returns_empty():
    assert tool.trim_history_for_context([{"i": 1}], max_messages=0) == []


def test_trim_history_for_context_negative_max_returns_empty():
    assert tool.trim_history_for_context([{"i": 1}], max_messages=-3) == []


def test_trim_history_for_context_max_larger_than_list_returns_all():
    messages = [{"i": i} for i in range(3)]
    trimmed = tool.trim_history_for_context(messages, max_messages=50)
    assert trimmed == messages


def test_cmd_new_conversation_id_prints_uuid(capsys):
    rc = tool.cmd_new_conversation_id(SimpleNamespace())
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert len(out) == 36


def test_cmd_validate_payload_valid_prints_success(capsys):
    args = SimpleNamespace(payload=json.dumps({"message": "hello"}))
    rc = tool.cmd_validate_payload(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "payload is valid" in out


def test_cmd_validate_payload_invalid_json_prints_error_and_returns_one(capsys):
    args = SimpleNamespace(payload="not json")
    rc = tool.cmd_validate_payload(args)
    out = capsys.readouterr().out
    assert rc == 1


def test_cmd_validate_payload_invalid_payload_prints_error_and_returns_one(capsys):
    args = SimpleNamespace(payload=json.dumps({"message": "   "}))
    rc = tool.cmd_validate_payload(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "required" in out


def test_cmd_classify_intent_prints_json(capsys):
    args = SimpleNamespace(message="delete all tasks")
    rc = tool.cmd_classify_intent(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["action"] == "delete"


def test_cmd_test_invokes_pytest_subprocess_with_expected_command(monkeypatch):
    calls = {}

    class FakeResult:
        returncode = 0

    def fake_run(cmd, *a, **kw):
        calls["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(_subprocess_module, "run", fake_run)
    rc = tool.cmd_test(SimpleNamespace())
    assert rc == 0
    assert "-m" in calls["cmd"]
    assert "pytest" in calls["cmd"]
    assert "--import-mode=importlib" in calls["cmd"]
    assert "-q" in calls["cmd"]


def test_cmd_test_propagates_nonzero_return_code(monkeypatch):
    class FakeResult:
        returncode = 7

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: FakeResult())
    rc = tool.cmd_test(SimpleNamespace())
    assert rc == 7


def test_main_dispatches_new_conversation_id_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "new-conversation-id"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 36


def test_main_dispatches_validate_payload_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-payload", "--payload", json.dumps({"message": "hi"})])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "payload is valid" in out


def test_main_dispatches_classify_intent_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "classify-intent", "--message", "show my tasks"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["action"] == "list"


def test_main_dispatches_test_subcommand_end_to_end(monkeypatch, capsys):
    class FakeResult:
        returncode = 0

    monkeypatch.setattr(_subprocess_module, "run", lambda *a, **kw: FakeResult())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0


def test_main_with_no_command_exits_nonzero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code != 0


def test_main_validate_payload_missing_required_payload_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "validate-payload"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_classify_intent_missing_required_message_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "classify-intent"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_smoke_runs_as_script_and_exercises_main_guard():
    from pathlib import Path as _Path
    script = _Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = _subprocess_module.run([sys.executable, str(script), "new-conversation-id"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert len(proc.stdout.strip()) == 36
