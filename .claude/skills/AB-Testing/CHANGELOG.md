
## 1.1.0 - 20260914-113128
Replaced TODO stub with real deterministic hash-based variant bucketing + two-proportion z-test significance check + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 37.0%.

## 1.2.0 - 20260919-062244
Bulletproofing pass: added 29-6=23 new tests covering CLI layer (cmd_assign_variant, cmd_check_significance, cmd_test, main dispatch table via sys.argv), required-arg enforcement (SystemExit for each required flag on both subcommands), boundary/edge cases (exact z-threshold tie via >=, se=0 zero-pool case, negative z beyond/below threshold, floating-point tolerance boundary on traffic_split sum, empty split, single-variant split), malformed JSON input, a hash-boundary correctness test for the bucketing comparison, and a subprocess smoke test exercising the __main__ guard. Coverage 37%->96%, mutation score measured at 100% (18/18 mutants).
- Verified 6 pre-existing test(s) still pass
- 23 new test(s) added
- Coverage of scripts/tool.py: 96.0%
