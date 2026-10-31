agent: patryk2-claude (R3 FACT-LEDGER)
fact: On dev, R1@926005e already puts every gold session of knowledge-update and single-session-user questions in
the pack (both 1.000), so fact keys cannot win on retrieval there; R3's only lever is reading (the ledger). With a
CPU-only laptop (Ryzen 5 2500U), local extraction is the bottleneck and small models fail in specific ways:
- Qwen2.5-1.5B-Instruct Q4: copies example values from the prompt as facts ("monthly rent 1200 USD", "dog Max"),
  copies category names as attributes, invents values ("Not specified, but likely ..."). Unusable.
- JSON output: the model repeats one fact until max_tokens, the cut JSON fails to parse -> 0 facts, 290 s/session.
  A pipe format `turn | speaker | attribute | value`, max 300 tokens, repeat_penalty 1.15, keeping complete lines:
  43 s/session (1.5B), 73 s/session (3B).
- Qwen2.5-3B-Instruct Q4, no examples in the prompt, system + "list the facts" after the chat: sensible facts, but
  on 15 k-update questions (both gold sessions in R1's top 2 for 13 of 13 answerable) it missed the NEWER value in
  3 cases (Negroni 5 -> 10, coding 1 h -> 2 h, volleyball 3-2 -> 5-2) and caught the change in 1 (bikes 3 -> 4).
evidence: rockets/r3/ (extract.py, rocket.py), runs/r3/20261031-0201-9f488cf-ku15, dev minus holdout, 15 k-update q.
so: a ledger built from incomplete extraction must not label a single value "Latest" (it states the OLD value as
current when the update was missed). R3 now says "Latest" only when it saw 2+ values and tells the reader the facts
can be incomplete. Fact extraction for "latest wins" needs a model >= 7B or a GPU; on CPU, prefer code-side
signals (correction regex, dates) over LLM facts.

update 01:40 UTC, Reactor t10 A/B (same 15 k-update questions, same R1@926005e candidates, each arm in its own
Reactor history, arms alternating): R1 pack 15/15 correct (13 auto + 2 unjudged checked by hand), evidence F1 0.718;
R1 pack + ledger 13/15 (11 + 2), 1 false abstention, evidence F1 0.641. Lost: "previous personal best" (the ledger's
"latest wins" note pulled the reader to the NEWER value; the question asked for the old one) and one false
abstention (ledger full of off-topic facts). On dev k-update R1 is at the ceiling: a fact ledger can only add noise.
so: DEADEND for a prompt-side ledger on dev. Never tell the reader "latest wins" without reading the question
("previous", "before", "used to", "originally" ask for the old value). Remaining value of R3: none measurable on dev;
maybe on test near-misses, untested.
