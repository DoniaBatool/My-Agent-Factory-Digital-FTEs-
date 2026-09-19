#!/usr/bin/env python3
"""
Microservices Patterns Tool - real Circuit Breaker + Saga executor

Commands: demo-circuit-breaker, run-saga, test

These are genuine, runnable implementations of the two patterns this
skill documents (not code samples in markdown) -- a real state machine
and a real compensating-transaction executor.
"""
import argparse
import sys
import time


class CircuitBreaker:
    """CLOSED -> OPEN after `failure_threshold` consecutive failures.
    OPEN -> HALF_OPEN after `recovery_timeout` seconds.
    HALF_OPEN -> CLOSED on a success, or back to OPEN on a failure."""

    def __init__(self, failure_threshold=5, recovery_timeout=60, clock=time.time):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock
        self.state = "CLOSED"
        self._failure_count = 0
        self._opened_at = None

    def _maybe_recover(self):
        if self.state == "OPEN" and self._clock() - self._opened_at >= self.recovery_timeout:
            self.state = "HALF_OPEN"

    def call(self, func, *args, **kwargs):
        self._maybe_recover()
        if self.state == "OPEN":
            raise CircuitOpenError("circuit is open -- call rejected without invoking func")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self):
        self._failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self._failure_count += 1
        if self.state == "HALF_OPEN" or self._failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self._opened_at = self._clock()


class CircuitOpenError(Exception):
    pass


def run_saga(steps):
    """steps: list of (name, action, compensate) callables. Runs actions in
    order; on any failure, runs compensate() for every already-succeeded
    step in REVERSE order (choreography-style rollback). Returns
    {"status": "completed"|"failed", "completed_steps": [...], "error": str|None}."""
    completed = []
    for name, action, _compensate in steps:
        try:
            action()
            completed.append(name)
        except Exception as e:
            for comp_name, _action, compensate in reversed([s for s in steps if s[0] in completed]):
                compensate()
            return {"status": "failed", "completed_steps": completed, "error": str(e)}
    return {"status": "completed", "completed_steps": completed, "error": None}


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_demo_circuit_breaker(args):
    breaker = CircuitBreaker(failure_threshold=args.threshold, recovery_timeout=args.recovery_timeout)
    calls = 0

    def flaky():
        nonlocal calls
        calls += 1
        if calls <= args.threshold:
            raise RuntimeError("simulated failure")
        return "ok"

    for i in range(args.threshold + 1):
        try:
            result = breaker.call(flaky)
            print(f"call {i + 1}: success ({result}), state={breaker.state}")
        except CircuitOpenError:
            print(f"call {i + 1}: rejected (circuit open), state={breaker.state}")
        except RuntimeError:
            print(f"call {i + 1}: failed, state={breaker.state}")
    return 0


def cmd_run_saga(args):
    import json
    log = []

    def make_step(name, should_fail):
        def action():
            log.append(f"{name}: action")
            if should_fail:
                raise RuntimeError(f"{name} failed")
        def compensate():
            log.append(f"{name}: compensate")
        return (name, action, compensate)

    fail_at = args.fail_at
    steps = [make_step(n, n == fail_at) for n in args.steps.split(",")]
    result = run_saga(steps)
    print(json.dumps({**result, "log": log}, indent=2))
    return 0 if result["status"] == "completed" else 1


def cmd_test(args):
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=100, clock=lambda: 0)
    for _ in range(2):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
        except RuntimeError:
            pass
    ok = breaker.state == "OPEN"
    try:
        breaker.call(lambda: "should not run")
        ok = False
    except CircuitOpenError:
        pass

    log = []
    def ok_action(): log.append("a")
    def failing_action(): raise RuntimeError("boom")
    def comp(name):
        def c(): log.append(f"comp:{name}")
        return c
    steps = [("reserve", ok_action, comp("reserve")), ("charge", failing_action, comp("charge"))]
    result = run_saga(steps)
    ok = ok and result["status"] == "failed" and result["completed_steps"] == ["reserve"]
    ok = ok and "comp:reserve" in log
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Microservices Patterns Tool")
    sub = parser.add_subparsers(dest="command")

    cb_p = sub.add_parser("demo-circuit-breaker")
    cb_p.add_argument("--threshold", type=int, default=3)
    cb_p.add_argument("--recovery-timeout", type=int, default=60)

    saga_p = sub.add_parser("run-saga")
    saga_p.add_argument("--steps", required=True, help="comma-separated step names")
    saga_p.add_argument("--fail-at", default=None, help="step name to simulate failure at")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "demo-circuit-breaker": cmd_demo_circuit_breaker,
        "run-saga": cmd_run_saga,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
