
## 1.1.0 - 20260914-112158
Replaced TODO stub with real Alembic migration generation + zero-downtime add-column checks + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 31.0%.

## 1.2.0 - 20260919-063231
Bulletproofing pass: added 26 new tests covering the CLI layer (cmd_generate_add_column blocked/forced/success paths, cmd_generate_add_index, cmd_check_zero_downtime both paths, cmd_test, main() dispatch and no-command help path), the --not-nullable store_false flag, the default nullable=True behavior when omitted from generate_add_column_migration, multi-column index rendering, required-argument enforcement for every required argparse arg across all three subcommands via SystemExit, and a subprocess smoke test exercising the __main__ guard. Coverage 31%->98%, mutation score measured at 95.5% (21/22 mutants killed; the sole survivor at scripts/tool.py:87 is an equivalent mutant -- the nullable=True literal inside cmd_test's own internal call to generate_add_column_migration is never checked by cmd_test's self-test assertions, which only inspect the migration text for 'op.add_column' and 'def downgrade', so flipping that literal has no observable effect on any correct-code test path).
- Verified 7 pre-existing test(s) still pass
- 26 new test(s) added
- Coverage of scripts/tool.py: 99.0%
