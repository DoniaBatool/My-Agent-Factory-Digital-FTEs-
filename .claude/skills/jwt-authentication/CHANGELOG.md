
## 1.1.0 - 20260914-110802
Replaced generic 8-command TODO stub with a real stdlib-only HS256 JWT encode/verify implementation + 9 fixed tests
- Verified 0 pre-existing test(s) still pass
- 9 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks, golden-file lock, mutation testing). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 49.0%, mutation score 0.36 (11 mutants).

## 1.2.0 - 20260918-083229
Bulletproofing pass: added 24 new tests (CLI layer coverage, argparse required-flag enforcement, JWT edge cases: exact expiry boundary, malformed signature/payload, missing exp claim). Coverage 49%->98%, mutation score 36%->91% (10/11 mutants killed; 1 documented equivalent mutant).
- Verified 9 pre-existing test(s) still pass
- 24 new test(s) added
- Coverage of scripts/tool.py: 98.0%
- Mutation kill-score: 91%
