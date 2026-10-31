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
## 2026-10-31 karol-claude: milestone 3, error analysis on dev and dev-hard v1

Every wrong decision on dev listed with its cause (entity, QA score and span, question shape); dev-hard v1 errors
split by variant with POLIGON's manifest (analysis only, never fed to the rocket).

- BUG (fixed, qa.py): verify.py put the session date before each chunk and SQuAD answered "how long / how often"
  with it ("How long was I in Korea for?" -> "2023/05/25", "How often do I see Dr. Johnson?" -> "2023/05/21").
  Without the date "Korea" abstains. The AUCs in coord/findings/*squad2-verifier.md were measured with the date.
- BUG (fixed, entities.py): names ran across punctuation ("Emma, Rachel and Alex" -> "Emma Rachel").
- FIXED: holidays and degree words are not names; "Valentine's day" and "Bachelor's degree" were the two `pack`
  false abstentions (chats say "February 14" and "BS").
- FIXED (qa.py): positions in a list ("the 27th of the 100 prompt parameters") are computed answers; the QA gate
  abstained on it once the date was gone.
- DEADEND: entity presence in the whole history instead of the pack. Names: same 6/25 and 2/398 as the pack;
  head nouns of noun phrases 1/25 for 7/398; of other content runs 2/25 for 22/398; compound nouns as one phrase
  7/25 for 101/398; multi-word names as one phrase 1/25 for 3/398. Swapped words ("football", "violin", "Korea")
  occur somewhere in 50 noisy sessions.
- dev-hard v1 with the milestone-2 code (runs/r7/20261030-2336-6b9dc3c, removed from the tree, in git history at aac6aeb): `pack` 16/107 right, 0/398 false;
  `pack` + QA 23/107, 3/398. On dev's own 25 unanswerable questions the entity gate drops from 6 to 1: injected
  near-miss sessions carry the missing names. On the remove variants QA's best span comes from an injected session
  in 30 of 32 scored questions, often with high confidence ("previous occupation" -> "software developer" 5.6,
  "painting worth" -> "$250" 10.4): no threshold separates them. Most misses are computed shapes the QA gate skips
  (multi-session 17 of 21).
- NOT DONE on purpose: POLIGON drops injected sessions with a first-person sentence holding 60% of the question's
  words, so "the answer must sit in such a sentence" would score well on dev-hard by construction, not on test.
- Question shapes for the QA gate, from stored QA scores (dev / dev-hard, right then false): base 13/25 3/398,
  26/107 3/398; + positions in a list 13/25 2/398, 26/107 2/398 (KEPT); + "how long have I been" 11/25 1/398,
  24/107 2/398 (DROPPED: it also holds swapped-entity questions the gate caught).
- Result (runs/r7/20261031-0021-aac6aeb, runs/r7/20261031-0055-aac6aeb): dev 13/25 right, 2/398 false (was 12/25, 3/398); dev-hard 26/107,
  2/398 (was 23/107, 3/398). `pack` alone has no false abstention left on either.
## 2026-10-31 karol-claude: reverted the "last / latest" exclusion (5546b48)

The QA gate briefly skipped "the last X I mentioned" questions. The idea came from looking at the questions R7
abstained on in the TEST split (no gold seen), which is fitting rules to the test; the reviewer of PR #5 flagged it.
Dev alone gave thin support (one false abstention fewer, no change on dev-hard), so the rule is gone. From here on
no rule is designed from test questions; the test split is only run, never read.
## 2026-10-31 karol-claude: R7's gate on R1's real candidates

R1 at 926005e with the reranker (runs/r1/20261030-2320-926005e-{dev,hard}, PR #9), read with run.py --cands; R7's
pack is rebuilt from R1's turn ranking with memsys.build_evidence (all gold in the pack: dev 0.922, dev-hard 0.824;
R1's own packs differ). Same QA threshold and shapes (dev-chosen).
- dev: `pack` 8/25 right, 2/398 false (BM25: 6/25, 0/398); `pack` + QA 13/25, 2/398 (BM25: 13/25, 1/398).
- dev-hard v1: `pack` 23/107, 4/398 (BM25: 16/107, 0/398); `pack` + QA 27/107, 4/398 (BM25: 26/107, 2/398).
The gate does about the same on either retriever. On R1's candidates the entity gate catches more and also abstains
falsely more often; why was not checked.
## 2026-10-31 karol-claude: DEADEND, entity swap sensitivity (swap.py)

Swap the question's most specific word (longest name, else the word rarest in the history) for a made-up one and
score both questions with SQuAD 2.0 on the same 8 chunks; a small drop should mean the evidence is not about that
entity. Dev minus holdout, 423 q: AUC of the drop 0.830 vs 0.868 for the plain QA score (single-fact shapes: 0.890
vs 0.916). Added to the gate it buys recall only with mass false abstentions (drop < 0.5: 24/25 right, 134/398
false). A made-up word lowers SQuAD's confidence almost always, near-miss or not. Not run on dev-hard.
## 2026-10-31 karol-claude: DEADEND, answer-name co-location

Abstain when SQuAD's best span comes from a session where a name of the question (or a noun-phrase head) does not
occur. Added to the gate, single-fact shapes, names only: dev +1 right / +3 false (BM25), +0 / +4 (R1 candidates);
dev-hard +1 / +3 (BM25), +6 / +2 (R1). With noun phrases: about +2 to +20 right for +28 to +30 false. Not
consistent and near 1:1. With a reader that answers ~90% of answerable questions right and already abstains on most
near-misses, an extra rule needs far better than 1:1 to pay.
## 2026-10-31 karol-claude: milestone 4, the gate against the real reader (Reactor t10)

The 43 questions R7's gate (`pack` + QA < -5, BM25 candidates) abstains on: 15 dev minus holdout, 28 dev-hard v1.
Reactor got R1's prompt (prepare.py GUIDE) on R7's evidence (plan.py), run by Karol 00:12-01:04 UTC, 43/43
answered, then gate_value.py:
- Reactor abstained on 41 of 43 by itself: 38 of the 39 unanswerable and 3 of the 4 answerable ones.
- gain 1: Reactor answered an unanswerable single-session-assistant question ("UCLA Mindful Awareness Research
  Center"); loss 1: Reactor answered a temporal question right ("27"). Net 0.
Verdict: with R1's prompt (near misses do not count, abstain only when nothing states it about the user) the reader
already abstains where the cheap gate would; laying R7's gate over the ship gains nothing. The gate predicts the
reader's abstention 41/43, which could save reader calls when reader time is short. On the 4 answerable questions
the gate flags, the gold sessions were in R7's pack (all of them in 3, one of two in 1); Reactor still abstained on 3:
a duration counted from dates, a paraphrased gift, a bedtime on a relative day. Hard answers, not missing evidence.