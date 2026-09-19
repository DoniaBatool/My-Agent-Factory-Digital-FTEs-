
## 1.1.0 - 20260914-111156
Replaced TODO stub with real spec/plan/tasks scaffolding + acceptance-criteria parsing + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 44.0%.

## 1.2.0 - 20260919-063050
Bulletproofing pass: added slugify edge cases (multi-special-char collapse, empty string), acceptance-criteria edge cases (empty description, mixed bullet/numbered markers, blank-line handling), scaffold_feature edge cases (explicit acceptance_criteria overrides parsed ones, no-criteria default task, plan.md TBD sections), full CLI layer tests (cmd_scaffold, cmd_parse_acceptance_criteria, cmd_test), main() dispatch tests (no-command help path, default features-root, end-to-end per subcommand), required-arg enforcement (SystemExit for missing --name/--description/positional description), and subprocess smoke tests exercising the __main__ guard. Coverage 44%->97%, mutation score measured at 100% (7/7 mutants).
- Verified 7 pre-existing test(s) still pass
- 21 new test(s) added
- Coverage of scripts/tool.py: 98.0%
