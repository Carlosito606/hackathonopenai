agent: karol-claude-2 (POLIGON)
fact: R1's evidence budget (18,000) is what loses multi-session gold on near-miss-heavy histories. Rebuilding
R1's packs from its own candidates with larger budgets: dev-hard v1 multi-session all-gold-in-pack 0.722 (18k)
-> 0.814 (22k) -> 0.845 (26k), temporal 0.814 -> 0.853, all 0.884 -> 0.925; dev multi 0.928 -> 0.959, temporal
0.892 -> 0.931. Other types stay at 1.000. Only 1.5% of gold sessions never reach R1's 80 candidates on dev-hard
(0.3% on dev), so the rest is the budget. Longest whole message (kit build_message + prepare GUIDE): 27,234 chars
at 26k, 29,117 at 28k (ask.py refuses > 30,000). Routing 26k only to prepare.COUNTING / memsys.TEMPORAL questions
keeps most of the gain (dev-hard multi 0.825, all 0.910).
evidence: rockets/poligon/pack_budget.py on runs/r1/20261030-2320-926005e-{dev,hard} (patryk-opencode). The
rebuild maps the k-th appearance of a turn to its k-th chunk, so 60-75% of packs match the run exactly and the
rest differ by about one session; levels match the run within 1-3 points.
so: a 26k budget for counting and temporal questions is the cheapest retrieval gain left for R1. Untested: how
Reactor reads a pack with more near-misses, and the added latency.
