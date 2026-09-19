
## 1.1.0 - 20260914-112354
Replaced TODO stub with real pool-size calculation formula + SQLAlchemy config generation + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 30.0%.

## 1.2.0 - 20260919-062330
Bulletproofing pass: added 15 new tests covering the CLI layer (cmd_calculate_pool_size, cmd_generate_config, cmd_test, main() dispatch and no-command help path), required-argument enforcement for all 4 required argparse args via SystemExit, boundary case where available budget floors at num_instances, default reserved_for_admin behavior, and a subprocess smoke test exercising the __main__ guard. Coverage 30%->96%, mutation score measured at 92.3% (12/13 mutants; the sole survivor at scripts/tool.py:62 is an equivalent mutant -- the ok=False fallback inside cmd_test's self-test can only execute if calculate_pool_size(0,100) failed to raise ValueError, which is structurally impossible given the guard at the top of that function).
- Verified 6 pre-existing test(s) still pass
- 15 new test(s) added
- Coverage of scripts/tool.py: 97.0%
