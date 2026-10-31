# R4 TIMELINE — antek-codex

Bet: code computes event dates, elapsed time and event order; the reader phrases the answer and cites sources.
Status: first end-to-end Reactor smoke completed; full paired stand-in evaluation is still running.
Reactor smoke @ `616bb63`, temporal n=2: R1 2/2 correct, R4 2/2; mean evidence F1 0.75 for both.
R4 supplied one computed fact (5 complete calendar months / 154 days), verified against the source and used correctly.
This two-question smoke makes **no claim of improvement over R1**.
Checks: 46 synthetic tests pass, including interrupted paired-run recovery and official score.py through a local reader fixture.
Baseline: R1 at `de158d5`, same retrieval candidates, same machine; dev minus `splits/dev_holdout.txt`.
Both variants neutralize the inherited format example to `<answer> [E4]`; no named answer example is seeded.
Stand-in: Qwen2.5-7B-Instruct Q4_K_M downloaded; it starts after R1 preparation to fit 8 GiB RAM.
Parts: all four contract stages in `rocket.py`; R1 retrieval, R4 enrichment/assembly/decision.
Dates: `dates.py` forks the date block in R1 `memsys.py` at `de158d5` (there was no standalone dates.py).
Limits: no local semantic event extractor or cross-session item counter yet; ambiguous events fall back to reading.
Artifacts: `runs/r4/20261030-224702-616bb63-reactor-smoke/` (reserved 4 calls, then released early).

## What the first implementation does

- Classifies differences, elapsed time, order, counting and date/entity lookups without gold or type labels.
- Resolves explicit dates, weekdays and relative day/week offsets in the current history's session date.
- Adds `two weekends ago`, `the 15th`, `a couple of days ago`, calendar month offsets and period ranges.
- Keeps weekends as ranges; omitted months/years and conversational month offsets are marked inferred.
- Exact calculations require two uniquely grounded event dates (or one event and the question date).
- Chronological order also works for disjoint date ranges; overlapping ranges leave order unresolved.
- Complete calendar months/years use clamped anniversaries (January 31 → February 28, leap-day anniversaries).
- Rejects plans, negations, assistant suggestions, conflicting matches and ambiguous multi-date sentences.
- Matches coherent entity names/titles and question-provided aliases, not a bag of their words.
- Adds computed facts and their `[E#]` labels only when their supporting text is included in the evidence pack.
- Conservatively falls back to R1-style reading rather than generating an ungrounded count or date.
- Accepts contract candidates without R1's private fields and session/fact units without a turn number.

## Reproduce

From the repository root, using Python 3.11+ and the R1 dependencies in this folder's requirements.txt:

```bash
R4_SCORER=/path/to/memory-challenge/score.py python -m unittest rockets.r4.test_timeline rockets.r4.test_contract rockets.r4.test_checkpoint -v
R4_DEVICE=cpu python -m rockets.r4.run \
  --data /path/to/dev --types temporal-reasoning,multi-session \
  --local http://TEAM-STAND-IN:8899 --reader TEAM-MODEL \
  --scorer /path/to/memory-challenge/score.py
```

The integration test uses the official scorer from `R4_SCORER` (default `./score.py`); otherwise it skips
that test. Its reader is a protocol fixture and its perfect synthetic result is **not** a benchmark metric.

`--prepare-only` writes retrieval, evidence and computation artifacts without calling a reader. Such runs have
`complete: false`; they deliberately have no fabricated predictions or answer scores. `report.py` audits partial
runs too, reporting how many questions have actually been processed:

```bash
python -m rockets.r4.report runs/r4/RUN_ID --data /path/to/dev --scorer /path/to/score.py
```

Every answer run creates paired artifacts under `runs/r4/<id>/` and `runs/r4/<id>/baseline-r1/`. Plans, raw reader
replies, candidate text and embedding caches stay under ignored `rockets/r4/cache/`. No test-split runs are
supported by this development runner. It has no Reactor execution path and never accesses the operator's key.

For a fair comparison, both variants use the same cached R1 candidates and the same stand-in endpoint.
Use `--resume --run-id ORIGINAL_ID` with the same options and clean source commit to resume an interrupted run.
Recovery keeps only the common complete prefix of both variants and recomputes an interrupted pair. Changes
to source, reader revision, endpoint or data path are rejected; a partial last JSON append can be recovered.
The endpoint must advertise exactly `--reader` at `/v1/models`: root `ask.py --local` uses the server's default.
R4 may
omit an evidence session if date annotations would exceed the 24,000-character evidence budget. Computation
coverage and automatic scorer matches are reported separately from reader answer accuracy; automatic partial
matches do not establish independent fact correctness. Measurements under three percentage points are noise.
An all-user-turn diagnostic (not R1 retrieval and not an answer benchmark) produced 16 computations on 107 temporal
dev questions. One gold/source inconsistency was verified independently; see the R4 temporal-gold finding.
Reproduce the parser-only diagnostic with `python -m rockets.r4.diagnose --data DEV --scorer SCORE_PY`.
If the reader omits its final-answer marker, the runner records an empty response and a protocol-failure count;
it does not convert that failure into an evidence-based abstention. Transport errors leave the run incomplete.
