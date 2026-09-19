
## 1.1.0 - 20260914-112620
Replaced TODO stub with real GraphQL SDL generation + N+1 risk heuristic detection + 5 fixed tests
- Verified 0 pre-existing test(s) still pass
- 5 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 40.0%.

## 1.2.0 - 20260919-063635
Bulletproofing pass: added 20 new tests covering CLI layer (cmd_build_sdl, cmd_check_n_plus_one, cmd_test, main dispatch), required-arg enforcement (missing --types, missing --query-fields, missing path positional), malformed JSON input to build-sdl, N+1 regex edge cases (case sensitivity, query/fetch verbs beyond get, word-boundary matching of get_by_id-style names, and the real greedy-body-capture behavior that merges vs separates adjacent for-loops), empty-fields SDL generation, and a subprocess smoke test exercising the __main__ guard. Coverage 40%->97% (only __main__ guard line unreachable in-process). Mutation score measured at 100% (5/5 mutants killed).
- Verified 5 pre-existing test(s) still pass
- 20 new test(s) added
- Coverage of scripts/tool.py: 98.0%
