import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("robust_ai_assistant_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["robust_ai_assistant_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_retry_with_backoff_succeeds_eventually():
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("not yet")
        return "ok"
    result = tool.retry_with_backoff(flaky, max_retries=5, base_delay=0.0, sleep_fn=lambda s: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_with_backoff_raises_after_exhausting_attempts():
    def always_fails():
        raise ValueError("nope")
    with pytest.raises(ValueError):
        tool.retry_with_backoff(always_fails, max_retries=3, base_delay=0.0, sleep_fn=lambda s: None)


def test_fallback_chain_uses_first_success():
    def primary():
        raise RuntimeError("primary down")
    def fallback1():
        raise RuntimeError("fallback1 down")
    def fallback2():
        return "fallback2 result"
    result = tool.fallback_chain(primary, [fallback1, fallback2])
    assert result == "fallback2 result"


def test_fallback_chain_raises_primary_error_when_all_fail():
    def primary():
        raise RuntimeError("primary error")
    def fallback1():
        raise RuntimeError("fallback error")
    with pytest.raises(RuntimeError, match="primary error"):
        tool.fallback_chain(primary, [fallback1])


def test_validate_ai_response_schema_detects_missing_keys():
    errors = tool.validate_ai_response_schema({"answer": "hi"}, ["answer", "confidence"])
    assert any("confidence" in e for e in errors)


def test_validate_ai_response_schema_passes_when_complete():
    errors = tool.validate_ai_response_schema({"answer": "hi", "confidence": 0.9}, ["answer", "confidence"])
    assert errors == []


def test_sanitize_user_input_strips_control_chars():
    dirty = "hello\x00world\x1f!"
    assert tool.sanitize_user_input(dirty) == "helloworld!"


def test_sanitize_user_input_truncates_long_text():
    long_text = "a" * 5000
    result = tool.sanitize_user_input(long_text, max_len=100)
    assert len(result) == 100


def test_should_allow_request_blocks_during_cooldown():
    state = {"tripped": True, "tripped_at": 100.0}
    assert tool.should_allow_request(state, now=110.0, cooldown_seconds=30.0) is False


def test_should_allow_request_allows_after_cooldown():
    state = {"tripped": True, "tripped_at": 100.0}
    assert tool.should_allow_request(state, now=140.0, cooldown_seconds=30.0) is True
    assert state["tripped"] is False
