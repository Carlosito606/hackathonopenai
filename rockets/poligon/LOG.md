# POLIGON log (append-only)

## 2026-10-30 23:00 karol-claude-2: dev-hard v1

- Generator `make_dev_hard.py`, seed 0: 505 questions (423 inject + 82 remove), 107 abstain, injected per
  question 3: 173, 4: 177, 5: 155. Build 30 s; `--check` passes; two builds byte-identical.
- First build had two kinds of bad injections, found by reading samples, both fixed with a filter:
  near-copies of a session already in the history (LongMemEval reuses sessions with small edits), and sibling
  questions' evidence sessions ("I recently participated in a 5K charity run" injected into "How many days ago
  did I participate in the 5K charity run?"), which change the gold. Now: no dev evidence session in the pool,
  near-copies dropped, first-person sentences with >= 60% of the question's words dropped.
- Plain BM25 (all turns, `bm25_run.py`), all gold sessions in top 5 sessions, 398 paired answerable questions:

  | type | dev | dev-hard | drop (pts) | injected in top 5 |
  |---|---|---|---|---|
  | k-update | 0.966 | 0.845 | 12.1 | 97% |
  | multi | 0.670 | 0.423 | 24.7 | 98% |
  | ss-asst | 1.000 | 0.989 | 1.1 | 100% |
  | ss-user | 1.000 | 1.000 | 0.0 | 100% |
  | temporal | 0.725 | 0.529 | 19.6 | 94% |
  | all | 0.844 | 0.714 | 13.1 | 98% |

  Top 10: all 0.907 -> 0.852 (-5.5), multi 0.825 -> 0.680 (-14.4), temporal 0.814 -> 0.755 (-5.9).
  Dev numbers equal karol-claude's smoke-test run (0.844 all), so the comparison is on the same footing.
- R1 (`r1_run.py`, root memsys.py unchanged, device cpu): CPU embedding runs at 12 chunks/s; dev has 351,678
  chunks, so R1 dense retrieval on all of dev takes about 8-10 h here (115 s per history), reranking more.
  Not run yet; see the handoff.

## 2026-10-30 23:45 karol-claude-2: judge, injection check, failure analysis (code only)

- `judge.py`: LongMemEval judge prompts (default, temporal off-by-one, knowledge-update "updated answer wins") plus
  the challenge rule "several answers, hedging or negation = wrong"; judges only score.py's unjudged rows; caches
  verdicts. `--selftest` builds 490 cases with known verdicts from dev gold (gold in a sentence, another question's
  answer, hedged, negated, temporal off by one (35) / five, knowledge-update old-then-new).
- `check_injections.py`: 4 question-relevant sentences per injected session, asks whether they answer or contradict.
- `failures.py`: outcomes per type. On R7's gate-only run (no reader) it shows 25/398 packs missing gold.
- Tested only on a mock OpenAI-compatible server (plumbing, cache, table). The stand-in model (Qwen2.5-7B-Instruct
  Q4_K_M, llama.cpp Vulkan build) is downloaded but not started yet.
