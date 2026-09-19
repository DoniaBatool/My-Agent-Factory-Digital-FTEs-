
## 1.1.0 - 20260914-112039
Replaced TODO stub with real migration-safety checks, index suggestion, constraint checks + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 41.0%.

## 1.2.0 - 20260919-062837
Bulletproofing pass: added 27 new tests covering regex edge cases (drop_table negative-lookahead for IF EXISTS, rename_column, alter_column_type, multiple simultaneous risks, LIKE case-insensitivity, all comparator operators, word-boundary correctness for dotted table-prefixed columns), check_constraints edge cases (multiline SQL, inline NOT NULL exclusion, malformed input with no parenthesised column list, and a documented regex quirk where VARCHAR(n) columns are never flagged due to the trailing \b anchor being unsatisfiable after a literal closing paren), file-reading CLI commands via tmp_path fixtures, the full CLI layer (cmd_suggest_indexes, cmd_check_migration_safety, cmd_check_constraints, cmd_test, main() dispatch and no-command help path), required-argument enforcement for --where and both path positionals via SystemExit, and a subprocess smoke test exercising the __main__ guard. Coverage 41%->98%, mutation score measured at 100% (5/5 mutants killed).
- Verified 7 pre-existing test(s) still pass
- 27 new test(s) added
- Coverage of scripts/tool.py: 99.0%
