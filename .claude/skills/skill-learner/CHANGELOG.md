
## 1.1.0 - 20260914-111319
Replaced TODO stub with real issue-to-skill keyword mapping, structured learning capture/log, and a stage-skill helper that hands off to skill_gate.py for promotion + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 41.0%.

## 1.2.0 - 20260919-062349
Bulletproofing pass: added 24 new tests covering the full CLI layer (cmd_capture_learning, cmd_find_skill_for_issue, cmd_stage_skill, cmd_test, main() dispatch), per-argument required-arg enforcement (--issue/--root-cause/--fix each tested in isolation), default-log-path behavior, case-insensitive/multi-keyword matching, and a subprocess smoke test exercising the __main__ guard. Coverage 41%->98%, mutation score measured at 100% (11/11 mutants).
- Verified 8 pre-existing test(s) still pass
- 24 new test(s) added
- Coverage of scripts/tool.py: 99.0%
