import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("microservices_patterns_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_circuit_breaker_starts_closed():
    breaker = tool.CircuitBreaker()
    assert breaker.state == "CLOSED"


def test_circuit_breaker_opens_after_threshold_failures():
    breaker = tool.CircuitBreaker(failure_threshold=3, clock=lambda: 0)
    for _ in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        except RuntimeError:
            pass
    assert breaker.state == "OPEN"


def test_circuit_breaker_rejects_calls_while_open_without_invoking_func():
    breaker = tool.CircuitBreaker(failure_threshold=1, recovery_timeout=1000, clock=lambda: 0)
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    calls = []
    try:
        breaker.call(lambda: calls.append(1))
    except tool.CircuitOpenError:
        pass
    assert calls == []  # func was never actually invoked


def test_circuit_breaker_recovers_to_half_open_after_timeout():
    now = [0]
    breaker = tool.CircuitBreaker(failure_threshold=1, recovery_timeout=10, clock=lambda: now[0])
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    assert breaker.state == "OPEN"
    now[0] = 11
    result = breaker.call(lambda: "recovered")
    assert result == "recovered"
    assert breaker.state == "CLOSED"


def test_run_saga_all_steps_succeed():
    steps = [("a", lambda: None, lambda: None), ("b", lambda: None, lambda: None)]
    result = tool.run_saga(steps)
    assert result == {"status": "completed", "completed_steps": ["a", "b"], "error": None}


def test_run_saga_compensates_completed_steps_on_failure():
    log = []
    steps = [
        ("reserve", lambda: log.append("reserve"), lambda: log.append("comp:reserve")),
        ("charge", lambda: (_ for _ in ()).throw(RuntimeError("card declined")), lambda: log.append("comp:charge")),
    ]
    result = tool.run_saga(steps)
    assert result["status"] == "failed"
    assert result["completed_steps"] == ["reserve"]
    assert "comp:reserve" in log
    assert "comp:charge" not in log  # charge never completed, nothing to compensate
