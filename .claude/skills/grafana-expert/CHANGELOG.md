
## 1.1.0 - 20260914-110435
Restored + strengthened prerequisite/test logic that had regressed to a 1-of-6-checks stub; added 14 fixed regression tests
- Verified 0 pre-existing test(s) still pass
- 14 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 42.0%.

## 1.2.0 - 20260919-063404
Bulletproofing pass: added 40 new tests covering the full CLI layer (check_prerequisites, install, setup_datasource, create_dashboard, provision, configure_alerting, run_tests, troubleshoot, main dispatch), argparse choice validation (invalid --method), real run_command subprocess behavior (shell/capture/text flags, timeout handling, and generic-exception path), boolean-literal edge cases (dashboard overwrite flag, provisioning isDefault default, os.makedirs exist_ok idempotency), the partial-failure remediation-warning branch and per-check success/error icon selection in run_tests, the provisioning-directory-missing-alone-does-not-fail branch in check_prerequisites, and a subprocess smoke test of the __main__ guard via check-prerequisites. Coverage 42%->99% (only __main__ guard line unreachable in-process). Mutation score measured at 100% (21/21 mutants killed) after two iterations that found and fixed genuinely unobserved branches (run_tests warning-print threshold, per-check icon selection, os.makedirs exist_ok).
- Verified 14 pre-existing test(s) still pass
- 40 new test(s) added
- Coverage of scripts/tool.py: 99.0%
