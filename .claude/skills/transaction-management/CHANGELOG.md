
## 1.1.0 - 20260914-113641
Replaced TODO stub with a real ACID-style Transaction class (commit/rollback with reverse-order inverse ops), wait-for-graph deadlock detector and serialization-failure retry, 10 tests
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 81.0%.

## 1.2.0 - 20260919-062702
Bulletproofing pass: added 16 new tests covering Transaction post-rollback state checks (execute/commit after rollback, no-op rollback), deadlock detection boundary cases (empty graph, self-loop), retry_on_serialization_failure exhaustion/exception-filtering/sleep_fn/zero-retries boundary, print_success/print_error output, cmd_test's subprocess construction (mocked to avoid recursive pytest spawn), main() dispatch/required-subcommand enforcement, and a subprocess smoke test hitting the __main__ guard. Coverage 81%->98%, mutation score measured at 100% (10/10 mutants).
- Verified 10 pre-existing test(s) still pass
- 16 new test(s) added
- Coverage of scripts/tool.py: 99.0%
