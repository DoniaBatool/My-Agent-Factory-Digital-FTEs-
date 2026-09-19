
## 1.1.0 - 20260914-110948
Replaced TODO stub with real regex-based secret scanner, security-header checker, threat-model builder + 9 fixed tests
- Verified 0 pre-existing test(s) still pass
- 9 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 43.0%.

## 1.2.0 - 20260919-063910
Bulletproofing pass: added 25 new tests covering scan_secrets masking boundary (exact 6-char match vs 7-char truncation via monkeypatched pattern set), multiple secret categories on one line, correct line-number tracking across repeated matches, check_headers partial-missing case, build_threat_model matching via entry-point keyword alone vs asset keyword alone vs no match, the CLI layer (every cmd_* function called directly and via main() end-to-end dispatch, malformed-JSON handling in check-headers), required-argument enforcement (SystemExit when path/--headers/--assets/--entry-points are omitted), cmd_test's self-test failure branch, and a subprocess __main__ smoke test. Coverage 43%->98% (only the __main__ guard line remains, by design). Mutation score measured at 100% (9/9 mutants killed).
- Verified 9 pre-existing test(s) still pass
- 25 new test(s) added
- Coverage of scripts/tool.py: 99.0%
