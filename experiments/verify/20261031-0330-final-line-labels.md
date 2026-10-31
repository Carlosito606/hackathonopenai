# VERIFIER: GUIDE demands the [E#] labels on the final line

Why: Reactor writes labels in its reasoning but may omit them on the final line; only that line counts.
Change: GUIDE bullet "... followed by the labels of the excerpts you quoted ... Labels count only on that line, so
always repeat them there." Same sample, harness and seed as 20261031-0214-abstention.md;
`sh experiments/verify/run_variant.sh final2+v` (plan step now through ~/vibathon/gpujob).

| variant | acc | match | judged | false_abst | abs_recall | evidence_f1 | answered without labels |
|---|---|---|---|---|---|---|---|
| base_s (main GUIDE, 18k) | 0.320 | 0.267 | 0.053 | 0.520 | 0.76 | 0.317 | – |
| final+v | 0.427 | 0.253 | 0.173 | 0.200 | 0.52 | 0.567 | 3 / 72 |
| final2+v | 0.440 | 0.293 | 0.147 | 0.240 | 0.52 | 0.607 | 0 / 69 |

Per type, final2+v (acc / false_abst / abs_recall / evidence_f1): knowledge-update 0.733/0.067/0.00/0.700,
multi-session 0.133/0.133/0.80/0.615, single-session-assistant 0.667/0.200/–/0.711, single-session-user
0.600/0.333/0.60/0.578, temporal-reasoning 0.067/0.467/0.40/0.433. Per-type moves vs final+v are within the
±0.1 noise of 15–25 questions; labels on the final line: 3 missing -> 0.
