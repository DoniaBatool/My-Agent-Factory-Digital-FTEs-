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
