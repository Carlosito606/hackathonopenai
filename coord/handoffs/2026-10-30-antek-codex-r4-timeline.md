agent: antek-codex   rocket: R4 TIMELINE   branch: r4/timeline

done:
- All four contract stages in rockets/r4/rocket.py, reusing R1 retrieval at de158d5.
- Forked date parser, event matching and code calculations for grounded exact durations and ordering.
- Range/inference handling for weekends, bare ordinals, calendar months; rejects plans and ambiguous matches.
- Paired R1/R4 artifact runner, partial-run auditor, model-identity check; no Reactor execution path.
- 40 synthetic tests pass, including contract interoperability, a local HTTP fixture and the official scorer.
- Ordering supports disjoint explicit date ranges; complete calendar months/years clamp month-end anniversaries.
- All-user-turn parser diagnostic: 14 computations / 107 temporal questions (not R1 retrieval, not a reader score).
- Verified one temporal gold/source inconsistency, recorded separately in coord/findings/.
- Reserved Reactor smoke @616bb63 completed: 2 canonical temporal questions, R1 and R4 both 2/2 correct,
  evidence F1 0.75 each; one computed fact verified and used correctly. Reservation RELEASE sent at 22:56 UTC.
- Official dev/scorer and dependencies downloaded outside the repository; holdout excluded throughout.

not done:
- End-to-end dev answer comparison: Qwen2.5-7B-Instruct 4-bit was confirmed by the team, but its Mac endpoint is
  local-only; a Q4_K_M/llama.cpp CPU installation is being prepared on this machine.
- Full R1 retrieval preparation: running on CPU; all neural weights and local Qwen are downloaded.
- Independent auditing of computed-fact correctness on dev; no claim of improvement over R1.
- Cross-session counting, semantic event extraction, local-model fallback for unresolved dates.
- PR creation needs an authenticated GitHub connection; a connector was requested separately.

learned:
- No standalone dates.py exists in the baseline; R4 forks memsys.py's date block without modifying shared code.
- Do not count protocol-fixture accuracy as a benchmark. Partial runs have complete=false and no fake predictions.

next:
1. Configure the team's stand-in and run python -m rockets.r4.run --data DEV --types temporal-reasoning,multi-session
   --local URL --reader MODEL --scorer SCORE_PY. Default candidate cache reuses completed R1 retrieval.
2. Run rockets.r4.report; inspect computed facts against dev gold separately from automatic partial matches.
3. Complete the paired 214-question answer run; record per-type scores, update README and announce measured findings.
4. Keep at most three milestone run folders. Do not commit dataset text, candidate caches or raw reader replies.
