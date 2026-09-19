
## 1.1.0 - 20260914-113509
Replaced TODO stub with real stdlib-only schema validation, coercion, error envelope and email check, 11 tests
- Verified 0 pre-existing test(s) still pass
- 11 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 79.0%.

## 1.2.0 - 20260919-063116
Bulletproofing pass: added 28 new tests covering coerce_value edge cases (bool passthrough/rejection of unrecognized or non-string input, float coercion, TypeError-wrapped-as-ValueError on None), validate_schema boundary values (exact min/max pass, one-below/above fail, None on required vs optional fields, type-mismatch short-circuiting min/max/regex checks without crashing, regex ignored for non-string values), validate_email malformed inputs, build_error_response ordering, previously-uncalled print_success/print_error helpers, and the CLI layer (cmd_test's subprocess invocation mocked for both exit codes, main()'s required-subcommand enforcement via SystemExit, unknown-subcommand rejection, and a subprocess __main__ smoke test that avoids the recursive pytest-invocation trap by exercising the missing-subcommand exit path). Coverage 79%->98% (only the __main__ guard line remains, by design). Mutation score measured at 100% (11/11 mutants killed).
- Verified 11 pre-existing test(s) still pass
- 28 new test(s) added
- Coverage of scripts/tool.py: 98.0%
