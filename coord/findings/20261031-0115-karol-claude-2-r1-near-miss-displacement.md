agent: karol-claude-2 (POLIGON)
fact: On dev-hard v1, R1 (926005e, rerank) loses gold from its 18k pack for 29 answerable questions that were
complete on dev: 21 because injected near-miss sessions took the budget (removing them from the same ranked
candidates brings the gold back), 7 because gold fell out of the 80 candidates, 1 other. All 29 are multi-session
(20) or temporal (9); k-update and single-session lose nothing. A pack holds 3.0 injected sessions on average
(0 injected in only 6 of 398 packs).
evidence: rockets/poligon/pack_budget.py rebuild of runs/r1/20261030-2320-926005e-{dev,hard} packs, dev-hard
manifest.jsonl; same rebuild for dev and dev-hard.
so: near-misses hurt R1 by crowding, not by outranking gold everywhere: a bigger budget for counting/temporal
questions (see 20261031-0110) or demoting sessions that only share a swapped entity would recover most of it.
Reading is the other half: with 3 near-misses in every pack, the reader must reject them (R7's job).
