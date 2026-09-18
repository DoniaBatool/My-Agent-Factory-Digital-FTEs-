
## 1.1.0 - 20260914-110911
Replaced TODO stub with real static ownership-filter/IDOR checks + 9 fixed tests
- Verified 0 pre-existing test(s) still pass
- 9 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks, golden-file lock, mutation testing). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 40.0%, mutation score 1.00 (2 mutants).

## 1.2.0 - 20260918-084756
Bulletproofing pass: added 31 new tests (CLI layer coverage for check-query/scaffold-query/scan-file/test commands, argparse required-positional enforcement, owner-column variants account_id/created_by, word-boundary correctness against substring false-positives, case-insensitivity, all client-supplied-user_id detector variants params/args/body/payload, multi-statement scan_source coverage, statement-truncation boundary). Coverage 40%->98%, mutation score verified 100% (2/2 mutants killed) plus 3 additional manual logic-mutation checks (any->all, word-boundary removal, missing args. alternative) all caught by the suite.
- Verified 9 pre-existing test(s) still pass
- 31 new test(s) added
- Coverage of scripts/tool.py: 99.0%
- Mutation kill-score: 100%
