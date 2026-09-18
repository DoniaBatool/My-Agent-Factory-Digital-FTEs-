
## 1.1.0 - 20260914-110841
Replaced TODO stub with real salted PBKDF2 hashing, policy checks, reset tokens + 9 fixed tests
- Verified 0 pre-existing test(s) still pass
- 9 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks, golden-file lock, mutation testing). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 50.0%, mutation score 0.62 (8 mutants).

## 1.2.0 - 20260918-084220
Bulletproofing pass: added 27 new tests (CLI layer coverage, argparse required-flag enforcement, password-policy edge cases: exact-length boundary, individual rule violations, malformed hash segments, deterministic salt, reset-token exact-expiry boundary). Coverage 50%->99%, mutation score 62%->100% (8/8 mutants killed).
- Verified 9 pre-existing test(s) still pass
- 27 new test(s) added
- Coverage of scripts/tool.py: 99.0%
- Mutation kill-score: 100%
