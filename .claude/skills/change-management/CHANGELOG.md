
## 1.1.0 - 20260914-111129
Replaced TODO stub with real change-spec scaffolding, cross-file impact scanning, rollback-note generation + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 46.0%.

## 1.2.0 - 20260919-063627
Bulletproofing pass: added 39 new tests covering CLI layer (cmd_create_change_spec, cmd_scan_impact, cmd_rollback_note, cmd_test, main dispatch table via sys.argv), required-arg enforcement (SystemExit for every required flag across all 3 subcommands), edge cases (slugify punctuation collapsing/empty string, non-numeric-prefix folders ignored by next_change_number, custom/default non_goals, all supported+custom scan_impact extensions, sorted scan results, OSError-on-unreadable-file resilience, missing-intermediate-directory creation, each build_rollback_note step-ordering combination), and a subprocess smoke test exercising the __main__ guard. Coverage 46%->99%, mutation score measured at 80% (8/10 mutants); the 2 surviving mutants are documented equivalents (tool.py:30, the parents=True and exist_ok=True flags on folder.mkdir() inside create_change_spec) -- folder's parent (changes_root) is unconditionally created on the immediately preceding line, and next_change_number() guarantees the computed folder name is always higher than every existing numbered folder, so the target directory can never already exist and its parent can never be missing; no correct-code test path can observe either flag's value.
- Verified 8 pre-existing test(s) still pass
- 31 new test(s) added
- Coverage of scripts/tool.py: 99.0%
