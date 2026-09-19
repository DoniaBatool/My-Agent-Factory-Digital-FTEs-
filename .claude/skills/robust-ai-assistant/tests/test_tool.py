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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess as _subprocess


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- retry_with_backoff edge cases -------------------------------------------

def test_retry_with_backoff_sleeps_with_exponential_delays():
    sleeps = []
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        tool.retry_with_backoff(always_fails, max_retries=3, base_delay=1.0, sleep_fn=lambda s: sleeps.append(s))
    assert sleeps == [1.0, 2.0]  # base*2**0, base*2**1 -- no sleep after the final attempt


def test_retry_with_backoff_single_attempt_never_sleeps():
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    slept = []
    with pytest.raises(ValueError):
        tool.retry_with_backoff(always_fails, max_retries=1, base_delay=5.0, sleep_fn=lambda s: slept.append(s))
    assert calls["n"] == 1
    assert slept == []


def test_retry_with_backoff_does_not_catch_unlisted_exception_types():
    def raises_type_error():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        tool.retry_with_backoff(
            raises_type_error, max_retries=3, base_delay=0.0,
            exceptions=(ValueError,), sleep_fn=lambda s: None,
        )


# --- fallback_chain edge cases -----------------------------------------------

def test_fallback_chain_primary_success_never_calls_fallbacks():
    fallback_called = {"called": False}

    def primary():
        return "primary result"

    def fallback():
        fallback_called["called"] = True
        return "should not be used"

    result = tool.fallback_chain(primary, [fallback])
    assert result == "primary result"
    assert fallback_called["called"] is False


def test_fallback_chain_with_no_fallbacks_raises_primary_error():
    def primary():
        raise RuntimeError("only failure")

    with pytest.raises(RuntimeError, match="only failure"):
        tool.fallback_chain(primary, [])


# --- validate_ai_response_schema edge cases ----------------------------------

def test_validate_ai_response_schema_rejects_non_dict_response():
    errors = tool.validate_ai_response_schema("not a dict", ["answer"])
    assert errors == ["response must be a JSON object"]


def test_validate_ai_response_schema_empty_required_keys_always_passes():
    assert tool.validate_ai_response_schema({}, []) == []


# --- sanitize_user_input edge cases ------------------------------------------

def test_sanitize_user_input_rejects_non_string():
    with pytest.raises(ValueError):
        tool.sanitize_user_input(12345)


def test_sanitize_user_input_no_truncation_at_exact_max_len():
    text = "a" * 100
    result = tool.sanitize_user_input(text, max_len=100)
    assert result == text
    assert len(result) == 100


def test_sanitize_user_input_strips_leading_and_trailing_whitespace():
    assert tool.sanitize_user_input("   hello world   ") == "hello world"


# --- should_allow_request edge cases -----------------------------------------

def test_should_allow_request_true_when_not_tripped():
    assert tool.should_allow_request({}, now=0.0) is True
    assert tool.should_allow_request({"tripped": False}, now=0.0) is True


def test_should_allow_request_exact_cooldown_boundary_allows():
    state = {"tripped": True, "tripped_at": 100.0}
    assert tool.should_allow_request(state, now=130.0, cooldown_seconds=30.0) is True
    assert state["tripped"] is False


def test_should_allow_request_one_second_before_cooldown_blocks():
    state = {"tripped": True, "tripped_at": 100.0}
    assert tool.should_allow_request(state, now=129.0, cooldown_seconds=30.0) is False
    assert state["tripped"] is True


# --- previously-uncalled print helpers ---------------------------------------

def test_print_success_and_print_error_format_output(capsys):
    tool.print_success("all good")
    tool.print_error("went wrong")
    out = capsys.readouterr().out
    assert "all good" in out
    assert "went wrong" in out


# --- CLI layer: cmd_test / main ----------------------------------------------

def test_cmd_test_invokes_pytest_with_expected_args(monkeypatch):
    captured = {}

    class FakeResult:
        returncode = 0

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(_subprocess, "run", fake_run)
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "pytest" in captured["cmd"]
    assert "--import-mode=importlib" in captured["cmd"]
    assert "-q" in captured["cmd"]


def test_cmd_test_propagates_nonzero_pytest_exit_code(monkeypatch):
    class FakeResult:
        returncode = 1

    monkeypatch.setattr(_subprocess, "run", lambda cmd, *a, **kw: FakeResult())
    rc = tool.cmd_test(_Args())
    assert rc == 1


def test_main_no_command_exits_nonzero_because_subcommand_required(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code != 0


def test_main_dispatches_test_command_success(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    monkeypatch.setattr(tool, "cmd_test", lambda args: 0)
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 0


def test_main_dispatches_test_command_failure(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    monkeypatch.setattr(tool, "cmd_test", lambda args: 1)
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1


def test_main_rejects_unknown_subcommand(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "bogus-command"])
    with pytest.raises(SystemExit):
        tool.main()


def test_script_runs_as_main_via_subprocess_missing_command_exits_nonzero():
    # Exercises the `if __name__ == "__main__":` guard for real without
    # triggering the "test" subcommand's own (recursive) pytest invocation:
    # omitting the required subcommand fails fast inside argparse.
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()
