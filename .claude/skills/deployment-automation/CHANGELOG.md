
## 1.1.0 - 20260914-112233
Replaced TODO stub with real env-var validation, curl-based smoke checks, rollback-plan generation + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 37.0%.

## 1.2.0 - 20260919-063547
Bulletproofing pass: added 20 new tests covering run_smoke_check's full branch matrix (HTTP 200 success, non-200 failure, TimeoutExpired, missing curl binary via FileNotFoundError, and a mocked-subprocess assertion on the exact curl invocation kwargs: capture_output/text/timeout/url), the CLI layer (cmd_check_env_vars via monkeypatched real os.environ for both present and missing cases, cmd_smoke_check success/failure with run_smoke_check mocked, cmd_rollback_plan, cmd_test, main() dispatch and no-command help path), required-argument enforcement for --required/--url/--previous-version via SystemExit, and a subprocess smoke test exercising the __main__ guard. Coverage 37%->97%, mutation score measured at 100% (9/9 mutants killed).
- Verified 7 pre-existing test(s) still pass
- 20 new test(s) added
- Coverage of scripts/tool.py: 98.0%
