# Final code vs the code calibrated on Reactor (no Reactor time left before the final run)

Reactor calibration (39 dev questions) ran on 323eb44. The final code (5871633; plans are identical to bcdc526)
adds retrieval/recall-audit: date windows and session diversity. Check without Reactor:
`experiments/r1/replan.py` on the same 39 questions, then `experiments/r1/diff_plans.py` (323eb44 vs final).

| type | packs changed | gold sessions lost |
|---|---|---|
| abstention (4) | 0 | - |
| single-session-user (6) | 0 | 0 |
| single-session-assistant (6) | 2 (3 -> 6 and 3 -> 10 sessions) | 0 |
| knowledge-update (7) | 3 | 0 |
| multi-session (8) | 6 | 0 |
| temporal-reasoning (8) | 7 | 0 |

No question loses a gold session; packs keep ~17k chars and spread over more sessions where diversity triggers.
Diversity triggers on retrieval.MULTI words or a named period. On the 146 test questions it triggers for 71: 69
counting or date-difference questions (the target: dev-hard multi-session 0.714 -> 0.914, see
20261031-0030-budget.md) and 2 name questions where "before"/"after" matches by chance. The dev ss-assistant
changes came from "first"/"most", which no test question uses. Decision: the final run uses the final code.
Not measured: Reactor's answers on the final code (risk: more sessions, so more near misses, in diversified packs).

Test plan checks (plan-test-bcdc526.jsonl): 146 questions, 15 histories, all test ids present; whole message max
22,328 chars, median 19,845, none over 29,000; no empty evidence; 40 with date tags, 33 with the counting note;
no name from the test data in the answering notes.
