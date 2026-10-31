# R4 TIMELINE — antek-codex

Bet: code computes event dates, elapsed time and event order; the reader phrases the answer and cites sources.
Status: initial implementation merged in PR #11; exact R1 chunk-manifest replay now available for local evaluation.
Reactor smoke @ `616bb63`, temporal n=2: R1 2/2 correct, R4 2/2; mean evidence F1 0.75 for both.
R4 supplied one computed fact; a later source audit found its event date unsupported (the dated action was recollection).
This two-question smoke makes **no claim of improvement over R1**.
Checks: 101 synthetic tests cover temporal/item scope, paired recovery, official score.py and exact chunk selection.
Baseline: root R1 at each run's recorded `baseline_sha`, same candidates/machine; dev minus holdout.
Historical smoke and the original in-progress CPU run use R1 at `de158d5`; their artifacts keep that provenance.
Both variants neutralize the inherited format example to `<answer> [E4]`; no named answer example is seeded.
Stand-in: Qwen2.5-7B-Instruct Q4_K_M downloaded; it starts after R1 preparation to fit 8 GiB RAM.
R1@fee061f export: all 107 temporal evidence manifests rebuilt with identical session order and character counts.
Preparation: 94/102 answerable packs contain all gold sessions in both variants; 12/107 grounded computations.
The same 12 exact claims have supported source audits; reader accuracy is still unmeasured on this full split.
Parts: all four contract stages in `rocket.py`; R1 retrieval, R4 enrichment/assembly/decision.
Dates: `dates.py` forks the date block in R1 `memsys.py` at `de158d5` (there was no standalone dates.py).
Counting: opt-in local item extraction, grounded spans, identity deduplication and bounded period counts.
Limits: counting semantics/coverage remain unmeasured; the default pipeline does not load counting caches.
Artifacts: `runs/r4/20261030-224702-616bb63-reactor-smoke/` (reserved 4 calls, then released early).

## What the first implementation does

- Classifies differences, elapsed time, order, counting and date/entity lookups without gold or type labels.
- Separates counts within a period from distances between boundaries; supports elapsed `since` and forward `after`.
- Resolves explicit dates, weekdays and relative day/week offsets in the current history's session date.
- Adds `two weekends ago`, `the 15th`, `a couple of days ago`, calendar month offsets and period ranges.
- Keeps weekends as ranges; omitted months/years and conversational month offsets are marked inferred.
- Exact calculations require two uniquely grounded event dates (or one event and the question date).
- Chronological order also works for disjoint date ranges; overlapping ranges leave order unresolved.
- Complete calendar months/years use clamped anniversaries (January 31 → February 28, leap-day anniversaries).
- Rejects plans, negations, assistant suggestions, conflicting matches and ambiguous multi-date sentences.
- Keeps dates with their coordinated action; a dated recollection or discussion does not date the recalled event.
- A date in a relative clause stays with that clause; a return date does not prove the attendance date.
- A decision to act can date the decision; it does not establish that the planned action happened.
- Matches coherent entity names/titles and question-provided aliases, not a bag of their words.
- Adds computed facts and their `[E#]` labels only when their supporting text is included in the evidence pack.
- Without a grounded computation, returns the identical R1 evidence pack and prompt.
- Accepts contract candidates without R1's private fields and session/fact units without a turn number.

## Reproduce

`counting.count_distinct(history, items, window=None)` counts a supplied item ledger. Each extraction must point
to a literal entity span in a user turn; optional date spans resolve against that history and must belong to
the same asserted event clause. Exact-name normalization preserves near names, acronyms and articles.
Repeated entities retain their source mentions but count once. An uncertain period membership produces a
lower/upper bound rather than silently excluding an item. The result explicitly does **not** certify item
semantics or history coverage; it must not be used as the user's total without extraction/coverage validation.
Run the arithmetic and extraction invariants with `python -m unittest rockets.r4.test_counting rockets.r4.test_count_extract`.

Experimental counting integration is opt-in. First prepare R1 candidates in a fresh cache for the source
revision being measured, then extract items using the same candidates and the team's stand-in:

```bash
python -m rockets.r4.extract_counts --data /path/dev --candidate-cache /path/candidates \
  --out rockets/r4/cache/counting --local http://127.0.0.1:8899 --reader TEAM-MODEL
python -m rockets.r4.run --data /path/dev --types multi-session --candidate-cache /path/candidates \
  --counting-cache rockets/r4/cache/counting --local http://127.0.0.1:8899 --reader TEAM-MODEL --scorer /path/score.py
```

Literal closed lists use rules. Mixed prose is processed one user fragment at a time; code assigns the source
and copies the supporting sentence, while the model selects literal names and optional links to known entities.
Exact repeats merge in code; other alias links remain explicit local-model hypotheses, not independently proven
identities. The counter performs all arithmetic. Missing/invalid extractions, unresolved dates or an omitted
supporting quote produce the unchanged R1 pack/prompt. Empty extraction does not establish a zero inventory.
Weighted quantities, occurrence counts, changing inventories and complex/vague periods currently fall back.
Extraction is a separate CLI; the four stages never call a model endpoint. Invalid JSON or literal names get
at most one repair request with validation feedback; uncertainty and transport errors are not retried. The
known inventory changes only after an accepted response. Both attempts and their input hashes are cached.
Cache keys bind question/history/candidate text, extractor prompts/schema and the exact visible user-source
footprint. Assembly changes that expose different fragments invalidate reuse. The paired runner records cache
hashes and rejects changes on resume.
Source/quote validation does not certify semantic recall or ownership. Local-model completeness claims are
identified as such in reader facts. Do not enable this by default before paired multi-session evaluation.
If the full inventory would exceed the client message budget, R4 uses the unchanged R1 pack rather than
discarding items. Computation artifacts count only facts actually included in the final reader pack.

From the repository root, using Python 3.11+ and the R1 dependencies in this folder's requirements.txt:

```bash
R4_SCORER=/path/to/memory-challenge/score.py python -m unittest rockets.r4.test_timeline rockets.r4.test_contract rockets.r4.test_checkpoint rockets.r4.test_report -v
R4_DEVICE=cpu python -m rockets.r4.run \
  --data /path/to/dev --types temporal-reasoning,multi-session \
  --local http://TEAM-STAND-IN:8899 --reader TEAM-MODEL \
  --scorer /path/to/memory-challenge/score.py
```

The integration test uses the official scorer from `R4_SCORER` (default `./score.py`); otherwise it skips
that test. Its reader is a protocol fixture and its perfect synthetic result is **not** a benchmark metric.

Replay R1's shared, text-free chunk export without loading retrieval models:

```bash
python -m rockets.r4.run --data /path/to/dev --prepare-only \
  --candidate-manifest runs/r1/20261031-0040-fee061f-temporal-chunks
```

For answers, replace `--prepare-only` with the local reader/scorer options above. The runner checks the R1
source revision and every selected question's evidence manifest before any answer calls. Explicit chunk indices
select text from the question's own history. Turn-only exports and mismatched session/character manifests fail;
matching manifests validate those exported fields, not an independently exported hash of the full evidence text.
Export hashes are recorded in both variants' metadata and cannot change during checkpoint resume.

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
When their complete plans are identical, the local runner asks once and records the shared result for both.
`summary.json:shared_reader_results` and `reader_status.jsonl` record this reuse; changed evidence or prompts
always get a separate reader call. The protocol integration test checks actual call counts and paired outputs.
Use `--resume --run-id ORIGINAL_ID` with the same options and clean source commit to resume an interrupted run.
Recovery keeps only the common complete prefix of both variants and recomputes an interrupted pair. Changes
to source, reader revision, endpoint or data path are rejected; a partial last JSON append can be recovered.
The endpoint must advertise exactly `--reader` at `/v1/models`: root `ask.py --local` uses the server's default.
R4 may
omit an evidence session if date annotations would exceed the 24,000-character evidence budget. Computation
coverage and automatic scorer matches are reported separately from reader answer accuracy; automatic partial
matches do not establish independent fact correctness. Measurements under three percentage points are noise.
An all-user-turn diagnostic (not R1 retrieval and not an answer benchmark) produced 12 computations on 107 temporal
dev questions. One gold/source inconsistency was verified independently; see the R4 temporal-gold finding.
Reproduce the parser-only diagnostic with `python -m rockets.r4.diagnose --data DEV --scorer SCORE_PY`.
If the reader omits its final-answer marker, the runner records an empty response and a protocol-failure count;
it does not convert that failure into an evidence-based abstention. Transport errors leave the run incomplete.

`report.py --source-audit PATH` optionally joins manual source judgments to the exact hash of each calculation's
facts, answer and source ids. Changed claims or questions remain unreviewed. These judgments are used only in
reporting; they never enter the stages or reader prompt. Report supported/unsupported/unreviewed counts alongside
automatic scorer matches, and describe how the reviewed subset was selected.
