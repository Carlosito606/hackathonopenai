agent: antek-codex   rocket: R4 TIMELINE   source: 9586db6 / frozen temporal reader 42ab798

Multi-session reference: runs/r1/20261031-0200-fee061f-final-dev contains the required chunk ids already.
All 107 non-holdout multi-session packs rebuilt with the exported session order and character count. Baseline
reference fee061f065f52e3045ec63acf10b0655210fef98; all-gold-in-pack 94/97 answerable for both R1/R4, no reader
score yet. Preparation source was clean 9586db6. Counts are disabled without an explicit extraction cache.
Reconstruction compares all retrieval AST except the unused retrieve body; the current change only widens its
candidate pool. Chunking/signatures/defaults remain checked, and date/evidence/facade/prompt bytes match exactly.

Local runtime: the first temporal reader terminated under severe memory pressure, leaving 11 completed pairs.
The installed llama.cpp b12017 defaults to 8192 MiB host prompt cache, plus up to 32 context checkpoints.
The resumed runtime disables both retention policies and idle-slot saving; weights, KV precision, context,
threads, batch sizes, question plans and decoding parameters stay the same. Runtime sidecar records the boundary.
At the first check, four more pairs completed with minimum available memory ~3.1 GiB; this is an operational
observation, not a throughput/answer-accuracy comparison. A guard stops only our reader after sustained low memory.
All 214 cached temporal plans tokenized offline: max raw message 7024, reserve 64 wrapper + 600 output <= 8192.
Full temporal scoring remains pending; no R4 Reactor calls during the team's final reservation.
