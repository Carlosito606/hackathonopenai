# POLIGON: the test range (karol-claude-2)

**Status (2026-10-31):** dev-hard **v2** is current. It has the same 505 questions as v1 (423 inject + 82 remove)
but new question/history ids, and it excludes the injected sessions a local LLM audit found answering or
contradicting their question (`exclude_v2.jsonl`, ids only). Ids: `splits/dev_hard_ids.txt`. Data is local only;
regenerate it (about 1 min, standard library, deterministic):

    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --exclude rockets/poligon/exclude_v2.jsonl --ids splits/dev_hard_ids.txt
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --exclude rockets/poligon/exclude_v2.jsonl --check

v1 (b4ff5f8; R1's and R7's first dev-hard numbers) is `--version 1` without `--exclude`. **dev-hard-long** adds
`--pad-to 200`: random filler sessions from other histories up to test's 200 sessions per history (filler keeps
its original session ids, so embedding caches keyed by session id still hit); ids `splits/dev_hard_long_ids.txt`.

dev_hard/ has the dev format (questions, histories, gold) plus manifest.jsonl (source question, variant, injected
sessions). Never feed manifest.jsonl to a pipeline. Score with the challenge's score.py on dev_hard/gold.jsonl.

**The number to shrink: dev to dev-hard drop, per type.** Plain BM25 (all turns), all gold sessions in the top 5
sessions, same 398 answerable questions (v1 and v2 give the same numbers): k-update 0.966 -> 0.845 (-12.1),
multi 0.670 -> 0.423 (-24.7), ss-asst 1.000 -> 0.989 (-1.1), ss-user 1.000 -> 1.000 (0), temporal 0.725 -> 0.529
(-19.6), all 0.844 -> 0.714 (-13.1). R1 (926005e, rerank, measured by patryk-opencode on v1), all gold in the
pack: multi 0.918 -> 0.753, temporal 0.892 -> 0.804, all 0.952 -> 0.889; near-misses reach 99% of packs.
Fix found here: "sessdiv" pack order at a 26k budget brings dev-hard multi to 0.959 and temporal to 0.902
(`pack_policies.py`, coord/findings/20261031-0125-*).

Compare your rocket: run it on ../data/dev and ../data/dev_hard, then
`python rockets/poligon/compare_dev_hard.py ../data/dev ../data/dev_hard DEV/candidates.jsonl HARD/candidates.jsonl`
(or the two evidence.jsonl files for "all gold in the pack").

Local judge (`judge.py`, 0.951 on its selftest with Qwen2.5-7B Q4_K_M) for score.py's "unjudged"; failure
analysis (`failures.py`); pack studies on any rocket's candidates (`pack_budget.py`, `pack_policies.py`).

## How dev-hard is built

- **inject**: the question's own history plus 3-5 sessions from other dev histories, chosen by BM25 over user turns
  (assistant turns for single-session-assistant) with the question's words (weight 2) plus the 15 most distinctive
  words of its evidence sessions, sampled from the 10 best that pass all filters. Injected sessions get fresh
  session and turn ids (hashes) and a random date inside the history's span; for knowledge-update they are dated
  before the first evidence session, so "the latest value wins" still gives the gold. Gold is unchanged.
- **remove**: for a seeded quarter of the answerable questions of each type, the injected history without the
  evidence sessions. Gold: abstain, evidence empty, same question type (so score.py reports abstention per type).
  Kept only if the gold answer no longer occurs anywhere in the history (17 dropped).
- Dev's own 24 unanswerable non-holdout questions are in the inject set with their gold unchanged.
- Holdout questions are excluded, and holdout and dev evidence sessions never serve as distractors.

Filters on a candidate session (counts of rejections in the v1 build):
1. not in the history already, not a near-copy (same first 40 content words) of a session there (424);
2. no dev question's evidence session: LongMemEval reuses one event in edited evidence sessions of sibling
   questions ("I recently ran a 5K charity run"), which restate or contradict the gold instead of nearly missing it;
3. does not contain the gold answer: whole normalized phrase as score.py matches it, or 70% of the distinctive
   words of a long answer; bare numbers cannot be checked (650);
4. no first-person user sentence with 60% or more of the question's content words, i.e. no "my running shoes are
   Adidas" for "What brand are my favorite running shoes?" (622).

Checked by `--check`: holdout excluded, coverage of every non-holdout question, unique ids, sorted dates, injected
dates inside the span and before the question date, knowledge-update injections before the first evidence,
no injected session from dev evidence, containing the answer, stating an own fact or near-duplicating another,
inject gold equal to dev gold, remove variants without any evidence session or answer. Two builds with the same
seed are byte-identical (sha1 of all four files). About 40 injected sessions were read by hand.

5. (v2) not in `exclude_v2.jsonl`: `check_injections.py` asks the stand-in model to answer the question from a
   short excerpt of each injected session, or say NONE; any answer excludes the pair, and the build and audit
   repeat until a round adds nothing. The audit's calibration: it answers from a real evidence session 92/107
   times and says NONE on a random session 107/107 times. Round 1 flagged 93 of 1,682 injected sessions (5.5%,
   63 questions), e.g. "How many days a week do I attend fitness classes?" (gold 4) with another user saying 5.

**Known limits.** The audit reads an excerpt, not the whole session, and a 7B model misses some: a few
conflicting sessions may remain. The remove variants assume nothing else in the history answers the question
(checked by phrase, not by meaning). dev-hard is harsher than test is likely to be (near-misses reach the top 5
almost always); use it to rank rockets on robustness, not to predict the test score.

## Files

| File | What |
|---|---|
| `make_dev_hard.py` | generator and `--check` |
| `bm25_run.py` | plain BM25 baseline -> candidates.jsonl (fork of experiments/analysis/karol-claude/mkruns.py) |
| `compare_dev_hard.py` | dev vs dev-hard retrieval per type, paired, plus near-miss intrusion |
| `judge.py` | local LLM judge for score.py's "unjudged" (LongMemEval prompts, any OpenAI-compatible server), `--selftest` |
| `check_injections.py` | LLM check of injected sessions -> exclude list for `make_dev_hard.py --exclude` |
| `failures.py` | one outcome per question (retrieval miss, near-miss cited, stale value, wrong date, ...) per type |
| `exclude_v2.jsonl` | (source question, source session) pairs never injected in v2 (LLM audit) |
| `pack_budget.py` | R1's evidence budget vs all-gold-in-pack and whole-message size, from candidates.jsonl |
| `pack_policies.py` | pack orders against near-miss crowding (sessdiv, query-driven pruning), from candidates.jsonl |
| `r1_run.py` | R1 retrieval (root memsys.py) on a whole split -> candidates.jsonl, evidence.jsonl |
| `PITCH.md` | slide-ready summary for the final presentation |
| `LOG.md` | what was tried, numbers |
