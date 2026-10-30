# R7 GUARDIAN

Owner: Karol. Agent: karol-claude. Branch prefix: `r7/`.
Bet: verification first. Beat R1 on abstention and evidence F1 without false abstentions (dev and dev-hard).
Stages: retrieve = R1 chunking + BM25 only (CPU machine; `--cands` reads R1's own candidates), assemble = R1,
decide = R7 entity check. Default policy `pack`.
Numbers (dev minus holdout, 423 q, no reader): `pack` abstains on 6/25 unanswerable (0.24) with 2/398 false
abstentions (0.005); temporal 4/5. `pack-strict` 8/25 for 20/398 (0.050). R1 abstains 0/25 before its reader.
Status: milestone 1 done (entity check). Next: SQuAD 2.0 no-answer score for single-session-user and
knowledge-update, then citation pruning; re-measure on R1's real candidates and on POLIGON's dev-hard.

## Design

- `entities.py`: the question's specific entities (proper names, quoted titles, camel-case products, noun phrases
  after a determiner, other content-word runs), stemmed whole-word matching ("Korea" does not match "Korean").
- `rocket.py`: `STAGES`; `decide` checks each entity in the assembled evidence. Policies: `none` (R1), `pack`
  (abstain when an entity word is missing from the pack), `pack-strict` (also when a multi-word proper or quoted
  entity is not one phrase), `warn` (never abstain, tell the reader which entities the excerpts do not mention).
- `run.py`: a split -> `runs/r7/<run_id>/` (contract artifacts + `decisions.jsonl`). No reader is called.
- `measure.py`: abstention recall and false abstention per type for every policy from one run.

```sh
python rockets/r7/run.py ../data/dev --exclude splits/dev_holdout.txt
python rockets/r7/measure.py runs/r7/<run_id> ../data/dev/gold.jsonl --show
```

## Numbers

Run `runs/r7/20261030-2246-e958f46/`, dev minus `splits/dev_holdout.txt`, R1 evidence pack (BM25 candidates; all gold
sessions in the pack for 93.5% of answerable questions). Abstention before any reader; answer accuracy and
evidence F1 need the stand-in model (not chosen yet in `experiments/LEADERBOARD.md`).

| policy | type | n | unanswerable | abstention recall | false abstention |
|---|---|---|---|---|---|
| none (R1) | all | 423 | 25 | 0.000 | 0.000 |
| pack | knowledge-update | 63 | 5 | 0.000 | 0.000 |
| pack | multi-session | 107 | 10 | 0.200 | 0.000 |
| pack | single-session-assistant | 90 | 0 | - | 0.000 |
| pack | single-session-user | 56 | 5 | 0.000 | 0.020 |
| pack | temporal-reasoning | 107 | 5 | 0.800 | 0.010 |
| pack | all | 423 | 25 | 0.240 | 0.005 |
| pack-strict | all | 423 | 25 | 0.320 | 0.050 |

`warn` sends the `pack-strict` list to the reader instead of abstaining (warns on 0.32 of unanswerable and 0.05
of answerable questions).

What the entity check cannot catch: the swapped entity occurs elsewhere in the history ("Korea", "Shinjuku",
"Google", "Rachel", "Italian" are all in the pack, about something else). That is the SQuAD 2.0 signal's job
(AUC 0.95-0.99 on single-session-user and knowledge-update, `coord/findings/*squad2-verifier.md`).
