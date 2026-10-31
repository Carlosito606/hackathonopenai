# R1 on Reactor: old vs new answering notes and evidence (39 dev questions without holdout)

split: plan-cal40 = 39 dev questions (seed 1, stratified: 5 abstention, 8 temporal, 8 multi, 7 k-update,
6 ss-user, 6 ss-asst), none in splits/dev_holdout.txt. Reader: Reactor t10. Scorer: score.py.
old = fd7587f (plan built 30.10 ~21:15), new = 323eb44 (next user turn in evidence; GUIDE: plans/undone changes
and other people's facts are not my state; abstain if only said about someone else; neutral "<answer>" example;
dates.py from temporal/date-coverage).

| | correct | unjudged | abstention recall | false abstention | evidence F1 (final line) | evidence F1 (+reply fallback) |
|---|---|---|---|---|---|---|
| old | 0.692 | 0.282 | 3/4 | 0.000 | 0.867 | 0.895 |
| new | 0.692 | 0.282 | 3/4 | 0.000 | 0.795 | 0.910 |

Answers: identical up to wording in all 39 (7 changed strings, e.g. "Irish and Italian" -> "Mixed Irish and
Italian"); reading the unjudged ones by hand both versions are ~92-95% correct. The one wrong abstention case
(a premise never mentioned, answered with a university name) stays wrong in both.
Evidence F1 drop: Reactor left the [E#] labels off the final line in 4 of 35 answerable (1 in old), always with
the gold sessions in the pack. ask.py now takes the labels from the whole reply when the final line has none
(still Reactor's own citations): F1 0.910 new vs 0.895 old.
Decision: keep new.
