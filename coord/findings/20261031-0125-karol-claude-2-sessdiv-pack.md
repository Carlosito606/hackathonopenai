agent: karol-claude-2 (POLIGON)
fact: Ordering R1's ranked chunks so that every candidate session gets its best chunk before any session gets a
second one ("sessdiv") fixes most of the near-miss crowding. All gold sessions in pack, R1 926005e candidates:
dev-hard multi 0.722 -> 0.959, temporal 0.814 -> 0.902, all 0.884 -> 0.965 (R1 at 18k vs sessdiv at 26k);
dev multi 0.928 -> 0.990, temporal 0.892 -> 0.980, all 0.955 -> 0.992. A pack holds 13.5 sessions instead of
5.7. Where the gold answer is a checkable phrase, it is still written in the pack more often (dev-hard 147 -> 159
of 234, dev 156 -> 170). At 18k sessdiv loses single-session-assistant answers (dev 49 -> 36 of 57: long
assistant answers need several chunks of one session); at 26k nothing is lost. Max whole message 27,728 chars.
Query-relevant sentence pruning (rule-based) helps less: dev-hard all 0.927 at 18k.
evidence: rockets/poligon/pack_policies.py on runs/r1/20261030-2320-926005e-{dev,hard}; ideas from gbrain-evals
LongMemEval-S "sessdiv" (github.com/garrytan/gbrain-evals, docs/benchmarks/2026-05-07-longmemeval-s.md) and
Nano-Memory's query-driven pruning (arXiv 2604.11628).
so: use sessdiv with a 26k budget (at least for counting and temporal questions). Unmeasured: how the reader
copes with 13 sessions of which about 3 are near-misses; that is where a verifier (R7) earns its place.
