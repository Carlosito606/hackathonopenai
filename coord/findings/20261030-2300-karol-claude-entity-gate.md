agent: karol-claude
fact: A whole-word entity gate on R1's evidence pack abstains on 6/25 unanswerable dev questions (temporal 4/5)
with 2/398 false abstentions, when it checks only proper names and quoted titles. Checking every content word
gives 0.44 recall but 0.28 false abstention (verbs and frame words are not in excerpts). Most swapped entities
("Korea", "Shinjuku", "Google", "Rachel", "Italian") ARE in the pack, from other sessions, so presence alone
cannot catch them.
evidence: rockets/r7 (run.py + measure.py), dev minus holdout, 423 q, BM25 candidates, no reader.
so: use the gate as a cheap precise filter; near-misses whose entity occurs elsewhere need a QA/NLI signal or a
warning to the reader. Strip stopwords on both sides before phrase matching ("Husbands of Evelyn Hugo").
