# Final R1 (tag final-run-code) on dev, dev-hard v2 and dev-hard-long

command: experiments/r1/export_chunks.py <split> out --cache ... --type all, for dev (minus holdout), dev-hard v2
and dev-hard-long (rockets/poligon/make_dev_hard.py --exclude rockets/poligon/exclude_v2.jsonl, long: --pad-to
200; ids identical to splits/dev_hard*_ids.txt, --check passes), then rockets/poligon/compare_dev_hard.py on
candidates.jsonl (top 5 sessions) and evidence.jsonl (the 18,000-char pack). 398 answerable questions, paired.
Artifacts: runs/r1/20261031-0200-fee061f-final-{dev,dev-hard-v2,dev-hard-long}/.

All gold sessions in the evidence pack:

| type | n | dev | dev-hard v2 | dev-hard-long (200 sessions per history, like test) |
|---|---|---|---|---|
| knowledge-update | 58 | 1.000 | 1.000 | 0.983 |
| multi-session | 97 | 0.969 | 0.907 | 0.825 |
| single-session-assistant | 90 | 1.000 | 1.000 | 1.000 |
| single-session-user | 51 | 1.000 | 1.000 | 1.000 |
| temporal-reasoning | 102 | 0.922 | 0.833 | 0.804 |
| all | 398 | 0.972 | 0.935 | 0.905 |

Before tonight's changes (926005e, dev-hard v1, experiments/r1/20261030-2320-dev-hard.md): dev 0.952, dev-hard
0.889, multi-session 0.753. On test-like data the final pack still misses a gold session for ~18% of
multi-session and ~20% of temporal questions: the main remaining risk of the submission.

Raw compare_dev_hard.py output:
```
== dev_hard_v2 candidates
all gold sessions in top 5 sessions, paired answerable questions; near-miss intrusion on dev-hard
type         n    dev   hard   drop  intrude  inj@k
k-update    58  1.000  0.983    1.7    0.987   2.92
multi       97  0.897  0.649   24.7    0.984   2.68
ss-asst     90  1.000  1.000    0.0    0.991   3.04
ss-user     51  1.000  1.000    0.0    0.970   3.06
temporal   102  0.843  0.765    7.8    0.967   2.50
all        398  0.935  0.852    8.3    0.980   2.80
== dev_hard_v2 evidence
all gold sessions in the evidence pack, paired answerable questions; near-miss intrusion on dev-hard
type         n    dev   hard   drop  intrude  inj@k
k-update    58  1.000  1.000    0.0    0.987   3.36
multi       97  0.969  0.907    6.2    1.000   3.65
ss-asst     90  1.000  1.000    0.0    1.000   3.26
ss-user     51  1.000  1.000    0.0    0.970   3.18
temporal   102  0.922  0.833    8.8    0.992   3.40
all        398  0.972  0.935    3.8    0.992   3.40
== dev_hard_long candidates
all gold sessions in top 5 sessions, paired answerable questions; near-miss intrusion on dev-hard
type         n    dev   hard   drop  intrude  inj@k
k-update    58  1.000  0.966    3.4    0.960   2.47
multi       97  0.897  0.557   34.0    0.961   2.34
ss-asst     90  1.000  1.000    0.0    0.964   2.57
ss-user     51  1.000  1.000    0.0    0.955   2.75
temporal   102  0.843  0.706   13.7    0.935   2.15
all        398  0.935  0.812   12.3    0.954   2.42
== dev_hard_long evidence
all gold sessions in the evidence pack, paired answerable questions; near-miss intrusion on dev-hard
type         n    dev   hard   drop  intrude  inj@k
k-update    58  1.000  0.983    1.7    0.987   3.25
multi       97  0.969  0.825   14.4    0.992   3.43
ss-asst     90  1.000  1.000    0.0    1.000   3.05
ss-user     51  1.000  1.000    0.0    0.970   3.03
temporal   102  0.922  0.804   11.8    0.967   3.12
all        398  0.972  0.905    6.8    0.984   3.19
```
