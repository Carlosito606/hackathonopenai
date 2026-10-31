agent: antek-codex   rocket: R4 TIMELINE   branch: r4/count-literal-repair

Implemented: exact visible-user-source and prompt fingerprints for counting cache identity, a maximum of one
literal/JSON repair per fragment, and immutability of the known inventory on failed attempts. Uncertainty and
transport failures do not trigger repair. Complete source scope must match before cached items are reused.
Literal zero after period filtering does not establish a global zero. The scoped counting arithmetic still
returns zero normally; the answering stage defers to R1 without affirmative support for an empty inventory.

Full reference: 107/107 multi-session non-holdout packs reconstructed from
runs/r1/20261031-0200-fee061f-final-dev, named reference fee061f065f52e3045ec63acf10b0655210fef98.
All gold sessions in pack: R1 94/97 answerable, R4 94/97; no counting cache, no computed facts, no reader score.
Preparation source clean 9586db6, local run runs/r4/full-multi-reference-9586db6 (do not present it as accuracy).
Verification permits only differences in the unused retrieve body; signatures/defaults, all other retrieval AST
and exact date/evidence/facade/prompt bytes remain checked. 102 tests pass; touched Python files compile.

Next local validation: same prespecified first eligible count question as v1/v2, now using the full named R1
manifest and v3 repair. Private process handle/outcome: /tmp/r4-counting-probe-v3.json when launched; inspect
actual process/logs before deciding it is live or terminal. Defaults stay opt-in until real source audits and
full paired multi-session scores. Weighted sums, event counts and current inventories remain later work.

Temporal reader: original processes ended under heavy memory pressure; 11 pairs survived. The exact run/source
42ab798 was resumed with the same weights/context/KV precision/batches/decoding and bounded host caches.
Supervisor 88767, reader 88772, worker 88802; .tools/r4-manifest-benchmark-logs/active-resume.json points to logs.
The guard stops only our reader before sustained low memory. Runtime sidecar records the pair boundary.
Do not modify/rebase r4-chunk-manifest while it runs; publish scoring/audit only after all 107 pairs finish.
Bridge antek-codex remains connected. Reactor stays reserved for the team's final; no R4 Reactor calls.
