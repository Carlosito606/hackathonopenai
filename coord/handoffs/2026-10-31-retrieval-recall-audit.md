done: eval_retrieval.py fixed (build_evidence call was broken after the split) and extended (holdout excluded by id
  and text, --ids/--types/--details/--dump, streams only needed histories). Embedder.ensure saves every 1500
  sessions (killed runs keep progress). retrieve(): (1) questions naming a period ("N days/weeks ago", "past/last N",
  "in/since <Month>") also rerank the best 30 chunks of sessions dated in it, and those sessions get +4 logit in the
  evidence order; (2) counting / two-event questions (MULTI regex) order chunks with -1 logit per earlier chunk of
  the same session, so the 18k budget reaches more sessions; (3) sub-query reranker scores combined in logit space
  (the old "-0.5" was applied to probabilities and silenced sub-queries). Optional question_date kwarg.
  Tools: experiments/retrieval/{pick_cached,variants,audit_plan,grep_plan}.py. Numbers: experiments/retrieval/20261031-0130-recall-audit.md
not done: full dev minus holdout (300/398 evaluated); dev-large only 30 questions; prepare.py does not pass
  question_date yet (request in coord/requests/retrieval-to-verifier-question-date.md); no answer-level (stand-in)
  run of the change; paraphrase misses outside the fused top 80 ("kitchen appliance" vs "smoker").
learned: the CrossEncoder returns sigmoid probabilities, so build_evidence's min_score=-6 never fires; test sessions
  are short, so test evidence already holds 10-40 sessions; worst test pattern = counting inside a date window
  ("in August", "since March"), where in-window mentions lose to topical out-of-window chunks.
next: answer-level check on the stand-in for counting/temporal questions (more sessions = more distractors for the
  reader); a paraphrase pass (sub-queries from question nouns' hypernyms or HyDE) for vague "N days ago" questions.
