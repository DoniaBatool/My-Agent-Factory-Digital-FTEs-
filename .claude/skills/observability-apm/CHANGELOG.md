
## 1.1.0 - 20260914-113416
Replaced TODO stub with real span parsing/tree-building, percentile aggregation (no numpy) and error-rate alerting, 10 tests
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 78.0%.

## 1.2.0 - 20260919-063449
Bulletproofing pass: added print_success/print_error output tests, boundary-value tests (zero-duration span, threshold-exact exclusion for detect_slow_spans and check_error_rate using strict >), edge cases (empty span list, missing parent_id key, precomputed-duration span bypassing revalidation, single-sample and empty-list percentile/aggregate paths, zero-total error rate, negative total/errors rejection), and CLI-layer tests for cmd_test (subprocess invocation mocked to verify exact command construction without recursive pytest spawning) and main()'s dispatch/required-subcommand enforcement. Coverage 78%->98%, mutation score measured at 100% (11/11 mutants).
- Verified 10 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 98.0%
