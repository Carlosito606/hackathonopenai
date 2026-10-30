# R4 log (append-only)

## 2026-10-30 — antek-codex — first implementation

- Forked R1's date block from memsys.py at de158d5; no standalone dates.py exists on this baseline.
- Implemented interval-aware date resolution, conservative event matching and code arithmetic.
- Added all four contract stages, paired R1/R4 runner and partial-run audit tooling.
- Downloaded official dev and score.py outside the repository; no holdout examples inspected for development.
- 19 synthetic tests pass, including the real scorer behind a deterministic HTTP protocol fixture.
- Benchmark answer numbers pending: the team's stand-in endpoint/model has not been configured locally.
- Initial R1 CPU retrieval preparation started; model download and runtime are tracked separately from accuracy.

## 2026-10-30 — antek-codex — validation before review

- Expanded to 24 passing synthetic tests: cancellation vs attendance, other-person events and before/after premises.
- Reader runs now verify the server advertises exactly the recorded team model; mismatches stop before scoring.
- A one-time human-authorized authenticated connection check succeeded; no Reactor question or history reset was sent.
- Code contains no Reactor execution path or access key. Shared Reactor reservations remain with humans.
- Team endpoint/model requested; no end-to-end quality score is available, and no claim beats R1.

## 2026-10-30 — antek-codex — stand-in configuration

- Team confirmed Qwen2.5-7B-Instruct, 4-bit; the Mac endpoint is not remotely accessible.
- Preparing the official Q4_K_M GGUF with llama.cpp CPU locally, recording the exact model revision separately.
- Expanded to 25 passing tests; a missing final marker records an empty response and a reader failure, not abstention.
- This machine has 8 GiB RAM: R1 preparation and the local reader must run sequentially to avoid memory pressure.
- R4 now also enriches the preceding user excerpt that R1 brings with assistant candidates; the final pack must
  still contain the actual supporting text. All 26 tests pass.
- Added contract interoperability (no private R1 fields required), code selection of first/last events and
  rejection of future events as completed events. All 31 tests pass. Candidate caches remain unchanged R1 output.

## 2026-10-30 — antek-codex — initial real-history diagnostic

- An all-user-turn diagnostic (not R1 retrieval or a reader benchmark) produced 14 computations / 107 temporal
  dev questions; the automatic scorer matched 8 and left 6 unjudged. These are not answer-accuracy numbers.
- Checked one disagreement against the exact gold source ids: their stated event dates are 81 days apart,
  while gold says 15 weeks. Recorded a data-quality finding; arithmetic is not forced to match that label.
- A generic art-museum mention could match a specific named museum through scattered words. Fixed coherent
  name/title matching and explicit aliases; added alphanumeric-name and question-as-event regression tests.
- All 35 tests pass. Temporal questions now have preparation priority; completed multi-session caches are retained.
- Neutralized the inherited format example in both R1 and R4 prompts before any Reactor smoke test; named examples
  from task data are not allowed to prime either variant. Baseline retrieval and evidence selection are unchanged.

## 2026-10-30 — antek-codex — reserved Reactor smoke, 22:50–22:56 UTC

- Human authorized use when free. Confirmed RELEASE and obtained an exclusive window; used 4 calls and released early.
- Two available temporal questions from the canonical reactor_mini split, holdout excluded, identical cached R1
  candidates for both variants. R1 source de158d5; neutral format example in both prompts. Code sha 616bb63.
- R1: 2/2 correct, evidence F1 0.75. R4: 2/2 correct, evidence F1 0.75. All four client statuses answered.
- R4 computed one source-grounded fact: 2022-10-22 to 2023-03-25 = 154 days, 5 complete calendar months;
  the reader used it correctly. The other question fell back to reading. No broad quality claim from n=2.
- Model latencies (seconds): R1 94.29 / 41.39; R4 80.95 / 91.68. Too few observations for a speed comparison.
- Standard run artifacts and scorer details are published; raw plans/replies stay in ignored cache, no key stored.
