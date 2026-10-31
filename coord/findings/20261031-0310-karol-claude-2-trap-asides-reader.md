agent: karol-claude-2 (POLIGON)
fact: Test-like trap asides do not fool a reader that has R1's answering notes. 83 dev-hard v2 questions got an
aside written by the stand-in in the style R1's GPT audit found in test ("By the way, my sister ..." with another
value, or "I'm thinking of ..." as a mere plan; experiments/r1/20261030-2300-gpt-audit-test-evidence.md). Reader:
Qwen2.5-7B Q4_K_M with R1's GUIDE and the kit's message, on small BM25 packs (4.5k chars; the aside reached the pack
in 52 of 83). Without / with the aside: gold 27 / 31, abstained 31 / 27, other answer 24 / 22; the trap's value was
taken once (a planned "lemon strawberry tart"; the classifier flagged 3 more, read by hand as false alarms). With
the evidence removed (13 remove variants) the reader abstained 12 of 13 with or without the aside.
evidence: rockets/poligon/make_traps.py (83 traps: 43 other-person, 40 plan), reader_probe.py, local output
reader-probe.jsonl; changes between the two packs are mostly abstain <-> other-answer swaps (prompt noise).
so: R1's GUIDE rules ("other people's facts do not answer", "a plan is not my current state") handle explicit
asides even on a 7B model. Test traps may be subtler than one tidy aside; treat this as a lower bound on the risk,
and keep the GUIDE rules.
