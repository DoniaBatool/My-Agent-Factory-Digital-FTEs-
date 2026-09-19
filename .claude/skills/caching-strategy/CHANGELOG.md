
## 1.1.0 - 20260914-112329
Replaced TODO stub with real cache-key building, TTL policy suggestion, glob-based invalidation matching + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 37.0%.

## 1.2.0 - 20260919-062641
Bulletproofing pass: added 29 new tests covering CLI layer (cmd_build_key, cmd_suggest_ttl, cmd_match_invalidation, cmd_test, main dispatch table via sys.argv), required-arg/positional enforcement (SystemExit for every required flag/positional across all 3 subcommands), TTL policy edge cases (each pattern in TTL_POLICY individually, case-insensitivity, first-match-wins ordering priority), invalidation glob edge cases (? wildcard, case sensitivity, sorted output), the no-extra-parts cache key case, and the CLI error-message path for a colon-containing key part. Coverage 37%->97%, mutation score measured at 91% (10/11 mutants); the one surviving mutant is a documented equivalent (tool.py:75, the 'ok = False' line inside cmd_test's own self-check exception handler, which is unreachable because build_cache_key always raises ValueError for a colon-containing part under correct code -- flipping it to True/False cannot be observed by any correct-code test path).
- Verified 7 pre-existing test(s) still pass
- 29 new test(s) added
- Coverage of scripts/tool.py: 97.0%
