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


# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import subprocess
import sys as _sys
import pytest


def test_circuit_breaker_half_open_failure_returns_to_open():
    now = [0]
    breaker = tool.CircuitBreaker(failure_threshold=1, recovery_timeout=10, clock=lambda: now[0])
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    assert breaker.state == "OPEN"
    now[0] = 11  # exactly at the recovery_timeout boundary -- >= is required, not >
    breaker._maybe_recover()
    assert breaker.state == "HALF_OPEN"
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("still broken")))
    except RuntimeError:
        pass
    assert breaker.state == "OPEN"  # a HALF_OPEN failure re-opens even below failure_threshold count


def test_circuit_breaker_does_not_recover_before_timeout_elapses():
    now = [0]
    breaker = tool.CircuitBreaker(failure_threshold=1, recovery_timeout=10, clock=lambda: now[0])
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    now[0] = 9  # one unit short of the boundary
    breaker._maybe_recover()
    assert breaker.state == "OPEN"


def test_circuit_breaker_below_threshold_stays_closed():
    breaker = tool.CircuitBreaker(failure_threshold=3, clock=lambda: 0)
    for _ in range(2):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        except RuntimeError:
            pass
    assert breaker.state == "CLOSED"


def test_circuit_breaker_success_resets_failure_count():
    breaker = tool.CircuitBreaker(failure_threshold=2, clock=lambda: 0)
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    breaker.call(lambda: "ok")
    assert breaker.state == "CLOSED"
    assert breaker._failure_count == 0
    # now it should take another 2 failures (not 1) to open, proving the count really reset
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    assert breaker.state == "CLOSED"


def test_run_saga_empty_steps_completes_with_no_steps():
    result = tool.run_saga([])
    assert result == {"status": "completed", "completed_steps": [], "error": None}


def test_run_saga_first_step_fails_nothing_to_compensate():
    log = []
    steps = [("only", lambda: (_ for _ in ()).throw(RuntimeError("boom")), lambda: log.append("comp"))]
    result = tool.run_saga(steps)
    assert result["status"] == "failed"
    assert result["completed_steps"] == []
    assert log == []


def test_run_saga_compensation_runs_in_reverse_order():
    log = []
    steps = [
        ("a", lambda: log.append("a"), lambda: log.append("comp:a")),
        ("b", lambda: log.append("b"), lambda: log.append("comp:b")),
        ("c", lambda: (_ for _ in ()).throw(RuntimeError("c failed")), lambda: log.append("comp:c")),
    ]
    result = tool.run_saga(steps)
    assert result["completed_steps"] == ["a", "b"]
    # compensation must be reverse order: b before a
    assert log.index("comp:b") < log.index("comp:a")


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_cmd_demo_circuit_breaker_prints_transitions(capsys):
    args = _Args(threshold=2, recovery_timeout=60)
    rc = tool.cmd_demo_circuit_breaker(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "state=OPEN" in out
    assert "failed" in out


def test_cmd_run_saga_success_path_returns_0(capsys):
    args = _Args(steps="a,b", fail_at=None)
    rc = tool.cmd_run_saga(args)
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["status"] == "completed"
    assert payload["completed_steps"] == ["a", "b"]


def test_cmd_run_saga_failure_path_returns_1_and_compensates(capsys):
    args = _Args(steps="reserve,charge,ship", fail_at="charge")
    rc = tool.cmd_run_saga(args)
    out = capsys.readouterr().out
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "failed"
    assert payload["completed_steps"] == ["reserve"]
    assert "reserve: compensate" in payload["log"]


def test_cmd_test_self_test_passes(capsys):
    args = _Args()
    rc = tool.cmd_test(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_demo_circuit_breaker_end_to_end_with_defaults(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "demo-circuit-breaker"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "call 1" in out


def test_main_run_saga_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "run-saga", "--steps", "x,y", "--fail-at", "y"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert '"status": "failed"' in out


def test_main_test_subcommand_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_run_saga_missing_required_steps_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "run-saga"])
    with pytest.raises(SystemExit):
        tool.main()


def test_cli_subprocess_smoke_test_runs_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "run-saga", "--steps", "a,b"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert '"status": "completed"' in proc.stdout


def test_cli_subprocess_smoke_test_saga_failure_exits_nonzero():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "run-saga", "--steps", "a,b", "--fail-at", "a"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 1


def test_cmd_demo_circuit_breaker_threshold_zero_succeeds_immediately(capsys):
    # With threshold=0 the loop runs exactly once and flaky() never raises
    # (calls=1 > threshold=0), so this is the only way to reach the
    # "success" print branch and flaky's `return "ok"` line -- with any
    # threshold >= 1 the breaker opens after exactly `threshold` failures
    # and rejects every subsequent call before flaky() can ever succeed.
    args = _Args(threshold=0, recovery_timeout=60)
    rc = tool.cmd_demo_circuit_breaker(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "call 1: success (ok), state=CLOSED" in out
