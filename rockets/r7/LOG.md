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

## 2026-10-30 karol-claude: milestone 2, SQuAD 2.0 no-answer signal

torch 2.6.0 (CPU) loads on this laptop where 2.15 failed. qa.py scores the top 8 candidate chunks (~10 min for 423
questions). Run runs/r7/20261030-2314-73a19d0.

- QA on every question shape except the assistant's: recall 0.68 at -5 but false abstention 0.068 (multi 10/97,
  temporal 16/102). DROPPED: counts, sums and orderings have no answer span.
- QA on non-computed shapes, "how long"/"how much" excluded: 127 questions, recall 0.36 at -5. DROPPED: "How long
  was I in Korea for?" has a stated answer.
- KEPT: "how long"/"how much" in, orderings ("who ... first") and comparisons ("than") out: 162 questions, AUC 0.925
  on them. With `pack`, threshold -5: recall 0.48 (ss-user 4/5, temporal 5/5, multi 3/10, k-update 0/5), false
  abstention 0.008 (3/398). Threshold picked on 25 unanswerable questions, so dev-hard decides.
- Knowledge-update 0/5 with every signal: the swapped entity sits in a real, similar session.