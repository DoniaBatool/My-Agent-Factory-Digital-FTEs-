
## 1.1.0 - 20260914-111021
Replaced TODO stub (the one README.md names as a TDD enforcer) with real boundary-value generation, leap-year/month-end date edge cases, calendar-correct add_months, matrix builder + 9 fixed tests
- Verified 0 pre-existing test(s) still pass
- 9 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 50.0%.

## 1.2.0 - 20260919-062130
Bulletproofing pass: added 21 new tests covering CLI layer (cmd_boundary_values, cmd_date_edge_cases, cmd_build_matrix, cmd_test, main dispatch), required-arg enforcement (missing --fields, missing type positional), malformed JSON input to build-matrix, the previously-uncovered feb_last_day_non_leap branch (both leap and non-leap outcomes), default-year behavior, float NaN and string boundary values, multi-field matrix accumulation, and a subprocess smoke test exercising the __main__ guard. Coverage 50%->98% (only __main__ guard line unreachable in-process). Mutation score measured at 100% (6/6 mutants killed).
- Verified 9 pre-existing test(s) still pass
- 21 new test(s) added
- Coverage of scripts/tool.py: 99.0%
