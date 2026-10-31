#!/bin/sh
# One variant end to end on the fixed sample with the local stand-in (run from the worktree on the Mac):
#   sh experiments/verify/run_variant.sh quote+v
set -e
V=$1
PY=../.venv/bin/python
mkdir -p out
~/vibathon/gpujob $PY experiments/verify/harness.py plan ../data/dev cands.pkl out/plan-$V.jsonl --variant $V
# ask.py derives the ref from hash(): a fixed seed keeps the prompts identical across variants
PYTHONHASHSEED=0 $PY ask.py out/plan-$V.jsonl out/results-$V.jsonl --local http://127.0.0.1:8899 2> out/ask-$V.log
$PY reactor/predictions.py out/results-$V.jsonl --out out/pred-$V.jsonl --abstain-on agent,no-answer
$PY experiments/verify/harness.py judge ../data/dev out/pred-$V.jsonl out/details-$V.jsonl --score ../repo/score.py
