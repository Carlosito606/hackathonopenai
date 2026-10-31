agent: antek-codex   rocket: R4 TIMELINE   PR branch: r4/timeline-pr   benchmark branch: r4/timeline

done:
- All four contract stages in rockets/r4/rocket.py, reusing root R1 retrieval.
- The original benchmark worktree keeps R1@de158d5. New PR-branch runs record the current root R1 snapshot
  at baseline_sha=git_sha, so newer main changes cannot be mislabeled as the historic baseline.
- Forked date parser, event matching and code calculations for grounded exact durations and ordering.
- Range/inference handling for weekends, bare ordinals, calendar months; rejects plans and ambiguous matches.
- Paired R1/R4 artifact runner, partial-run auditor, model-identity check; no Reactor execution path.
- 68 synthetic tests pass, including date/actor-scope checks, interrupted paired-run recovery and the official scorer.
- Ordering supports disjoint explicit date ranges; complete calendar months/years clamp month-end anniversaries.
- All-user-turn parser diagnostic after scope fixes: 12 computations / 107 temporal questions (not R1 retrieval,
  not a reader score); 8 automatic matches, 4 unjudged.
- Verified one temporal gold/source inconsistency, recorded separately in coord/findings/.
- Reserved Reactor smoke @616bb63 completed: 2 canonical temporal questions, R1 and R4 both 2/2 correct,
  evidence F1 0.75 each. Later audit withdrew the one fact's verification: its date grounds recollection of a
  tour, not the tour. Predictions and scores are unchanged. Reservation RELEASE sent at 22:56 UTC.
- Corrected scope: a date stays with its own coordinated predicate; a dated recollection does not date its subject.
- Without computed facts, R4 returns the identical R1 pack/prompt. The local evaluator shares a reader result
  only when both complete plans are identical, and records the reuse count and per-question status.
- Manual source audit of ten computations at the 23-question checkpoint: eight supported, two unsupported in the
  earlier code. Both scope errors are covered by regressions; the full answer evaluation is still pending.
- Six additional all-user-turn computations were source-reviewed: four supported, two dated a related event
  (club meeting / return) instead of the target event. New regressions reject those exact-date claims.
- report.py can join manual verdicts by exact computation hash. Local ignored cache/source-audit.json holds 16
  iterative reviews (12 supported, 4 unsupported); selected development audit, not an unbiased precision estimate.
- Official dev/scorer and dependencies downloaded outside the repository; holdout excluded throughout.

not done:
- End-to-end dev answer comparison: the Qwen2.5-7B-Instruct Q4_K_M model and llama.cpp are installed locally;
  the sequential supervisor starts the reader after retrieval releases its memory.
- Full R1 retrieval preparation: resumed on CPU, 32/107 at the latest checkpoint; all weights are downloaded.
- Independent auditing of computed-fact correctness on dev; no claim of improvement over R1.
- Cross-session counting, semantic event extraction, local-model fallback for unresolved dates.
- PR creation needs an authenticated GitHub connection; a connector was requested separately.

learned:
- No standalone dates.py exists in the baseline; R4 forks memsys.py's date block without modifying shared code.
- Do not count protocol-fixture accuracy as a benchmark. Partial runs have complete=false and no fake predictions.

next:
1. Monitor /home/antekpusz/hackathon/.tools/r4-benchmark-logs/supervisor-state.json and prepare.log. The supervisor
   runs temporal retrieval then paired local reading. Existing candidate caches are preserved; do not run two
   neural stages concurrently on this 8 GiB machine. Host processes require a host-level process check because
   the default filesystem sandbox isolates /proc.
2. Run rockets.r4.report; inspect computed facts against dev gold separately from automatic partial matches.
   The supervisor now invokes the report with the hash-bound manual audit and writes completion.json under logs.
3. Complete the paired 214-question answer run; record per-type scores, update README and announce measured findings.
4. Keep at most three milestone run folders. Do not commit dataset text, candidate caches or raw reader replies.
5. `run.py --resume --run-id ORIGINAL_ID` resumes at the same clean source commit and reader configuration;
   only complete paired questions are retained. A changed commit needs a new run id and reuses candidate caches.
