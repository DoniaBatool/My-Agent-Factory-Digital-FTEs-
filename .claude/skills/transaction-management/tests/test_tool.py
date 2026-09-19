import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
_spec = importlib.util.spec_from_file_location("transaction_management_tool", _MODULE_PATH)
tool = importlib.util.module_from_spec(_spec)
sys.modules["transaction_management_tool"] = tool
_spec.loader.exec_module(tool)

import pytest


def test_validate_isolation_level_accepts_known_levels():
    assert tool.validate_isolation_level("SERIALIZABLE") is True
    assert tool.validate_isolation_level("read committed") is True


def test_validate_isolation_level_rejects_unknown():
    assert tool.validate_isolation_level("BOGUS LEVEL") is False


def test_transaction_commit_keeps_applied_state():
    balance = {"value": 100}
    tx = tool.Transaction()
    tx.execute(lambda: balance.__setitem__("value", 50), lambda: balance.__setitem__("value", 100), "withdraw 50")
    tx.commit()
    assert balance["value"] == 50
    assert tx.committed is True


def test_transaction_rollback_undoes_applied_ops_in_reverse_order():
    log = []
    tx = tool.Transaction()
    tx.execute(lambda: log.append("A"), lambda: log.append("undo-A"))
    tx.execute(lambda: log.append("B"), lambda: log.append("undo-B"))
    tx.rollback()
    assert log == ["A", "B", "undo-B", "undo-A"]
    assert tx.rolled_back is True


def test_transaction_cannot_execute_after_commit():
    tx = tool.Transaction()
    tx.commit()
    with pytest.raises(RuntimeError):
        tx.execute(lambda: None, lambda: None)


def test_transaction_cannot_rollback_after_commit():
    tx = tool.Transaction()
    tx.commit()
    with pytest.raises(RuntimeError):
        tx.rollback()


def test_detect_deadlock_risk_finds_simple_cycle():
    # tx1 waits for tx2, tx2 waits for tx1 -> deadlock
    assert tool.detect_deadlock_risk([("tx1", "tx2"), ("tx2", "tx1")]) is True


def test_detect_deadlock_risk_no_cycle_in_linear_chain():
    assert tool.detect_deadlock_risk([("tx1", "tx2"), ("tx2", "tx3")]) is False


def test_detect_deadlock_risk_finds_longer_cycle():
    assert tool.detect_deadlock_risk([("tx1", "tx2"), ("tx2", "tx3"), ("tx3", "tx1")]) is True


def test_retry_on_serialization_failure_eventually_succeeds():
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("serialization failure")
        return "committed"
    result = tool.retry_on_serialization_failure(flaky, max_retries=5)
    assert result == "committed"


# --- edge cases + CLI layer (added for bulletproofing pass) ---

import subprocess as _subprocess_module
from pathlib import Path


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_validate_isolation_level_accepts_mixed_case():
    assert tool.validate_isolation_level("Repeatable Read") is True


def test_transaction_cannot_execute_after_rollback():
    tx = tool.Transaction()
    tx.rollback()
    with pytest.raises(RuntimeError):
        tx.execute(lambda: None, lambda: None)


def test_transaction_cannot_commit_after_rollback():
    tx = tool.Transaction()
    tx.rollback()
    with pytest.raises(RuntimeError):
        tx.commit()


def test_transaction_rollback_with_no_ops_still_marks_rolled_back():
    tx = tool.Transaction()
    tx.rollback()
    assert tx.rolled_back is True
    assert tx.committed is False


def test_detect_deadlock_risk_empty_list_is_false():
    assert tool.detect_deadlock_risk([]) is False


def test_detect_deadlock_risk_self_loop_is_cycle():
    assert tool.detect_deadlock_risk([("tx1", "tx1")]) is True


def test_retry_on_serialization_failure_raises_last_exception_after_exhausting_retries():
    def always_fails():
        raise ValueError("still conflicting")
    with pytest.raises(ValueError, match="still conflicting"):
        tool.retry_on_serialization_failure(always_fails, max_retries=3)


def test_retry_on_serialization_failure_does_not_catch_unlisted_exception_types():
    def raises_key_error():
        raise KeyError("boom")
    with pytest.raises(KeyError):
        tool.retry_on_serialization_failure(raises_key_error, max_retries=3, exceptions=(ValueError,))


def test_retry_on_serialization_failure_calls_sleep_fn_between_attempts():
    sleeps = []
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("retry me")
        return "ok"

    result = tool.retry_on_serialization_failure(flaky, max_retries=5, sleep_fn=lambda s: sleeps.append(s))
    assert result == "ok"
    assert sleeps == [0, 0]  # called once per failed attempt, not on the final success


def test_retry_on_serialization_failure_zero_max_retries_raises_type_error():
    # boundary: max_retries=0 means the loop body never runs, so last_exc
    # stays None and `raise None` surfaces as a TypeError -- documents real
    # (if surprising) behavior at this exact boundary.
    with pytest.raises(TypeError):
        tool.retry_on_serialization_failure(lambda: 1 / 0, max_retries=0)


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
