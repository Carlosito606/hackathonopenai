agent: karol-claude-2 (POLIGON)
fact: [DEADEND] llama.cpp's llama-server (b12004) started with `-c 4096` and its default 4 slots shares ONE
4,096-token KV cache between the slots (log: "n_slots = 4, n_ctx_slot = 4096, kv_unified = 'true'"). Short
prompts (judge, audit: ~400 tokens) run 4 at a time fine; four R1-style prompts of ~1,700 tokens stalled: all 4
slots "processing", 1 token decoded in 10 minutes, then HTTP 500 for prompts over the context.
evidence: /slots on the stand-in server during rockets/poligon/reader_probe.py; a request with 102 prompt tokens
took 1.9 s on the same server.
so: with llama-server, size `-c` for (slots x (prompt + max_tokens)), or start it with `-np 1` (R7 does: -c 9216
-np 1), or send at most floor(c / (prompt + max_tokens)) requests at once (judge.py/reader_probe.py --workers,
reader_probe.py --ctx fits each message with the server's /tokenize).
