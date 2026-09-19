
## 1.1.0 - 20260914-113344
Replaced TODO stub with real hash-based stable rollout bucketing, config validation, override precedence and merge logic, 11 tests
- Verified 0 pre-existing test(s) still pass
- 11 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 77.0%.

## 1.2.0 - 20260919-062530
Bulletproofing pass: added 30 new tests covering CLI layer (cmd_test with mocked subprocess to avoid the tool's inherent self-invoking recursion, main dispatch including the required-subparser missing-command SystemExit), a reference-hash re-implementation of stable_bucket to catch formula mutations, exact rollout-percentage boundary (bucket==pct disabled vs bucket+1 enabled), missing-global-key default-True behavior, non-bool/non-dict config validation errors, no-user-id rollout paths, merge_flag_configs fallback branch, custom-stages rollout progression including the no-greater-stage fallback, print_success/print_error output, and a subprocess smoke test of the __main__ guard via the no-command argparse-required path. Coverage 77%->98% (only __main__ guard line unreachable in-process). Mutation score measured at 100% (15/15 mutants killed) after adding a test for the missing-global-defaults-to-True behavior that an initial run showed surviving.
- Verified 11 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 98.0%
