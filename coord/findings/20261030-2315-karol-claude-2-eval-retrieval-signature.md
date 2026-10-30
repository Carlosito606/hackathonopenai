agent: karol-claude-2 (POLIGON)
fact: [WARNING] eval_retrieval.py on main (d7f02f8) calls `passages, _ = build_evidence(h, cands, q["question_date"])`,
but memsys.build_evidence(history, cands, budget=18000, ..., dates=False) returns one list of evidence dicts: the
question date lands in `budget` and the unpacking fails. It also samples 150 questions by default, while
AGENTS.md section 7 asks for all of dev minus holdout.
evidence: reading memsys.py lines 243-283 and eval_retrieval.py lines 26-28; not run (R1's area, not edited).
so: R1 owner: fix the call (e.g. `build_evidence(h, cands, dates=...)`, sessions = [e["id"] for e in ...]).
Until then, rockets/poligon/r1_run.py writes R1's candidates.jsonl and evidence.jsonl for a whole split with
the same calls as prepare.plan_question.
