
## 1.1.0 - 20260914-113612
Replaced TODO stub with real JSON log building, correlation id, context flattening, level filtering and redaction, 11 tests
- Verified 0 pre-existing test(s) still pass
- 11 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 80.0%.

## 1.2.0 - 20260919-062555
Bulletproofing pass: added 18 new tests covering redaction edge cases (case-insensitivity, substring match, custom key sets), correlation-id empty-string handling, flatten_context edge cases, level-filter error paths, to_json_log field/timestamp/sort_keys behavior, parse_json_log non-dict JSON, print_success/print_error output, cmd_test's subprocess construction (mocked to avoid recursive pytest spawn), main() dispatch/required-subcommand enforcement, and a subprocess smoke test hitting the __main__ guard. Coverage 80%->97%, mutation score measured at 100% (4/4 mutants).
- Verified 11 pre-existing test(s) still pass
- 18 new test(s) added
- Coverage of scripts/tool.py: 98.0%
