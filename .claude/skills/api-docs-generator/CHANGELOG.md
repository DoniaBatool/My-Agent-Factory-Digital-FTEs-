
## 1.1.0 - 20260914-112553
Replaced TODO stub with real FastAPI route extraction + markdown doc generation + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 44.0%.

## 1.2.0 - 20260919-062519
Bulletproofing pass: added 21 new tests covering CLI layer (cmd_extract_routes, cmd_generate_docs with/without --output, cmd_test, main dispatch table via sys.argv), required positional-arg enforcement (SystemExit for both subcommands), regex boundary correctness (handler found at the last line the 5-line search window checks, missed just past it, double-quoted decorators, sync def, patch method), the handler=None / '(unknown)' rendering path, empty-routes doc generation, and file-not-found / missing-file error propagation, plus a subprocess smoke test exercising the __main__ guard. Coverage 44%->99%, mutation score measured at 100% (3/3 mutants).
- Verified 6 pre-existing test(s) still pass
- 21 new test(s) added
- Coverage of scripts/tool.py: 99.0%
