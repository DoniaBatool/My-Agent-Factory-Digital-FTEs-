
## 1.1.0 - 20260914-112301
Replaced TODO stub with real CI/Dockerfile pipeline audit + incident runbooks + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 42.0%.

## 1.2.0 - 20260919-062029
Bulletproofing pass: added 12 new tests covering CLI layer (cmd_audit_pipeline, cmd_generate_runbook, cmd_test, main dispatch), required-arg enforcement (missing project_root, invalid incident_type choice via argparse), no-command help path, and a subprocess smoke test exercising the __main__ guard. Coverage 42%->97% (only __main__ guard line unreachable in-process). Mutation score measured at 100% (4/4 mutants killed).
- Verified 6 pre-existing test(s) still pass
- 12 new test(s) added
- Coverage of scripts/tool.py: 98.0%
