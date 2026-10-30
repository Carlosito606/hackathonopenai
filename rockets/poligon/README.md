# POLIGON: the test range (karol-claude-2)

**Status (2026-10-30):** dev-hard v1 ready. 505 questions = 423 dev-minus-holdout questions with 3-5 injected
near-miss sessions each (inject) + 82 unanswerable variants with the evidence removed (remove). Ids:
`splits/dev_hard_ids.txt`. Data is local only; regenerate it (30 s, standard library, deterministic):

    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --ids splits/dev_hard_ids.txt
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --check     # must print "all invariants hold"

dev_hard/ has the dev format (questions, histories, gold) plus manifest.jsonl (source question, variant, injected
sessions). Never feed manifest.jsonl to a pipeline. Score with the challenge's score.py on dev_hard/gold.jsonl.

**The number to shrink: dev to dev-hard drop, per type.** Plain BM25 (all turns), all gold sessions in the top 5
sessions, same 398 answerable questions: k-update 0.966 -> 0.845 (-12.1), multi 0.670 -> 0.423 (-24.7),
ss-asst 1.000 -> 0.989 (-1.1), ss-user 1.000 -> 1.000 (0), temporal 0.725 -> 0.529 (-19.6), all 0.844 -> 0.714
(-13.1). An injected session reaches the top 5 in 98% of questions. R1 numbers: see LOG.md.

Compare your rocket: run it on ../data/dev and ../data/dev_hard, then
`python rockets/poligon/compare_dev_hard.py ../data/dev ../data/dev_hard DEV/candidates.jsonl HARD/candidates.jsonl`.

Judge, injection check and failure analysis: written and tested on a mock server (`judge.py`, `check_injections.py`,
`failures.py`); not yet run on the stand-in model (see LOG.md).

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

**Known limits.** Injected sessions come from other users' histories, so a few may still state a conflicting
first-person fact below the 60% filter (e.g. another 5K race time before a knowledge-update question). The LLM
check above is meant to remove those. dev-hard is harsher than test is likely to be (injections reach the top 5
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
| `LOG.md` | what was tried, numbers |
