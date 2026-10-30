# R7 GUARDIAN

Owner: Karol. Agent: karol-claude. Branch prefix: `r7/`.
Bet: verification first. Beat R1 on abstention and evidence F1 without false abstentions (dev and dev-hard).
Stages: retrieve = R1 chunking + BM25 only (CPU machine; `--cands` reads R1's own candidates), assemble = R1,
decide = R7 entity check + SQuAD 2.0 no-answer score (`--qa`). Best: policy `pack` with `--qa`.
Numbers (dev minus holdout, 423 q, no reader): `pack --qa` abstains on 12/25 unanswerable (0.48) with 3/398 false
abstentions (0.008); `pack` alone 6/25 for 2/398. R1 abstains 0/25 before its reader. The QA threshold (-5) was
picked on these 25 questions: check it on dev-hard before trusting it.
Status: milestones 1-2 done (entity gate, QA gate). Next: dev-hard, R1's real candidates (GPU desktop), citation
pruning once the stand-in model runs.

## Design

- `entities.py`: the question's specific entities (proper names, quoted titles, camel-case products, noun phrases
  after a determiner, other content-word runs), stemmed whole-word matching ("Korea" does not match "Korean").
- `rocket.py`: `STAGES`; `decide` checks each entity in the assembled evidence. Policies: `none` (R1), `pack`
  (abstain when an entity word is missing from the pack), `pack-strict` (also when a multi-word proper or quoted
  entity is not one phrase), `warn` (never abstain, tell the reader which entities the excerpts do not mention).
- `qa.py`: SQuAD 2.0 (`deepset/roberta-base-squad2`) best span minus no-answer over the top 8 candidate chunks
  (forked from `experiments/analysis/karol-claude/verify.py`). Used only on single-fact question shapes: not
  computed answers (dates, counts, sums, orderings, comparisons) and not questions about the assistant.
- `run.py`: a split -> `runs/r7/<run_id>/` (contract artifacts + `decisions.jsonl`). No reader is called.
- `measure.py`: abstention recall and false abstention per type for every policy from one run; with `--qa` runs
  also the QA signal's AUC per type and a threshold sweep.

```sh
python rockets/r7/run.py ../data/dev --exclude splits/dev_holdout.txt --qa      # ~10 min on CPU
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
"Google", "Rachel", "Italian" are all in the pack, about something else). That is the SQuAD 2.0 signal's job.

### With the QA signal (`--qa`)

Run `runs/r7/20261030-2314-73a19d0/`, same split and candidates. QA AUC (answerable above unanswerable), all
questions / the single-fact shapes it is used on: k-update 0.966 / 0.906 (35 of 63 used), multi 0.851 / 0.816
(21), ss-user 1.000 / 1.000 (47), temporal 0.739 / 0.944 (19); ss-assistant skipped.

| policy | type | n | unanswerable | abstention recall | false abstention |
|---|---|---|---|---|---|
| pack + qa < -5 | knowledge-update | 63 | 5 | 0.000 | 0.000 |
| pack + qa < -5 | multi-session | 107 | 10 | 0.300 | 0.000 |
| pack + qa < -5 | single-session-assistant | 90 | 0 | - | 0.000 |
| pack + qa < -5 | single-session-user | 56 | 5 | 0.800 | 0.020 |
| pack + qa < -5 | temporal-reasoning | 107 | 5 | 1.000 | 0.020 |
| pack + qa < -5 | all | 423 | 25 | 0.480 | 0.008 |

Thresholds -4/-3 give 13/25 for 4/398; -1 gives 15/25 for 18/398. Knowledge-update stays at 0/5: its swapped
entities ("Shinjuku", "Dr. Johnson", "table tennis") sit in real, similar sessions, and the reader must catch them.
