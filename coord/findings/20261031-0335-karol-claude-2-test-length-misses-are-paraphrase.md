agent: karol-claude-2 (POLIGON)
fact: At test length the submitted R1 loses gold mostly in retrieval, and to paraphrase. On dev-hard-long (200
sessions per history) R1 fee061f misses a gold session in 38 of 398 answerable questions: 25 have a gold session
outside the 100 ranked candidates, 13 have it among them but cut by the 18k budget (dev: 3 and 8; dev-hard v2:
14 and 12). Of the 35 gold sessions missing from the candidates on long, 28 share at most one content word with
the question in any user turn, 13 carry the fact in an aside ("By the way ..."), and only 12 mention a question
word in the first user turn. Examples: "the order of the three trips I took" vs a turn about "a solo camping trip
in the Eastern Sierra"; "the life event of one of my relatives that I participated in" vs "hiring a wedding planner".
evidence: runs/r1/20261031-0200-fee061f-final-{dev,dev-hard-v2,dev-hard-long} candidates.jsonl/evidence.jsonl
(patryk-opencode), dev_hard_long histories, word overlap after stop words.
so: the next retrieval gain at test length is semantic, not lexical or packing: expand the question with the
category it names (trip -> camping, flight, visit; life event -> wedding, graduation, birth), or index per-session
notes/facts (R3, R5 ideas) next to raw turns, and give enumeration questions a larger candidate pool.
