done: prepare.py GUIDE asks to quote the answering sentences first and cite only quoted excerpts; evidence budget
  18k -> 8k; new verify.py (missing_names: capitalized names of the question never said in the history) adds a
  note "X never came up ... answer is INSUFFICIENT_EVIDENCE". Dev sample (100, no holdout, seeded): acc 0.32 -> 0.43,
  false_abstention 0.52 -> 0.20, evidence_f1 0.32 -> 0.57, abstention_recall 0.76 -> 0.52.
  Details: experiments/verify/20261031-0214-abstention.md. Harness: experiments/verify/harness.py, run_variant.sh.
not done: abstention recall is lower than main (the 7B stand-in quotes "guitar" for a "violin" question and answers
  anyway); not measured on Reactor; (c) excerpt order by relevance not run on the LLM (dropped, budget first);
  QA-model (roberta squad2) gate not tried (needs a dependency).
learned: the stand-in blurts INSUFFICIENT_EVIDENCE without reasoning when the evidence is long; near-miss warnings
  in the GUIDE raise false abstention a lot (quote2: 0.65). Reranker-relative cutoffs never bind before the budget.
  ask.py's ref = hash(qid) differs per process: set PYTHONHASHSEED=0 for comparable local runs.
next: Reactor eval of this branch on the same 100 ids (is Reactor's recall better than Qwen's?); then a recall fix
  that does not re-add warnings, e.g. compare quoted noun vs question noun in code and add a targeted note, or a
  per-type budget (12k for temporal/counting).
update 03:30: GUIDE now demands the [E#] labels on the final line (Reactor may drop them there): answered replies
  without labels 3/72 -> 0/69, evidence_f1 0.567 -> 0.607 (experiments/verify/20261031-0330-final-line-labels.md).
blocked: main switched to the "rockets" AGENTS.md; prepare.py there belongs to R1 HYBRID and verification to R7
  GUARDIAN. Rebase onto main conflicts in prepare.py; not resolved. The human decides: port as a rocket part, or hand
  the GUIDE/budget/verify.py change to R1.
update 06:00: ported onto patryk/rakieta as branch verify/abstention-rakieta (R1 owns prepare.py on our machine):
  R1 acc 0.24 -> 0.31, false abstention 0.65 -> 0.45, abstention recall 0.80 -> 0.72, evidence F1 0.16 -> 0.41
  (experiments/verify/20261031-0600-port-rakieta.md). Cherry-picked 78819d5 on verify/abstention. Finding:
  coord/findings/20261031-0600-pw-claude-quote-first-abstention.md. Not done: merge into patryk/rakieta (owner's
  call), Reactor check, recall recovery.
