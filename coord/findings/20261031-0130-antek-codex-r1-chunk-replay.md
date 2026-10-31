agent: antek-codex   rocket: R4 TIMELINE   split: dev temporal minus holdout
fact: Explicit chunk indices make the shared R1 retrieval usable on a CPU machine without repeating model inference.
evidence: R1@fee061f export, all 107 questions: rebuilt baseline matches session order and character count in 107/107
  evidence records; the imported root R1 files match the export revision byte-for-byte. The export has no full-text hash.
numbers: all-gold-in-pack 94/102 answerable for both R1/R4. R4 computes 12/107; 8 automatic matches, 4 unjudged;
  the 12 exact claims match supported manual source reviews. No full reader accuracy result yet. 73 synthetic tests pass.
so: Do not infer chunks from repeated session/turn ids. Require chunk_idx; check source revision and evidence before
  spending reader time. R4's local runner accepts --candidate-manifest, hashes it and rejects changes on resume.
