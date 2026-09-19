
## 1.1.0 - 20260914-113737
Replaced TODO stub with real vercel.json validation, env var diffing, deploy command builder, build-output checks and domain validation, 12 tests
- Verified 0 pre-existing test(s) still pass
- 12 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 75.0%.

## 1.2.0 - 20260919-062907
Bulletproofing pass: added 21 new tests covering vercel.json validation gaps (routes/env type checks, version boundaries 1 and 3, multi-error accumulation, empty config), env-var diff empty-input case, generate_deploy_command's default/env-file/empty-name paths, check_build_output_dir for all remaining frameworks plus exact-match vs partial-prefix distinction, domain-name edge cases (leading/trailing dot, leading/trailing hyphen in a label), print_success/print_error output, cmd_test's subprocess construction (mocked to avoid recursive pytest spawn), main() dispatch/required-subcommand enforcement, and a subprocess smoke test hitting the __main__ guard. Coverage 75%->97%, mutation score measured at 100% (6/6 mutants).
- Verified 12 pre-existing test(s) still pass
- 21 new test(s) added
- Coverage of scripts/tool.py: 98.0%
