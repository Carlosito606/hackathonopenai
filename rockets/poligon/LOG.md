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

## 2026-10-31 01:00 karol-claude-2: pack studies on R1's candidates (kept), dev-hard v2 audit

- `pack_budget.py` (R1's build_evidence on R1's own candidates, 926005e): dev-hard multi 0.722 / 0.814 / 0.845 at
  18k / 22k / 26k; whole message max 27,234 chars at 26k. Rebuild matches the run's pack exactly for 60-75% of
  questions (which chunk of a long turn was ranked is not in candidates.jsonl), levels within 1-3 points.
- Crowding: of R1's 29 dev-hard losses (gold complete on dev), 21 come back when the injected sessions are removed
  from the same ranking, 7 fell out of the 80 candidates, 1 other. Packs hold 3.0 injected sessions on average.
- `pack_policies.py`: "sessdiv" (best chunk of every candidate session first) at 26k: dev-hard multi 0.959,
  temporal 0.902, all 0.965 (R1 18k: 0.722 / 0.814 / 0.884); dev all 0.955 -> 0.992; 13.5 sessions per pack.
  At 18k sessdiv loses ss-assistant answers (dev 49 -> 36 of 57). Rule-based query-driven pruning: dev-hard all
  0.927 at 18k, weaker. Sent to R1 before its freeze; R1's final code already diversifies sessions for counting
  questions (experiments/r1/20261031-0030-budget.md: multi 0.914 at 18k) and kept 18k.
- Audit round 1 (`check_injections.py`, 1,682 injected sessions, 83 min with the CPU shared with R7): 93 suspect
  (5.5%), 63 source questions. v2 excludes them (`exclude_v2.jsonl`, ids only) with new question/history ids
  (`--version 2`); round 2 on the replacements: 148 new sessions, 20 suspect; the loop repeats until a round adds
  nothing. BM25 dev -> dev-hard v2: same numbers as v1 (all 0.844 -> 0.714).
- `--pad-to 200` (dev-hard-long): filler sessions up to test's 200 per history, original session ids; trial
  build passes `--check` (1.1 GB of histories, 7.5 min build).

## 2026-10-31 01:25 karol-claude-2: v2 audit rounds, test-like traps

- Audit loop on v2 replacements: rounds found 93, 20, 8, 4, 4, 3, 2, 1 new suspect pairs (135 in all). From round 4
  on nearly every replacement was itself flagged: a few questions sit in a dense topical neighbourhood. Claude Code
  stopped the loop in round 8 (machine memory under 2 GB: two llama-servers, 13 GB + 6 GB private). Not converged.
- R1's GPT audit of test evidence (experiments/r1/20261030-2300-*) says test traps are mostly facts about other
  people and plans/undone changes inside the user's own history; dev-hard's injected sessions are other users'
  first-person chats. So `make_traps.py`: the stand-in rewrites the gold sentence into an aside about another
  person (43) or a plan (40) with another value; 83 traps from 93 rewrites (rejected: 3 without the person word,
  7 without a plan word); 215 questions have no checkable phrase answer or no single answer sentence. 14 read by
  hand: none changes the gold; most are real near-misses ("my roommate's Fitbit Versa 2 for 6 months" vs "my
  Fitbit Charge 3, 9 months"), a few are off-topic and harmless.
- `reader_probe.py`: first run died on HTTP 500 (a prompt over the 4096-token slot); now each message is fitted
  with the server's /tokenize and judge.py records server errors per row instead of crashing.

## 2026-10-31 01:35 karol-claude-2: dev-hard-long (test-length histories) with BM25

v2 + `--pad-to 200` (exclude_v2, 135 pairs): build 7 min, 1.1 GB. Plain BM25, all gold in top 5 sessions, 398
paired questions, dev / v2 / long: multi 0.670 / 0.423 / 0.392, temporal 0.725 / 0.529 / 0.471, k-update 0.966 /
0.845 / 0.828, ss-user 1.000 / 1.000 / 0.961, ss-asst 1.000 / 0.989 / 0.978, all 0.844 / 0.714 / 0.681 (top 10:
0.907 / 0.852 / 0.809). The computed splits/dev_hard_long_ids.txt equals the build's (same sha1). `--check` on the
long build not run (about 5 GB of memory; the same code passed it on the trial build without --exclude).
- R1 final code (fee061f) on dev temporal, the 2 misses whose gold never reaches the candidates: "What did I do
  with Rachel on the Wednesday two months ago?" is benign (the ukulele session with the answer is in the pack; the
  missing gold session is a related keyboard chat); "How many months before my anniversary did Rachel get
  engaged?" is real (the engagement is an aside inside a bachelorette-trip chat). "All gold sessions in the pack"
  slightly overstates misses: gold also lists sessions the answer does not need.

## 2026-10-31 01:45 karol-claude-2: crowding.py

`crowding.py` turns the earlier one-off displacement count into a tool (exact with chunk-indexed candidates; counts
padded sessions too). On R1 926005e dev vs dev-hard v1 it gives ok 348, crowded 23, retrieval 7, other 1, missed on
dev too 19 (the one-off count in finding 20261031-0115 said 21 crowded of 29 losses: it classified hard-ok before
dev-missed, so 4 questions moved). Same conclusion: crowding is most of the loss.

## 2026-10-31 02:00 karol-claude-2: Reactor calibration answers: failure analysis and citations

failures.py on runs/r1/20261031-0125-reactor-cal39 with the human verdicts on unjudged: old ok 27, citation_miss 10,
answered_unanswerable 1, wrong_date 1; new ok 25, citation_miss 12, answered_unanswerable 1, wrong_date 1. All
citation misses leave a gold session out (none extra). `cite_expand.py` (ratio 0.8, cite the best pack session when
none): F1 0.867 -> 0.951 (old), 0.795 -> 0.917 (new) over final-line citations; vs ask.py's reply fallback 0.895 /
0.910 alone; combination unmeasured. Finding 20261031-0300.

## 2026-10-31 02:10 karol-claude-2: reader probe on test-like traps

Stand-in shares one 4,096-token KV cache across its 4 slots (finding 20261031-0245): the probe stalled at 4
parallel 1.7k-token prompts; rerun with --workers 2 --ctx 2048 --budget 4500 --max-tokens 250 (192 calls, ~35 min).
83 inject + 13 remove questions, plain / trap: gold 27 / 31, abstained 31 / 27, other 24 / 22, trap taken 1 / 3
(by hand: 1 real, the rest false alarms of the word-subset rule); remove: abstained 12 / 12 of 13. Aside in the
pack 52 / 83. Finding 20261031-0310.
- judge.py --human on cal39: agreement with patryk-opencode's verdicts 10/11 (old) and 11/11 (new); judged
  correct 0.923 / 0.949 vs human 0.949 / 0.949; the one miss is the flagged yes/no "Road bike" answer. Finding
  20261031-0315.

## 2026-10-31 02:20 karol-claude-2: R1 final code on dev-hard v2 and dev-hard-long

patryk-opencode exported R1 fee061f (the submitted code) on dev, v2 and long with chunk indices. All gold in pack
dev / v2 / long: all 0.972 / 0.935 / 0.905; multi 0.969 / 0.907 / 0.825; temporal 0.922 / 0.833 / 0.804. Crowding on
v2: 7 crowded, 7 retrieval, 1 other. sessdiv + prune at 18k: gold 0.992 / 0.965 / 0.937; answer phrase dev 0.714
(vs 0.692), v2 0.671 (0.654), long 147/234 (151): not a clear win at test length. Local dev_hard rebuilt with all
135 exclusions to match. Finding 20261031-0325.
