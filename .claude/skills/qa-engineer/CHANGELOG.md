
## 1.1.0 - 20260914-111057
Replaced TODO stub with real risk-based test planning, severity classification, bug-report formatting, and a run-tests command that genuinely shells out to pytest (previously always printed success) + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 42.0%.

## 1.2.0 - 20260919-063456
Bulletproofing pass: added 25 new tests covering the CLI layer (every cmd_* function called directly and via main() end-to-end dispatch, including run-tests against a real passing/failing pytest target), required-argument enforcement (SystemExit when --flows, description positional, --title/--repro/--expected/--actual, or the run-tests target positional are omitted), classify_severity's rule-priority ordering when multiple patterns match the same text, multiword risk-keyword substring matching in build_test_plan, cmd_test's self-test failure branch, and a subprocess __main__ smoke test. Coverage 42%->98% (only the __main__ guard line remains, by design). Mutation score measured at 100% (14/14 mutants killed).
- Verified 8 pre-existing test(s) still pass
- 25 new test(s) added
- Coverage of scripts/tool.py: 99.0%
