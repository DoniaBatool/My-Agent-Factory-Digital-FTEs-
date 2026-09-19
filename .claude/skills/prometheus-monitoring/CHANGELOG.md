
## 1.1.0 - 20260914-110550
Restored + strengthened prerequisite/test logic that had regressed to a 1-of-6-checks stub; added 14 fixed regression tests
- Verified 0 pre-existing test(s) still pass
- 14 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 44.0%.

## 1.2.0 - 20260919-062647
Bulletproofing pass: added 44 new tests covering the CLI layer (every cmd_* function called directly and via main() end-to-end dispatch), argparse choice validation (SystemExit on invalid --method/--type), optional-arg defaults, real (unmocked) run_command success/timeout/exception paths, boundary conditions in run_tests' pass-count gate and per-check status marking, dict_to_yaml edge cases (empty list, scalar input), URL-encoding of special characters, and a subprocess-level __main__ smoke test. Coverage 44%->99% (only the __main__ guard line remains, by design). Mutation score measured at 100% (21/21 mutants killed).
- Verified 14 pre-existing test(s) still pass
- 44 new test(s) added
- Coverage of scripts/tool.py: 99.0%
