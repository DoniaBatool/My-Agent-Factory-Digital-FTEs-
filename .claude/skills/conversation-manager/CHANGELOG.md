
## 1.1.0 - 20260914-113317
Replaced TODO stub with real user-isolation, pagination, cascade-delete-plan and preview helpers, 10 tests
- Verified 0 pre-existing test(s) still pass
- 10 new test(s) added

## 1.1.0 (baseline refresh) - 20260916-070313
Established test-body-hash baseline for the new guardrails (test-body hashing, coverage-never-shrinks). No implementation change.

## 1.1.0 (baseline refresh) - 2026-09-16
Backfilled guardrail baseline: coverage 79.0%.

## 1.2.0 - 20260919-062626
Bulletproofing pass: added 15 new tests covering print_success/print_error output, boundary/edge cases in latest_message_preview (exact max_len boundary, whitespace collapsing), build_conversation_list fallback to conv.created_at, paginate_messages non-positive-limit rejection and before-earliest-id empty-page edge case, cascade_delete_plan no-match case, scoped_conversations_for_user missing-key filtering, and the CLI layer (cmd_test with subprocess.run mocked to verify command construction and returncode forwarding for both success and failure, main()'s required-command enforcement, unknown-command rejection, and dispatch-table propagation of return codes via SystemExit). Coverage 79%->97% (only the if __name__=="__main__" guard line remains uncovered), mutation score measured at 100% (12/12 mutants killed).
- Verified 10 pre-existing test(s) still pass
- 15 new test(s) added
- Coverage of scripts/tool.py: 98.0%
