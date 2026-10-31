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

## 2026-10-31 — antek-codex — interval ordering and calendar boundaries

- Ordering may use disjoint explicit date ranges while exact durations still require exact days. Overlapping
  intervals and mixed-date clauses remain unresolved. No inferred month/year is promoted to exact certainty.
- Complete month/year differences now use clamped calendar anniversaries, including January 31 and February 29.
- All 40 synthetic tests pass; these changes still need the full paired reader evaluation. The published Reactor
  smoke remains tied to its actual source sha 616bb63 and contains no ordering questions.

## 2026-10-31 — antek-codex — resumable local evaluation

- Resumed CPU retrieval from the preserved candidate cache; 23/107 temporal dev questions prepared at the
  checkpoint. Both variants contain all gold sessions in 19/23 packs; this is a partial retrieval audit only.
- The partial run supplies 10 computations; 7 match the automatic scorer and 3 remain unjudged. This is not
  independently verified computation accuracy or a completed reader comparison.
- Added `--resume`: retain the common complete question prefix across paired artifacts; retry an interrupted
  pair, recover a truncated last append, and reject changed source/model/data configuration. Reader failure
  counters survive recovery. A localhost integration test interrupts R1/R4 and then finishes through score.py.
- Use R1's public cached reranker factory so the split memsys facade is supported without `_reranker`.
- All 46 tests pass. The parser-only all-history diagnostic at 5c697f6 produced 16 computations, 11 automatic
  matches and 5 unjudged; this does not use R1 retrieval and is not an answer benchmark.
- Latest team R1 export lacks chunk ids for multi-chunk turns. Requested exact identifiers; no reconstruction
  is passed off as identical retrieval. The local sequential CPU/Qwen supervisor continues independently.

## 2026-10-31 — antek-codex — correction after source audit

- Manually reviewed all ten computed facts in the 23-question checkpoint. Eight had directly supported event
  dates; two did not. A date can modify remembering a past tour, or starting to enjoy music after an undated
  discovery, without dating the target visit/discovery. These ten observations are a small source audit.
- The unsupported tour-date fact was also the one fact supplied in the Reactor smoke at 616bb63. The earlier
  "verified" statement above is withdrawn: both reader scores remain 2/2, but the fact was not source-grounded.
  Corrected the aggregate verification field and added an explicit audit note; predictions and scores are unchanged.
- Date extraction now retains only the coordinated predicate containing the expression. Recollections and
  discussions cannot date their subjects; questions about the recollection itself remain supported.
- All 51 tests pass, including the two scope patterns, an actual dated visit followed by recollection, and a
  directly dated recollection. The final reader run will recompute facts using the corrected source.
- Extended the same distinction to deciding versus acting, and past intentions (wanted/hoped/planned). All 54
  tests pass. Replaying the ten cached cases drops precisely the two unsupported facts and retains the other eight.
- Post-fix all-user-turn diagnostic: 14/107 computations, 9 automatic matches, 5 unjudged; still not R1 retrieval
  or reader answer accuracy. This diagnostic was run on the scope patch over 98e95c5 before its own commit.

## 2026-10-31 — antek-codex — forms and actor scope

- Count questions with temporal boundaries are classified as counts before parsing between A and B; mentioning
  a week elsewhere in such a question does not turn the counted item into a duration.
- Added elapsed "since I" and forward "after A did I B" forms. Before/after premises must agree with source dates.
- Recognize shared action stems consistently. When a question explicitly asks about my event, a family member's
  solo event does not become mine just because that person is named as my companion in the question.
- All 60 tests pass. The all-history diagnostic now records dirty source status as well as the commit.

## 2026-10-31 — antek-codex — exact fallback and shared local inference

- When R4 cannot supply a grounded calculation, its pack and prompt now equal R1 exactly. Date/precision
  changes and computation instructions are applied only where R4 has a fact to supply.
- The local runner compares complete plans and reuses the R1 result only for exact equality. Changed prompts
  or evidence always trigger their own call. Both predictions are retained; `shared_reader_results` and the
  per-question reader status record reuse. Recovery restores that counter as well as protocol failures.
- The localhost integration test verifies one actual reader call for identical plans, equal paired predictions,
  and a separate interrupted/recovered pair when the plans differ. All 61 tests pass.
- JSONL checkpoint recovery uses actual file newlines, preserving Unicode line separators inside JSON strings;
  the regression covers U+2028 and U+0085 in an answer. All 62 tests pass. This applies the data-format lesson
  shared by Karol to R4's own recovery reader; the organisers' kit is unchanged.

## 2026-10-31 — antek-codex — related-event dates and hash-bound source review

- Inspected six additional computations from the all-user-turn diagnostic. Four were supported; two used a
  related event's date: a reading-group meeting rather than finishing a book, and returning from a workshop
  rather than attending. The book ordering answer happened to be correct despite an unsupported exact date.
- A relative clause containing the expression now retains its own scope. Returning from an event may date the
  return itself but does not prove the attendance date. Four regression tests cover the positive and negative cases.
- Current all-user-turn diagnostic: 12/107 computations, 8 automatic matches, 4 unjudged. All twelve surviving
  claims were inspected against their source user turns. This is development/source review, not reader accuracy.
- Added optional manual source-audit joining in report.py, bound to the exact facts, answer and source ids plus
  question id. Changed claims remain unreviewed; conflicting judgments fail. The ignored local audit has 16
  iterative reviews: 12 supported, 4 unsupported. It never enters retrieval, computation or reader input.
- All 68 tests pass. Full temporal CPU preparation reached 32/107; the old preparation's computed facts are
  from 5c697f6 and are not final R4 results. Final reading recomputes with the corrected code. The supervisor
  creates both score artifacts, the source-aware audit, and a completion.json after all 107 questions finish.

## 2026-10-31 — antek-codex — PR on current main

- Created a fresh unpublished r4/timeline-pr from the published review branch, rebased onto current main,
  preserving both published branch histories and the original in-progress benchmark worktree.
- All 68 tests pass with the current split R1 modules. New runs record root R1 at their actual git snapshot
  as baseline_sha instead of inheriting the historical de158d5 label. Historical artifacts remain unchanged.

## 2026-10-31 — antek-codex — complete temporal preparation from R1 chunk export

- PR #11 merged by mission control. Forked r4/chunk-manifest from main@130f913 to use the promised R1 export
  at runs/r1/20261031-0040-fee061f-temporal-chunks without loading embedding/reranking models on this CPU.
- All 107 baseline packs reproduce the exported session order and character count. Root R1 files match
  fee061f byte-for-byte. Explicit chunk indices avoid the ambiguous repeated-turn mapping; source/export hashes
  and full selected-question validation protect reproducibility and resume. No full-text reference hash was exported.
- Dev temporal minus holdout, preparation only: all-gold-in-pack 94/102 answerable questions for R1 and R4;
  12/107 computations, 8 automatic scorer matches and 4 unjudged. All 12 match previously inspected, supported
  source claims by exact claim hash. These are coverage/source metrics, not paired reader accuracy.
- 73 tests pass, including a later window ranked before the first window, foreign sources, invalid indices,
  incomplete manifests, duplicate questions, changed export identity on resume and actual local-reader/score.py.
- Pass question_date into current R1 retrieval so its question-relative windows match prepare.plan_question.
- Replaced the older incomplete CPU preparation with this verified complete export; old artifacts/caches are
  preserved. Next: Qwen2.5-7B-Instruct-Q4_K_M paired reader on all 107, with the exact same candidates in both arms.

## 2026-10-31 — antek-codex — auditable distinct-item arithmetic

- Added a standalone counting kernel on a separate worktree while the full temporal reader run remains frozen
  at 42ab798. It does not yet change any pipeline fact, question, prediction or reader call.
- Item identities come from literal spans in user turns of this history. Typography/case/whitespace normalize;
  near names, acronyms and different articles do not collapse. Duplicate mentions keep source links, not votes.
- Period counts use event dates, not conversation dates. Unknown/inferred dates and boundary-crossing intervals
  yield bounds. An independently dated in-period mention can establish membership despite undated repeats.
- Date spans must belong to the item's own asserted event clause; recollections, plans, another person's action,
  and a different coordinated action cannot lend the item their date. This applies the temporal scope finding.
- Nine new synthetic invariants pass. Arithmetic provenance does not validate semantic extraction, ownership,
  completeness, aliases or inventory updates; result flags explicitly retain these limits. No dev count-accuracy
  claim. Next: a conservative item extractor, followed by paired multi-session scoring before enabling counts.

## 2026-10-31 — antek-codex — opt-in item extraction and a failed global protocol

- Connected cached item extractions to enrich/assemble/decide; no count cache is loaded by default. The reader
  receives item/source links and code's count, with explicit uncertainty about local semantic extraction/aliases.
- Cache keys bind the question, history and candidate text. Run/resume fingerprints cover the extraction files;
  changing them during a run fails rather than mixing old and new facts. Missing source quotes do not shrink totals.
- Literal closed lists have a rule path; other user excerpts require the local stand-in. Weighted sums, event
  occurrence counts, current inventory changes and complex/vague periods remain pending and fall back to R1.
- Development cache availability: 6/57 multi-session count questions had existing CPU R1 candidates, 3 with
  supported scopes. Tested the first such question, not selected by gold outcome; the 15-source global prompt
  produced one invalid response (rewritten quotes/labels, wrong source indices), rejected before supplying facts.
- Replaced generated source ids/quotes with per-fragment requests. Code copies the sentence, exact repeats merge
  deterministically, and local alias links refer only to known observed entities. Model completeness remains
  unverified. Raw responses, loaded-source hashes and metadata stay in ignored caches. No count accuracy claim.
- 95 synthetic tests pass, including full stage assembly, source hallucination rejection, partial-word rejection,
  omitted evidence, period uncertainty, alias partition checks and official scorer/local-reader regression tests.
