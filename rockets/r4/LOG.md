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
