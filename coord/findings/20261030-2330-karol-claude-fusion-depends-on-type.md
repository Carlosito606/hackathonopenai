agent: karol-claude
fact: The best retrieval combination differs by question type. Three plain BM25 variants (all turns, user turns
only, assistant turns only), RRF-fused in every combination with core/permlab.py: all gold sessions in the top 5
sessions, dev minus holdout: fusing all three lifts multi-session 0.670 -> 0.722 and temporal 0.725 -> 0.745, but
drops ss-assistant 1.000 -> 0.944 and ss-user 1.000 -> 0.980. Best overall single run: all turns (0.844).
evidence: core/permlab.py retrieval --k 5 on smoke-test runs (not committed).
so: the final ship should choose retrieval per question type (R8 ROUTER), not one fusion for everything; every
rocket must write candidates.jsonl so these combinations can be tested without Reactor.
