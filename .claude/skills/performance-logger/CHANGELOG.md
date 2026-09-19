
## 1.1.0 - 20260914-113443
Replaced TODO stub with real redaction, duration/percentile aggregation and sliding-window rate limiting, 10 tests
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 80.0%.

## 1.2.0 - 20260919-063810
Bulletproofing pass: added print_success/print_error output tests, redaction substring-matching and non-sensitive-value passthrough tests, format_log_line field-sort-order and no-extra-fields tests, boundary-value tests (zero-duration, is_slow exactly-at-threshold using strict >, rate limiter entry exactly at cutoff, max_per_window=0), independent-bucket-per-key test for the rate limiter, percentile/aggregate single-sample and empty-list edge cases, and CLI-layer tests for cmd_test (subprocess invocation mocked to avoid recursive pytest spawning) and main()'s dispatch/required-subcommand enforcement. Coverage 80%->98%, mutation score measured at 100% (9/9 mutants).
- Verified 10 pre-existing test(s) still pass
- 18 new test(s) added
- Coverage of scripts/tool.py: 98.0%
