
## 1.1.0 - 20260914-113709
Replaced TODO stub with real WCAG relative-luminance contrast ratio math, compliance thresholds, color scale and spacing scale generators, 12 tests
- Verified 0 pre-existing test(s) still pass
- 12 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 81.0%.

## 1.2.0 - 20260919-062803
Bulletproofing pass: added 18 new tests covering hex parsing edge cases (mixed case, no-hash prefix, wrong-length rejection), _clamp boundaries, exact WCAG threshold values (>=4.5 passes, just-below fails, AAA/large boundary), generate_color_scale edge cases (zero steps rejected, single-step identity, lighten/darken direction, extreme-color bounds), spacing_scale invalid-input rejection, print_success/print_error output, cmd_test's subprocess construction (mocked to avoid recursive pytest spawn), main() dispatch/required-subcommand enforcement, and a subprocess smoke test hitting the __main__ guard. Coverage 81%->98%, mutation score measured at 100% (10/10 mutants).
- Verified 12 pre-existing test(s) still pass
- 18 new test(s) added
- Coverage of scripts/tool.py: 99.0%
