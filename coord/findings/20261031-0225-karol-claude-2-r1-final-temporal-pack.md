agent: karol-claude-2 (POLIGON)
fact: With R1's final code (fee061f), 8 of 102 answerable dev temporal questions still miss a gold session in the
18k pack; 6 of them have it among the candidates and lose it to the budget (typically 5 of 6 sessions of an
enumeration: counting ends off by one), 2 never retrieve it. Packs rebuilt exactly from the chunk-indexed export
(107/107 identical to the run). Ordering the candidates "sessdiv" (best chunk of every session first) at the same
18k: all gold in pack 94 -> 100 of 102; larger budgets without it: 97 (22k), 98 (26k). Where the answer is a
checkable phrase (78), it stays in the pack for 44 instead of 41 questions (6 gained, all day-difference
questions; 3 lost).
evidence: rockets/poligon/pack_budget.py rebuild (now exact for [session_id, turn, chunk_idx, score] rows) and
pack_policies.sessdiv on runs/r1/20261031-0040-fee061f-temporal-chunks; dev minus holdout.
so: R1 diversifies sessions only for counting and two-event questions; every temporal question gains from it.
Untested: R1's own diversify() instead of the hard ordering, dev-hard, and the reader.
