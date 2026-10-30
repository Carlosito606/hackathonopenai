# Leaderboard of main (integrator only)

Stand-in model for local end-to-end runs: <model name, e.g. Qwen2.5-7B-Instruct 4-bit> (one for the whole team).
Retrieval: `eval_retrieval.py` on dev minus `splits/dev_holdout.txt`. Reactor: `splits/reactor_mini.txt`.

| time | main sha | flags on | gold sessions in evidence (ms / tr / ku / ssu / ssa) | local acc | Reactor mini acc | abstain ok | evidence F1 |
|---|---|---|---|---|---|---|---|
