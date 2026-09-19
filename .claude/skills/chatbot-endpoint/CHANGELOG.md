
## 1.1.0 - 20260914-113249
Replaced TODO stub with real payload validation, action-intent classification, response envelope + history trimming helpers, 10 tests
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 58.0%.

## 1.2.0 - 20260919-063847
Bulletproofing pass: added 35 new tests covering CLI layer (cmd_new_conversation_id, cmd_validate_payload, cmd_classify_intent, cmd_test with a mocked subprocess to avoid recursive pytest spawning, main dispatch via sys.argv/SystemExit), required-arg enforcement (SystemExit for both required flags and for the required subparsers.command itself), payload validation boundaries (non-dict payload, missing/non-string message, exact 8000/8001 char boundary, valid conversation_id), intent classification coverage (complete/update/add/list actions, non-string message rejection, complete-without-target confirmation, non-destructive bulk actions never confirming, 'everything' bulk-word variant, double-quoted target extraction, bulk+quoted-target still confirming), response envelope tool_calls pass-through, and trim_history_for_context's zero/negative/oversized max_messages branches, plus a subprocess smoke test exercising the __main__ guard. Coverage 58%->99%, mutation score measured at 100% (8/8 mutants).
- Verified 10 pre-existing test(s) still pass
- 35 new test(s) added
- Coverage of scripts/tool.py: 99.0%
