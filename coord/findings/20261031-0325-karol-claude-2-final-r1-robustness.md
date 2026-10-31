agent: karol-claude-2 (POLIGON)
fact: R1's final code (fee061f) loses 3.8 points of "all gold sessions in the evidence pack" on dev-hard v2 and
6.8 on dev-hard-long (test-length histories): all 0.972 / 0.935 / 0.905, multi 0.969 / 0.907 / 0.825, temporal
0.922 / 0.833 / 0.804, k-update 1.000 / 1.000 / 0.983, single-session 1.000 everywhere (398 paired answerable
questions). The first R1 (926005e) lost 6.3 on dev-hard v1 (0.952 -> 0.889). On v2 the final code's losses are 7
crowded, 7 retrieval, 1 other (first R1 on v1: 23 crowded): its session diversity and date windows fixed most
of the crowding. Packs hold 3.4 injected sessions on average.
Pack order sessdiv + rule-based pruning at the same 18k budget, on the final candidates: all gold in pack dev
0.992, v2 0.965, long 0.937 (vs 0.972 / 0.935 / 0.905); the gold answer phrase stays in the pack on dev 0.714 vs
0.692 and v2 0.671 vs 0.654, but on long 147 vs 151 of 234: with 200-session histories the extra sessions start
to crowd out answer text.
evidence: runs/r1/20261031-0200-fee061f-final-{dev,dev-hard-v2,dev-hard-long} (patryk-opencode, chunk-indexed, so
packs rebuild exactly); rockets/poligon/compare_dev_hard.py, crowding.py, pack_policies.py.
so: the submitted R1 is robust to near-misses on dev-sized histories; test-length histories cost another ~3
points, mostly multi-session and temporal. The next gain is there (retrieval of the last missing session), not in
a bigger or reordered pack.
