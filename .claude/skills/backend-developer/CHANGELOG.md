# Changelog

## 1.0.0 - 2026-09-20
- Initial gate onboarding: added genuine test suite (48 tests), 99% coverage, 100% mutation score.

## 1.0.0 - 20260920-064043
Initial gate onboarding: added genuine test suite (48 tests), 99pct coverage, 100pct mutation score
- Verified 48 pre-existing test(s) still pass
- 0 new test(s) added
- Coverage of scripts/tool.py: 99.0%

## 1.0.1 - 2026-09-20
- Strengthened mkdir(parents=True) coverage for setup-auth and generate-tests with explicit nested-output-dir tests, closing the last 2 surviving mutants. Final: 50 tests, 99% coverage, 100% mutation score (24/24 mutants killed).

## 1.0.1 - 20260920-160011
Hardened mkdir(parents=True) mutation coverage for setup-auth and generate-tests; 50 tests, 99pct coverage, 100pct mutation score
- Verified 50 pre-existing test(s) still pass
- 0 new test(s) added
- Coverage of scripts/tool.py: 99.0%

## 1.1.0 - 20260926-130919
Bug fix: stray underscore in generated model base-class reference
- Verified 52 pre-existing test(s) still pass
- 0 new test(s) added
- ACKNOWLEDGED change to 1 existing test(s): Bug fix: removed stray leading underscore in generated FastAPI SQLModel class definition (class X(_XBase,...) -> class X(XBase,...)) that would have caused NameError if generated code were run. Updated the test documenting the old buggy behavior to assert the corrected class definition instead, and added regression tests.
  - test_tool.py::test_create_model_custom_fields_produce_exact_class_bodies: 8 -> 9 assert(s)
- Coverage of scripts/tool.py: 99.0%
