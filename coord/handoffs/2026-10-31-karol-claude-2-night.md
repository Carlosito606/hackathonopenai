# Handoff: POLIGON night shift (karol-claude-2, 2026-10-31, 23:00-02:30 UTC)

**On main** (PRs #7, #8, #15, #18, #20; #22 open, merged by patryk-opencode's review process):
- dev-hard **v2**: 135 LLM-audited exclusions (`exclude_v2.jsonl`; audit rounds 93, 20, 8, 4, 4, 3, 2, 1, stopped
  in round 8 by a memory reap, not converged), new ids. **dev-hard-long** (`--pad-to 200`, test-length histories;
  patryk-opencode's Mac: `--check` passes, ids identical). `--version 1` rebuilds v1 byte-identically.
- Tools: `judge.py` (selftest 0.951; 21/22 agreement with a person on Reactor's unjudged answers), `check_injections.py`,
  `failures.py`, `pack_budget.py` / `pack_policies.py` / `crowding.py` (exact with chunk-indexed candidates),
  `make_traps.py` + `reader_probe.py` (test-like asides), `cite_expand.py`, `r1_run.py` (with question_date).
- Findings 20261031-0110 ... 0325: R1 pack budget, near-miss crowding, sessdiv, final-R1 temporal packs, test-length
  noise, llama-server shared context (DEADEND), Reactor under-cites, trap asides vs R1's GUIDE, judge vs human, final
  R1 robustness.

**Numbers for the presentation** (all gold sessions in the evidence pack, 398 paired answerable questions):
R1 final (fee061f) dev 0.972 / dev-hard v2 0.935 / dev-hard-long 0.905; first R1 on v1 0.952 -> 0.889. Crowding
losses 23 -> 7. Slide text: `rockets/poligon/PITCH.md` (slide 5a in docs/PRESENTATION.md was taken from an earlier
version; the newer bullets are in PITCH.md).

**Citations:** `cite_expand.py`'s expansion was measured on dev only (+4 to +8 points) and costs ~7 points on dev-hard
(near-misses share the most question words); patryk-opencode caught it and kept it out of the submission (my
correction is in coord/findings/20261031-0300). Adopted in the final submission (tag `submission`, main 9998ea2): `--abstentions-only`, so each of the 12
abstentions cites the best pack session (0 -> 0.44-0.65 evidence F1 on such questions when they are answerable; answers
and abstentions unchanged).

**After 02:30 UTC:** test-length misses are retrieval and paraphrase (finding 0335); LLM category expansion helps plain
BM25 on all splits but loses gold when fused into R1 (DEADEND, finding 0340); `report.py` gives any rocket the
three-split report in under a second (R7's run: 48 of 64 dev-hard misses are crowding); chart `r1-robustness.svg` and
README top lines updated (PR #23); v2 `--check` with the exclude list passes locally.

**Local state (Karol's machine):** `C:\Users\karol\data\dev_hard` = v2 with all 135 exclusions; `dev_hard_long`
(1.1 GB); `dev_hard_v1` kept (R7 reads it); traps `data\poligon_runs\traps.jsonl` (local only); R1 runs under
`data\poligon_runs\r1*`. Stand-in: llama-server on 8897 (started by Karol, 13 GB private memory; its 4 slots share
one 4,096-token context: send at most 2 long prompts at once). R1-side venv: `C:\Users\karol\venv-poligon`.

**Not done:** audit rounds 8+ (needs Karol's OK after the memory reap), a dev-hard-trap split build (the probe does
not need one). (cite_expand on top of the reply fallback was measured by patryk-opencode: 0.910 -> 0.955 on cal39,
dev only; irrelevant now, see Citations.)
