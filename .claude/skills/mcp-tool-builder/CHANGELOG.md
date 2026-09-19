
## 1.1.0 - 20260914-112650
Replaced TODO stub with real MCP tool schema validation + typed stub generation + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 49.0%.

## 1.2.0 - 20260919-062316
Bulletproofing pass: added CLI layer tests (cmd_validate_schema, cmd_generate_stub, cmd_test), main() dispatch tests (no-command help path, end-to-end per subcommand via monkeypatched argv), required-arg enforcement (SystemExit for missing --schema/--name), edge cases (_py_type default mapping, no-properties schema, default description/idempotent fallback), and a subprocess smoke test exercising the __main__ guard. Coverage 49%->98%, mutation score measured at 100% (6/6 mutants).
- Verified 7 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 99.0%
