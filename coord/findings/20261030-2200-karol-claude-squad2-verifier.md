agent: karol-claude
fact: deepset/roberta-base-squad2 (best span minus no-answer, over BM25 top-8 turn chunks) separates answerable
from unanswerable dev questions with AUC 0.83: 0.99 single-session-user, 0.95 knowledge-update, 0.81 multi-session,
0.65 temporal. 55% of answerable temporal questions score below 0 (answers are computed, not spans).
Top escapes: "Software Engineer Manager" (span "five"), "table tennis" (span "weekly"); word-prefix overlap gave
"Korea" coverage 1.0 by matching "Korean".
evidence: 526 dev questions, CPU, ~11 min.
so: gate the QA score by question type; compare whole multi-word entities, not tokens.
