
## 1.1.0 - 20260914-112454
Replaced TODO stub with real Terraform HCL generation (S3, VPC) + variable validation + 7 fixed tests
- Verified 0 pre-existing test(s) still pass
- 7 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 34.0%.

## 1.2.0 - 20260919-064006
Bulletproofing pass: added 31 new tests covering CLI layer (cmd_generate_s3_bucket, cmd_generate_vpc, cmd_validate_variables, cmd_test, main dispatch), required-arg enforcement (missing --resource-name/--bucket-name/--cidr/--required/--provided across all three generator subcommands), validate_hcl_identifier edge cases (leading digit, special chars, empty string), default-parameter pinning for s3 bucket versioning/encryption, custom subnet counts, malformed JSON to validate-variables, and a subprocess smoke test exercising the __main__ guard. Coverage 34%->97%. Mutation score measured at 90.9% (10/11 mutants killed); the one surviving mutant is a documented equivalent at scripts/tool.py:96 (the 'ok = False' line inside cmd_test's own self-test, reached only if generate_vpc's CIDR validation were broken -- unreachable without deliberately breaking the real validation it is meant to self-check, so it is left undisturbed rather than force-killed with a contrived test).
- Verified 7 pre-existing test(s) still pass
- 31 new test(s) added
- Coverage of scripts/tool.py: 98.0%
