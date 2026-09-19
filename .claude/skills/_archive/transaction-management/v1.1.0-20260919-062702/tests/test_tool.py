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
