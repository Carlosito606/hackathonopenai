agent: antek-codex   rocket: R4 TIMELINE   split: one dev multi-session question, holdout excluded
source: dirty prototype over 95e67f4; Qwen2.5-7B-Instruct-Q4_K_M; not an answer benchmark
fact: A global item-extraction request over 15 visible user fragments generated canonicalized labels and rewritten
  quotes instead of literal spans, mixed source indices, and claimed completeness while omitting relevant source items.
evidence: first available eligible cached question in dataset order (5,603 input JSON characters); 1/1 responses
  rejected by literal source validation, zero reader facts supplied. Raw reply/prompt stay in ignored local cache.
so: Do not use model-reported complete=true as proof of coverage. Assign sources and copy quotes in code. The
  replacement processes one fragment at a time and exposes non-exact alias links as local-model hypotheses.
status: 95 synthetic tests pass; replacement still needs an actual local-model probe and paired multi-session scoring.
  No default enablement, no improvement claim. The separate full temporal reader run remains at 42ab798.
