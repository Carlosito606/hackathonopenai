agent: karol-claude
fact: All 30 unanswerable dev questions are near-misses of a real fact: one entity swapped (hamster/cat Luna,
violin/guitar, Korea/Japan, table tennis/tennis, Shinjuku/Harajuku, Dr. Johnson/Dr. Smith, Italian/Korean
restaurants), half of a two-part question missing (Hawaii + Seattle, headphones + iPad), or a false premise
(job at Google not started yet).
evidence: gold.jsonl abstain=true answers on dev, all 30 read by hand.
so: retrieval will find a near-hit with a high score; check that every specific entity of the question appears
as a whole phrase in the evidence. Test adds more such near-misses on purpose.
