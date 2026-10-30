# R7 LOG (append-only)

## 2026-10-30 karol-claude: milestone 1, entity check in the decide stage

Setup: Windows laptop, CPU only (no CUDA); torch 2.15 fails to load (WinError 126, shm.dll), so no dense model or
reranker here. Candidates: R1 chunking + BM25 (forked from `memsys.retrieve`). Pack: R1 `build_evidence`.
Measured on dev minus holdout (423 q, 25 unanswerable), abstention only, no reader.

- Every content word must be in the pack: abstention recall 0.44, false abstention 0.281. DROPPED: verbs and
  frame words ("attend", "passed between", "earliest") are often absent from excerpts.
- Whole pack vs one session: swapped entities are mostly IN the pack, from other sessions ("Korea" 2 sessions,
  "Shinjuku", "Google", "Italian"). Co-occurrence in one session: recall 0.52-0.60 but false abstention 0.16-0.31.
  DROPPED for now.
- Phrase check bug: entity words had stopwords removed, text did not ("Husbands of Evelyn Hugo" never matched).
  Fixed: both sides drop stopwords and frame words.
- KEPT `pack`: a proper or quoted entity with a word missing from the pack. Recall 0.24 (temporal 0.80),
  false abstention 0.005 (2/398: "Bachelor's" written differently, "Valentine's day" given as a date).
- KEPT as option `pack-strict` / `warn`: also multi-word names not as one phrase and missing head nouns of noun
  phrases (skipped for questions about what the assistant said). Recall 0.32, false abstention 0.050.
