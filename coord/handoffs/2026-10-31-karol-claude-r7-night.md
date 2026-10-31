agent: karol-claude (R7 GUARDIAN, Karol's laptop; Karol asleep until ~08:00 CET)

done (all merged to main through PRs #5, #10, #12; #13 open):
- R7's gate: entity presence (`pack`) + SQuAD 2.0 no-answer score on single-fact shapes (threshold -5). No reader:
  dev minus holdout 13/25 right, 2/398 false; dev-hard v1 26/107, 2/398; about the same on R1's real candidates.
- Reactor check (t10, 00:12-01:04 UTC, run by Karol): on the 43 questions the gate abstains on Reactor abstained on
  41 by itself; gate gain 1, loss 1. Verdict: keep the gate off the ship (posted as [LESSON]).
- Error analysis and dead ends with numbers in rockets/r7/LOG.md: whole-history presence, compound nouns, entity
  swap, answer-name co-location; one test-informed rule reverted after review.
- [WARNING] reactor/predictions.py cuts histories at U+2028 (test: 2 of 15 lines); workaround in the team README.
- Tools: plan.py (R1 prompt on R7 evidence for ask.py), gate_value.py, apply_gate.py, cite_on_abstain.py (kept out
  of the ship by mission control's decision), check_submission.py (sanity checks for ship/predictions.jsonl).
- Pitch deck for Karol (Polish, 7 slides): https://claude.ai/artifact/B4cdFf7VCFyGeovJtw2QRe (private to Karol).

not done / open:
- LLM claims + NLI gate: dev (157 q) adds 1 right abstention per 2 false at best; dev-hard sample still running.
- llm_check.py (Qwen as YES/NO verifier): only a 3-question smoke test.
- Desktop GTX 1660 went offline twice tonight (sleep); Qwen runs on the laptop iGPU (Vulkan) instead, ~2x slower.

learned:
- With R1's prompt Reactor already abstains on the near-misses a cheap gate catches; more abstention rules need far
  better than 1:1 precision to pay, and injected near-miss sessions defeat presence and span-confidence signals.
- Never design rules from test questions, even without gold.

next:
1. When the final R1 test run lands: `python rockets/r7/check_submission.py ship/predictions.jsonl ../data/test`.
2. If time allows after the deadline: R7's gate as a Reactor-call saver (it predicts the reader's abstention 41/43).
