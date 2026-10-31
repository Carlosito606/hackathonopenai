# R3 FACT-LEDGER

Owner: Patryk 2 (patryk2-claude). Bet: knowledge-update and single-session-user, where the answer is one value
the user stated (and maybe corrected) somewhere in the history.
Idea: a local LLM extracts atomic facts per session `{subject, attribute, value, said_by, turn, is_correction,
when}`; facts are extra retrieval keys pointing to their source turns (LongMemEval fact-augmented keys), and code
decides "latest user statement wins" and states it to the reader in `Pack.facts`.
Status: DEADEND on dev (2026-10-31). Milestone cut to 15 k-update questions (CPU-only laptop, `ku15_questions.txt`).
Numbers (Reactor t10, same R1@926005e candidates): R1 15/15, evidence F1 0.718; R3 (R1 pack + ledger) 13/15, F1 0.641,
1 false abstention. R1 already has every gold session for k-update/ss-user (1.000), so the ledger only adds noise;
its "latest wins" note hurt a "previous value" question. Do NOT adopt the ledger into the ship.
Stages: retrieve = R1 turns + fact keys (RRF), enrich = dates per history + superseded_by, assemble = R1 evidence
with fact source turns forced in + ledger, decide = question + ledger + R1 answering notes. All in `rocket.py`.
Parts others may want: `ab.py` (A/B on Reactor, each arm in its own history), `extract.py` pipe-format extraction
(73 s/session, Qwen2.5-3B on CPU). Lessons: coord/findings/20261031-0105-patryk2-claude-fact-ledger-extraction.md.

## Run

```sh
python rockets/r3/r1_cands.py ../data/dev rockets/r3/m1_questions.txt cache/r3/r1_cands.jsonl --device cpu
python rockets/r3/extract.py ../data/dev cache/r3/r1_cands.jsonl --top 15 --model ~/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
python rockets/r3/run.py ../data/dev rockets/r3/m1_questions.txt --r1-cands cache/r3/r1_cands.jsonl --variant r3
python rockets/r3/run.py ../data/dev rockets/r3/m1_questions.txt --r1-cands cache/r3/r1_cands.jsonl --variant r1
# then per run dir: ask.py --local, reactor/predictions.py, score.py (see run.py docstring)
python core/permlab.py retrieval --gold ../data/dev/gold.jsonl r1=runs/r1/<id>/candidates.jsonl r3=runs/r3/<id>/candidates.jsonl
```

## Design notes

- Fact cache is keyed by session id and holds only what the text says; dates come from the question's own history
  at use time (`enrich`), since 3517 session ids carry different dates in different histories.
- `when` ("last Saturday") is resolved with R1's `annotate_dates` against the session date.
- Ledger groups facts whose subject+attribute tokens overlap (Jaccard >= 0.5); the latest USER statement wins,
  assistant numbers are listed but marked "by the assistant" (finding: in-session-corrections).
- Machine: CPU only (8 cores, 14 GB), so extraction uses Qwen2.5-1.5B-Instruct Q4_K_M via llama-cpp-python
  (`requirements.txt` here).
