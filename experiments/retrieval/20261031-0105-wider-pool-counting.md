# Wider reranker pool for counting / two-event questions (n_fuse 80 -> 120 when MULTI fires)

Base: origin/patryk/rakieta fee061f. Same command, sample and machine as 20261031-0045-sentence-bm25.md
(dev minus holdout, 150 already-embedded questions, seed 0, through ~/vibathon/gpujob).

| type | n | sent_all base | sent_all pool 120 | sent_recall base | new | n_sent base | new |
|---|---|---|---|---|---|---|---|
| all | 150 | 0.967 | 0.973 | 0.989 | 0.991 | 7.8 | 8.0 |
| multi-session | 33 | 0.939 | 0.939 | 0.982 | 0.982 | 9.5 | 9.8 |
| temporal-reasoning | 37 | 0.919 | 0.946 | 0.972 | 0.981 | 8.4 | 8.6 |
| knowledge-update | 19 | 1.000 | 1.000 | 1.000 | 1.000 | 6.4 | 6.5 |
| single-session-assistant | 44 | 1.000 | 1.000 | 1.000 | 1.000 | 7.2 | 7.3 |
| single-session-user | 17 | 1.000 | 1.000 | 1.000 | 1.000 | 6.2 | 6.2 |

+1 temporal question; within noise on dev (50 sessions per history, where the top 80 already covers most).
No type gets worse. Cost: 50% more reranker pairs for questions matching MULTI (~half of dev). Expected to matter
more on test (200 sessions per history, items spread over months), which cannot be measured with gold.
