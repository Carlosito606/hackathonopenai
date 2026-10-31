agent: karol-claude-2 (POLIGON)
fact: Padding dev-hard v2 histories to test's 200 sessions with filtered random sessions from other histories
(dev-hard-long) costs plain BM25 another 3 points on top of the near-misses: all gold sessions in the top 5
sessions, same 398 answerable questions, dev / dev-hard v2 / dev-hard-long: multi 0.670 / 0.423 / 0.392, temporal
0.725 / 0.529 / 0.471, k-update 0.966 / 0.845 / 0.828, ss-user 1.000 / 1.000 / 0.961, ss-asst 1.000 / 0.989 /
0.978, all 0.844 / 0.714 / 0.681 (top 10: all 0.907 / 0.852 / 0.809). Single-session questions start to lose
gold only with test-length histories.
evidence: rockets/poligon/make_dev_hard.py --exclude rockets/poligon/exclude_v2.jsonl --pad-to 200, bm25_run.py,
compare_dev_hard.py (splits/dev_hard_long_ids.txt).
so: dev (~50 sessions per history) overstates retrieval on test (200); measure a ship on dev-hard-long before
trusting its dev numbers. R1 (final code) on dev-hard v2 and dev-hard-long is being measured by patryk-opencode.
