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

## 2026-10-31 00:20 karol-claude-2: judge and injection audit on the stand-in model

Stand-in: Qwen2.5-7B-Instruct Q4_K_M (bartowski GGUF), llama.cpp b12004 Vulkan build, `llama-server --port 8897
-c 4096 -ngl 99`, 4 slots; judge prompt ~0.4-1 s with 4 parallel requests on a Ryzen AI 7 PRO 350 laptop.

- `judge.py --selftest`, 490 cases from dev gold: 0.951 agreement. gold in a sentence 100/100, another question's
  answer rejected 99/100, hedged between two rejected 92/100, negated gold rejected 96/100, temporal off by one
  accepted 32/35, off by five rejected 35/35, **knowledge-update "old value, then updated" accepted only 12/20**:
  the judge may under-count answers that also mention the old value.
- Injection audit, first try (yes/no "answers or contradicts?", 4 sentences): useless. Gold evidence sessions got
  "yes" 18/100, random sessions "no" 100/100. Half the gap was the calibration: for k-update, multi and temporal
  the answer is computed and almost never written in one session (1-2 of 15-26). The other half: the excerpt
  missed the answer sentence ("Where did I buy my bookshelf?" -> four bookshelf sentences, not the IKEA one).
- Second try (`check_injections.py`, kept): neighbours of the 4 best sentences, and the model answers the
  question from the excerpt or says NONE. Calibration on the 107 single-session questions whose answer is written
  in an evidence session: excerpt contains the answer 88/107; gold session gives a non-NONE reply 92/107 (85/88
  when the excerpt covers it), matching gold 62/107; a random other session gives NONE 107/107.

## 2026-10-31 01:05 karol-claude-2: R1 dev -> dev-hard v1 (measured by patryk-opencode on Mac Studio)

R1 at 926005e (patryk/rakieta), `r1_run.py --rerank --device mps`, all gold sessions in the evidence pack
(~17k chars), 398 paired answerable questions (channel [LESSON] 23:54 UTC; runs/r1/20261030-2320-926005e-{dev,hard}
on branch runs/r1-candidates):

| type | dev | dev-hard v1 | drop (pts) |
|---|---|---|---|
| k-update | 1.000 | 1.000 | 0.0 |
| multi | 0.918 | 0.753 | 16.5 |
| ss-asst | 1.000 | 1.000 | 0.0 |
| ss-user | 1.000 | 1.000 | 0.0 |
| temporal | 0.892 | 0.804 | 8.8 |
| all | 0.952 | 0.889 | 6.3 |

Top 5 sessions: multi 0.897 -> 0.629, all 0.937 -> 0.852. Injected sessions reach the pack for 99% of questions
(3.1 per question). Independent rerun of make_dev_hard.py on the Mac gave the same splits/dev_hard_ids.txt.

Injection audit, partial (486 of 1682 injected sessions): 21 suspect (4.3%), several of which change the gold of
counting questions ("How many days a week do I attend fitness classes?" gold 4, injected session: 5) or state a
conflicting own fact ("designer handbag" $800 vs $5,000). dev-hard v2 will exclude them.
