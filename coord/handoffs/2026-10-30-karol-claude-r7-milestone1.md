agent: karol-claude (R7 GUARDIAN, Karol's machine)

done:
- rockets/r7/: entity extraction (entities.py), STAGES with a decide stage and four policies (rocket.py),
  run.py (contract artifacts + decisions.jsonl), measure.py (abstention per type per policy).
- Milestone run runs/r7/20261030-2246-e958f46/ on dev minus holdout: policy `pack` abstention recall 0.24
  (temporal 0.80), false abstention 0.005; `pack-strict` 0.32 / 0.050. Numbers in rockets/r7/README.md.
- Finding coord/findings/20261030-2300-karol-claude-entity-gate.md.

not done (decisions for humans):
- Team stand-in model is still a placeholder in experiments/LEADERBOARD.md: no answer accuracy or evidence F1 yet.
- R1 baseline here is BM25-only: this laptop has no CUDA and torch 2.15 fails to load (WinError 126, shm.dll;
  the analysis README suggests torch==2.6.0). Full R1 on CPU would take many hours for 229M chars.

learned:
- Checking every content word abstains on 28% of answerable questions; only names and quoted titles are safe.
- Most swapped entities of unanswerable questions occur elsewhere in the history, so presence checks miss them.

next:
1. Load torch (pin 2.6.0 in rockets/r7/requirements.txt) and add the SQuAD 2.0 no-answer score for
   single-session-user and knowledge-update questions (question type must be guessed: test has no labels).
2. Re-run on R1's real candidates (`run.py --cands`) once a Mac run is committed, and on POLIGON's dev-hard.
3. Citation pruning for evidence F1, once the stand-in model is chosen.
