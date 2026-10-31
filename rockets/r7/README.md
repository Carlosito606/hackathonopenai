# R7 GUARDIAN

Owner: Karol. Agent: karol-claude. Branch prefix: `r7/`.
Bet: verification first. Beat R1 on abstention and evidence F1 without false abstentions (dev and dev-hard).
Stages: retrieve = R1 chunking + BM25 only (CPU machine; `--cands` reads R1's own candidates), assemble = R1,
decide = R7 entity gate + SQuAD 2.0 no-answer gate (`--qa`). Best: policy `pack` with `--qa`, threshold -5.
Numbers (no reader): dev minus holdout 13/25 abstentions right (0.52), 2/398 false (0.005); dev-hard v1 26/107
right (0.24), 2/398 false. R1 abstains 0 before its reader. Threshold picked on dev, held on dev-hard.
Lesson: injected near-miss sessions defeat both gates (they carry the missing names and give SQuAD confident
spans); computed questions (counts, dates) are left to the reader.
Status: milestones 1-3 done (entity gate, QA gate, error analysis). Next: the stand-in reader on `reactor_mini`
(`plan.py`), R1's real candidates when committed, citation pruning.

## Design

- `entities.py`: the question's specific entities (proper names, quoted titles, camel-case products, noun phrases
  after a determiner, other content-word runs), stemmed whole-word matching ("Korea" does not match "Korean"). A
  name never runs across punctuation; months, weekdays, holidays and degree words are not names.
- `rocket.py`: `STAGES`; `decide` checks each entity in the assembled evidence. Policies: `none` (R1), `pack`
  (abstain when a name or quoted title has a word missing from the pack), `pack-strict` (also when such a name is
  not one phrase, or a noun phrase's head noun is missing), `warn` (never abstain, tell the reader which entities
  the excerpts do not mention).
- `qa.py`: SQuAD 2.0 (`deepset/roberta-base-squad2`) best span minus no-answer over the top 8 candidate chunks
  (forked from `experiments/analysis/karol-claude/verify.py`, without its session-date prefix). Used only on
  single-fact question shapes: not computed answers (dates, counts, sums, orderings, comparisons, positions in a
  list) and not questions about the assistant.
- `run.py`: a split -> `runs/r7/<run_id>/` (contract artifacts + `decisions.jsonl`). No reader is called.
- `measure.py`: abstention recall and false abstention per type for every policy from one run; for `--qa` runs
  also the QA signal's AUC per type and a threshold sweep.
- `plan.py`: R1's prompt on R7's evidence as an `ask.py` plan, and R7's abstentions laid over the reader's
  predictions, so one reader pass gives both R1's and R7's behaviour.

```sh
python rockets/r7/run.py ../data/dev --exclude splits/dev_holdout.txt --qa      # ~10 min on CPU
python rockets/r7/run.py ../data/dev_hard --qa                                  # POLIGON's dev-hard v1
python rockets/r7/measure.py runs/r7/<run_id> ../data/dev/gold.jsonl --show
```

## Numbers

Runs `runs/r7/20261031-0021-aac6aeb/` (dev minus `splits/dev_holdout.txt`, 423 q, 25 unanswerable) and `runs/r7/20261031-0055-aac6aeb/`
(dev-hard v1, 505 q, 107 unanswerable). R1 evidence pack on BM25 candidates: all gold sessions in the pack for
93.5% of answerable dev questions, 83.9% on dev-hard. Abstention before any reader; answer accuracy and evidence
F1 need the stand-in reader.

Abstentions right / false, policy `pack` + QA below -5:

| type | dev | dev-hard v1 |
|---|---|---|
| knowledge-update | 0/5, 0/58 | 5/17, 0/58 |
| multi-session | 3/10, 1/97 | 3/32, 1/97 |
| single-session-assistant | -, 0/90 | 9/21, 0/90 |
| single-session-user | 5/5, 0/51 | 4/16, 0/51 |
| temporal-reasoning | 5/5, 1/102 | 5/21, 1/102 |
| all | 13/25, 2/398 | 26/107, 2/398 |
| all, `pack` alone | 6/25, 0/398 | 16/107, 0/398 |

QA AUC (answerable above unanswerable), all questions / the shapes it is used on, dev then dev-hard:
k-update 0.962 / 0.896, 0.946 / 0.911; multi 0.828 / 0.737, 0.684 / 0.750; ss-user 1.000 / 1.000, 0.923 / 0.907;
temporal 0.714 / 0.944, 0.633 / 0.653; ss-assistant (skipped) -, 0.869. Thresholds on dev-hard: -4 gives 29/107
for 4/398, -3 32/107 for 9/398.

What the gates cannot catch (details in LOG.md):
- A swapped entity that occurs elsewhere in the history ("Korea", "Shinjuku", "Google"): the entity gate passes.
- Evidence removed but a similar session from someone else present: SQuAD answers from it with confidence.
- Counts, sums, durations and orderings: no span to score; the reader (or R4 TIMELINE) must abstain.
