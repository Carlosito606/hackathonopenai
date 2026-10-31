agent: antek-codex   rocket: R4 TIMELINE   source: c3c72ec, r4-global-source-schema-v1
split: same one prespecified non-holdout multi-session count question; not an independent question sample
model: Qwen2.5-7B-Instruct-Q4_K_M, bb5d59e06d9551d752d08b292a50eb208b07ab1f, local only

what: One request binds every source to a required JSON field with its own literal-name enum. Code supplies
source ids/quotes, merges exact names and computes identity-group cardinality. No generated count is trusted.
This fixes malformed/borrowed source spans but cannot establish semantic coverage.

numbers: 22 visible user fragments, 5,284 excerpt characters, 7,947 prompt characters, 16,700 literal choices,
1,094,366 schema bytes. One model call, finish_reason=stop. Two real names from the first source, every other
source empty, complete=true. Diagnostic count=2. A review of all excerpts, recorded before the reply existed
and without reading gold, had identified five named items, including three missing asserted work/completion
cases. Scoped named-item recall 2/5; completeness claim false. No pipeline caches or reader facts accepted.

limits: The audit is an agent review of the visible source subset, not human adjudication or a full-history
exhaustiveness proof. Generic plural mentions and acquisition wording remain explicit uncertainty. This is
one repeatedly developed case, not full multi-session accuracy, a comparison to R1, or a latency benchmark.
The server is shared with the temporal and per-source experiments. 116 synthetic tests pass on this branch.

so: A schema constrains spelling/source attribution, not recall. Do not promote a literal, complete=true
response to a total without a coverage check. Next: shorter source batches with a shared observed-name ledger,
then independent source audits and the full paired multi-session reader evaluation. Keep defaults disabled.
artifacts: private /tmp/r4-global-schema-probe-v1.json and /tmp/r4-global-manual-source-audit-v1.json; raw reply
and diagnostic ledger under ignored rockets/r4/cache/global-schema-probe-v1/. Neither is an inference input.
