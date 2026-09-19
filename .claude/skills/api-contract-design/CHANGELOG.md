
## 1.1.0 - 20260914-112526
Replaced TODO stub with real OpenAPI path-spec building, contract completeness validation, breaking-change detection + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 45.0%.

## 1.2.0 - 20260919-062417
Bulletproofing pass: added 32 new tests covering CLI layer (cmd_build_path_spec, cmd_validate_contract, cmd_check_breaking_change, cmd_test, main dispatch table via sys.argv), required-arg/positional enforcement (SystemExit for every required flag across all 3 subcommands), edge cases (_error_description unknown code fallback, method-name case normalization, unknown HTTP method default, custom response_schema/error_codes, empty spec, removed-method-on-kept-path breaking-change detection), malformed JSON file input, and a subprocess smoke test exercising the __main__ guard. Coverage 45%->99%, mutation score measured at 100% (9/9 mutants).
- Verified 8 pre-existing test(s) still pass
- 32 new test(s) added
- Coverage of scripts/tool.py: 99.0%
