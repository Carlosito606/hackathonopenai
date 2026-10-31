# Answer-level check of retrieval/recall-audit on the stand-in (Qwen2.5-7B-Instruct-4bit, mlx_lm :8899)

Questions: 60 dev, non-holdout, multi-session (29) + temporal-reasoning (31) where the change fires (counting /
two-event regex or a date window); random.seed(0) from the 300 already-embedded ids.
Plans: `experiments/retrieval/plan_ids.py` (prepare.plan_question) with base retrieval.py (cd31788) and this branch,
run through `~/vibathon/gpujob`; prepare.py unchanged, so no question_date (falls back to last session date).
Then `ask.py --local`, `reactor/predictions.py --abstain-on agent,no-answer`, `score.py`.

| | n | correct (score.py) | unjudged | false_abstention | evidence_f1 | correct incl. hand-judged unjudged |
|---|---|---|---|---|---|---|
| base multi-session | 29 | 0.034 | 0.241 | 0.724 | 0.139 | 2/29 |
| new multi-session | 29 | 0.069 | 0.241 | 0.690 | 0.127 | 1/29 |
| base temporal | 31 | 0.065 | 0.323 | 0.613 | 0.183 | 3/31 |
| new temporal | 31 | 0.065 | 0.387 | 0.548 | 0.167 | 3/31 |
| base all | 60 | 0.050 | 0.283 | 0.667 | 0.162 | 5/60 |
| new all | 60 | 0.067 | 0.317 | 0.617 | 0.148 | 4/60 |

Hand judging (me, gold vs answer): base right on 5 (movie festivals 4, Nightingale, Page Turners, smart thermostat,
taxi $6); new right on 4 (Nightingale, Page Turners, United Airlines, backpack 6 days); new loses festivals (3 vs 4)
and thermostat (abstained), gains United and backpack.
Reading: the stand-in abstains on ~2/3 of these questions either way, so 5 vs 4 of 60 is noise; this does not show
that more sessions in the evidence help or hurt the reader. Evidence F1 drops 0.162 -> 0.148 (more sessions
shown, the stand-in cites more of them). Needs a Reactor mini run on the same 60 ids to decide.
Side note for VERIFIER: 4 answers are literally "Sombra" (the GUIDE's example answer) or "E1"/"E3" (a label alone).
