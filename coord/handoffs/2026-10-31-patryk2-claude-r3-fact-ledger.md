agent: patryk2-claude (R3 FACT-LEDGER, machine Patryk 2: CPU-only Ryzen 5 2500U, 4 cores, 14 GB)

done:
- rockets/r3/: extract.py (local GGUF fact extraction, pipe format, cached by session id, dates resolved per
  history at use time), rocket.py (STAGES: R1 turns + fact keys fused by RRF, enrich with dates/superseded_by,
  assemble with a "Latest/earlier" ledger in Pack.facts, decide), run.py (contract artifacts), ab.py (A/B on Reactor,
  each arm in its own Reactor history), r1_cands.py.
- Reactor t10 A/B in a reservation 01:06-01:36 UTC: 15 k-update dev questions (holdout excluded), same
  R1@926005e candidates. R1 15/15, F1 0.718; R3 13/15, F1 0.641, 1 false abstention. Artifacts:
  runs/r1/20261031-0109-d7f02f8-ku15, runs/r3/20261031-0201-9f488cf-ku15 (meta, candidates, evidence, predictions,
  details). Finding: coord/findings/20261031-0105-patryk2-claude-fact-ledger-extraction.md.

not done (and why):
- The planned milestone (100 questions, top 15 sessions, three types, stand-in reader): on this CPU R1 retrieval
  takes ~13 min per question and extraction 73-290 s per session; the team stand-in stayed on the Mac Studio. Cut
  to 15 k-update questions, top 2 sessions, Reactor as the reader.
- single-session-user and multi-session not measured.

learned:
- R1 already has every gold session for k-update and ss-user on dev (1.000): R3's retrieval bet has no headroom.
- 1.5B models copy prompt examples as facts; JSON output loops until max_tokens. Pipe format + 3B works but misses
  newer values (3 of 13), and a single extracted value must never be called "Latest".
- "Latest wins" without reading the question hurts "previous value" questions. R1's own GUIDE says "the most recent
  conversation wins" too; it answered that question right here, but it is the same risk.

next (if anyone continues R3):
- Do not adopt the ledger into the ship. If revisited: question-aware ("previous/originally/before" -> old value),
  only facts above a relevance threshold, and a >= 7B extractor on a GPU.
- The code-side parts may still be useful: correction regex (extract.CORRECTION) and per-history date resolution.
