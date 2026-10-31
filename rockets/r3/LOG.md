# R3 LOG (append-only)

- 2026-10-30 patryk2-claude: rocket scaffold (extract, rocket stages, run). Ledger unit-checked on a synthetic Starbucks case (120 wins over 300, assistant 400/125 marked). No dev numbers yet.
- 2026-10-31 01:00 patryk2-claude: Qwen2.5-1.5B unusable (copies prompt examples, invents values); JSON output loops and gets cut (0 facts, 290 s/session); pipe format + 3B: 73 s/session. 3B misses the newer value in 3 of 13 answerable k-update questions (both gold sessions were in R1's top 2). Ledger now says "Latest" only with 2+ values.
- 2026-10-31 01:36 patryk2-claude: Reactor t10 A/B, 15 k-update dev q, R1@926005e candidates: R1 15/15, F1 0.718; R3 13/15, F1 0.641, 1 false abstention. DROPPED as a prompt-side part: R1 is at the ceiling on dev k-update, the ledger misleads on "previous value" questions. runs/{r1,r3}/*-ku15.
