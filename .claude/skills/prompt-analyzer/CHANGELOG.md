
## 1.1.0 - 20260914-110726
Replaced generic 8-command TODO stub with real intent-detection/keyword-extraction/skill-mapping logic + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 47.0%.

## 1.2.0 - 20260919-062858
Bulletproofing pass: added 33 new tests covering the CLI layer (every cmd_* function called directly and via main() end-to-end), required-prompt positional-arg enforcement (SystemExit when omitted for analyze/detect-intent/extract-keywords), regex word-boundary correctness (recreate must not match create), both optimise/optimize spellings, the not-working phrase, case-insensitive keyword extraction, exact longest-keyword-first ordering guarantee, empty-string inputs, the analyze command's known-intent-but-no-skills success branch, cmd_test's failure branch, and a subprocess __main__ smoke test. Coverage 47%->98% (only the __main__ guard line remains, by design). Mutation score measured at 100% (3/3 mutants killed).
- Verified 8 pre-existing test(s) still pass
- 33 new test(s) added
- Coverage of scripts/tool.py: 99.0%
