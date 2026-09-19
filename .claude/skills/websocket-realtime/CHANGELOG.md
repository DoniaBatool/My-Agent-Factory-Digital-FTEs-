
## 1.1.0 - 20260914-113803
Replaced TODO stub with real room broadcast targeting, message schema validation, heartbeat expiry and sliding-window rate limiting, 12 tests
- Verified 0 pre-existing test(s) still pass
- 12 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 77.0%.

## 1.2.0 - 20260919-063011
Bulletproofing pass: added 19 new tests covering build_room_key's room_id-empty branch, broadcast_targets edge cases (no exclude, empty connections, no room match), validate_ws_message's non-dict payload / both-fields-missing / None-type-is-not-unknown / absent-type-vs-missing-field distinctions, heartbeat_expired's exact-timeout boundary (not expired) vs just-past boundary (expired), rate_limit_check's exact-cutoff eviction boundary and per-connection bucket isolation, serialize_event with None data, print_success/print_error output, cmd_test's subprocess construction (mocked to avoid recursive pytest spawn), main() dispatch/required-subcommand enforcement, and a subprocess smoke test hitting the __main__ guard. Coverage 77%->97%, mutation score measured at 100% (10/10 mutants).
- Verified 12 pre-existing test(s) still pass
- 19 new test(s) added
- Coverage of scripts/tool.py: 98.0%
