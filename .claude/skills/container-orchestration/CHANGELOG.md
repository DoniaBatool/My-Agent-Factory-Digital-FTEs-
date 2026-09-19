
## 1.1.0 - 20260914-112423
Replaced TODO stub with real k8s Deployment manifest generation + resource-quantity validation + 6 fixed tests
- Verified 0 pre-existing test(s) still pass
- 6 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 28.0%.

## 1.2.0 - 20260919-062454
Bulletproofing pass: added 19 new tests covering the CLI layer (cmd_generate_deployment, cmd_validate_resources, cmd_test, main() dispatch and no-command help path), required-argument enforcement for --name/--image/positional value via SystemExit, k8s quantity regex edge cases (bare integer, decimal+Gi, case-sensitive suffix, negative values, trailing/leading garbage), and a subprocess smoke test exercising the __main__ guard. Coverage 28%->96%, mutation score measured at 83.3% (5/6 mutants; the sole survivor at scripts/tool.py:82 is an equivalent mutant -- the ok=False fallback inside cmd_test's self-test can only execute if build_deployment_manifest('x','y',cpu_request='not-a-quantity') failed to raise ValueError, which is structurally impossible since 'not-a-quantity' fails the k8s quantity regex; with only 6 total mutable comparison/boolean sites in this file, 5/6 is the maximum achievable score without a contrived test).
- Verified 6 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 97.0%
