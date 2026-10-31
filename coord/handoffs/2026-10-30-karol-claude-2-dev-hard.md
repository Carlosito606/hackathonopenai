# Handoff: POLIGON dev-hard v1 (karol-claude-2, 2026-10-30 23:20 local)

**Done (main b4ff5f8, PR #6):** `rockets/poligon/make_dev_hard.py` builds `../data/dev_hard` (505 questions: 423
inject + 82 remove), `splits/dev_hard_ids.txt`, `--check` invariants, BM25 and R1 runners, paired comparison
`compare_dev_hard.py`. BM25 drop dev -> dev-hard, all gold in top 5: all -13.1 pts, multi -24.7, temporal -19.6,
k-update -12.1 (README, LOG.md, coord/findings/20261030-2310-...). [PART-READY] posted on the channel.

**Open:**
1. R1 dev -> dev-hard drop. This machine is CPU-only: bge-base embeds 12 chunks/s, dev has 351,678 chunks (~8-10 h).
   [ASK] on the channel to patryk-opencode for R1's dev embedding cache (.pkl). With it:
   `python rockets/poligon/r1_run.py ../data/dev OUT_DEV --cache X.pkl --device cpu --skip-holdout`, the same on
   `../data/dev_hard`, then `compare_dev_hard.py` on both candidates.jsonl and both evidence.jsonl.
   Note: patryk-opencode reports an Embedder.ensure fix on patryk/rakieta fd7587f (not on main yet).
2. LLM check of every injected session (does it answer or contradict the question?) -> `--exclude` file -> v2.
3. Local LLM judge for score.py's "unjudged" (stand-in: Qwen2.5-7B-Instruct 4-bit; not installed here).
4. Failure analysis of every rocket's runs, posted as findings.

**Local setup on Karol's machine (not in the repo):** data in `C:\Users\karol\data` (dev extracted, dev_hard
generated, BM25 runs in `data/poligon_runs/`). The `score.py` in `data/` is a corrupted copy (line-wrapped,
does not compile); the original is in `C:\Users\karol\vendor\memory-challenge\score.py`. Python deps for R1 in
`C:\Users\karol\venv-poligon` (torch 2.6.0+cpu: newer torch fails to load shm.dll on this Windows).

**Warning posted:** `eval_retrieval.py` on main calls `build_evidence` with the wrong signature (R1's area).
