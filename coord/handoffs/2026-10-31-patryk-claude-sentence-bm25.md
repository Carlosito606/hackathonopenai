done: on top of patryk/rakieta fee061f, measured two fixes for the test-evidence audit (dev minus holdout, 150
  already-embedded questions, seed 0, via ~/vibathon/gpujob):
  (a) sentence-level BM25 as a third fusion list: DEADEND (multi-session 0.939 -> 0.848), code not kept;
      finding in coord/findings/20261031-0045-patryk-claude-sentence-bm25-deadend.md.
  (b) reranker pool 80 -> 120 for counting/two-event questions (MULTI regex), one line in retrieve():
      all 0.967 -> 0.973, temporal 0.919 -> 0.946, others unchanged; kept (commit 8c8d7cf).
not done: (b) is not in the frozen final run (fee061f); not measured on all 398 dev questions nor at test scale;
  asides inside long chunks (cause a) still unsolved.
learned: giving short sentences a full fusion vote lets topical sentences from other sessions crowd out the
  chunks the reranker needs; extra candidates are safe, reordering the pool is not.
next: for asides, add the top ~10 sentence-BM25 hits as extra reranker candidates only (no fusion vote) and
  measure; check (b) on dev-large when the GPU is free.
