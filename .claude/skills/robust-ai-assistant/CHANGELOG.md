
## 1.1.0 - 20260914-113546
Replaced TODO stub with real retry-with-backoff, fallback chain, response schema validation, input sanitization and circuit-breaker cooldown gate, 10 tests (examples/ preserved)
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 79.0%.

## 1.2.0 - 20260919-063657
Bulletproofing pass: added 21 new tests covering retry_with_backoff (exact exponential sleep-delay sequence, single-attempt-never-sleeps, unlisted exception types propagate uncaught), fallback_chain (primary success never touches fallbacks, empty-fallback-list re-raises primary error), validate_ai_response_schema (non-dict response, empty required-keys list), sanitize_user_input (non-string rejection, exact-max-length boundary, whitespace stripping), should_allow_request (not-tripped passthrough, exact cooldown boundary allows, one-second-early still blocks), previously-uncalled print_success/print_error helpers, and the CLI layer (cmd_test's subprocess invocation mocked for both exit codes, main()'s required-subcommand enforcement, unknown-subcommand rejection, and a subprocess __main__ smoke test that avoids the recursive pytest-invocation trap). Coverage 79%->98% (only the __main__ guard line remains, by design). Mutation score measured at 100% (10/10 mutants killed).
- Verified 10 pre-existing test(s) still pass
- 21 new test(s) added
- Coverage of scripts/tool.py: 99.0%
