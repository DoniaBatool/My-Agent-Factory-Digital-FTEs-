
## 1.1.0 - 20260914-112726
Replaced TODO stub with a real Circuit Breaker state machine (CLOSED/OPEN/HALF_OPEN) and a real Saga executor with reverse-order compensation + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 42.0%.

## 1.2.0 - 20260919-062735
Bulletproofing pass: added HALF_OPEN re-open-on-failure test, recovery-timeout boundary tests (exactly-at vs one-unit-short), failure-count-reset verification, saga edge cases (empty steps, first-step failure, reverse-order compensation), full CLI layer tests (cmd_demo_circuit_breaker incl. threshold=0 edge case, cmd_run_saga success/failure, cmd_test), main() dispatch end-to-end tests, required-arg enforcement (SystemExit for missing --steps), and subprocess smoke tests exercising the __main__ guard. Coverage 42%->98%, mutation score measured at 92.9% (13/14 mutants) -- the one surviving mutant (line 133, ok=False inside cmd_test's self-test) is a documented equivalent mutant: that branch is defensive code reachable only if the circuit breaker incorrectly lets a call through while OPEN, which never happens with a correct implementation, so no test can observe a difference.
- Verified 6 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 98.0%
