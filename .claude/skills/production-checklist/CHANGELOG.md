
## 1.1.0 - 20260914-111223
Replaced TODO stub with real go-live checks (.env gitignored, no hardcoded secrets, tests exist, health endpoint present) + 8 fixed tests
- Verified 0 pre-existing test(s) still pass
- 8 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 58.0%.

## 1.2.0 - 20260919-064236
Bulletproofing pass: added .gitignore wildcard-pattern and present-but-lacking-.env variants, secret-detection edge cases (case-insensitive key names, sub-6-char values not flagged, no files, extensions outside allowlist, multiple offenders, unreadable-file OSError handling via monkeypatched read_text), tests_exist singular test/ dir variant, health-endpoint case-insensitivity/no-leading-slash and unreadable-file OSError handling, run_checklist all-pass and offenders-detail tests, full CLI layer tests (cmd_run_checklist ready/not-ready incl. JSON-validity check, cmd_test), main() dispatch tests (no-command help path, end-to-end per subcommand), required positional-arg enforcement (SystemExit for missing project_root), and subprocess smoke tests exercising the __main__ guard. Coverage 58%->98%, mutation score measured at 100% (15/15 mutants).
- Verified 8 pre-existing test(s) still pass
- 24 new test(s) added
- Coverage of scripts/tool.py: 99.0%
