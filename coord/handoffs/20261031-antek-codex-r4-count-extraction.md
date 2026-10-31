agent: antek-codex   rocket: R4 TIMELINE   branch: r4/count-extraction   PR: #21 (DRAFT)

Implemented: opt-in cached item facts across the four stages, literal closed-list rules, a local per-fragment
extractor, code-assigned sources/sentences, exact-repeat merging and explicit model-proposed alias partitions.
Source spans, dates, quoted evidence, period membership, full message length and cache/resume hashes are checked.
96 tests pass; changed Python files compile. Default behavior does not load counting caches. Counts, date facts
and computations.jsonl now distinguish what was actually supplied to the reader from unused calculations.

Real local-model evidence: one first eligible cached dev multi-session count question, repeated across two
protocols. Global v1 (dirty prototype) failed literal quote/name/source checks. Per-source v2 at clean 24701ff
failed on its first response: one name appended descriptive words not present in the user source. Both rejected
before caching/supplying any count fact. No answer-accuracy or counting-improvement claim. Only 6/57 count
questions have legacy R1 candidates locally; 3 currently pass the scope profile. Do not call this a benchmark.

v2 job terminal (pid 86790 no longer present, extraction-summary.json records invalid_source_response=1).
Private output: rockets/r4/cache/counting-probe-v2; log:
/home/antekpusz/hackathon/.tools/r4-count-extraction-logs/probe-v2.log. Loaded-source hashes/model revision recorded.

Next: bind cache reuse to the exact visible user-source footprint across assembly changes; add at most one
literal-span repair request per source using generic validation feedback; repeat the same source audit and then
obtain full paired multi-session scores with named retrieval provenance. Weighted sums, occurrence counts,
inventory updates and complex scopes remain required later work. Keep PR #21 draft/default counts disabled.

Do not modify the independent running temporal benchmark worktree r4-chunk-manifest at 42ab798. Supervisor
84683, reader 84686, runner 84755; status/logs under .tools/r4-manifest-benchmark-logs, 9/107 pairs at this handoff.
It will run official scoring and the exact-claim audit after all 107. No latency claim: the local extraction
probe shared the queued reader. Reactor is reserved for final R1 from 01:38 through 08:15 UTC; no R4 calls.
Channel bridge antek-codex remains connected. Continuous human-authorized R4 goal stays active.
