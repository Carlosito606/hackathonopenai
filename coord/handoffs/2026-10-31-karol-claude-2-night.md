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

**Open decision for mission control:** `cite_expand.py` as post-processing of the submission (evidence F1 on Reactor's
cal39 answers 0.867 -> 0.951 / 0.795 -> 0.917 over final-line citations; combination with ask.py's reply fallback not
measured) and `--cite-abstentions` (an answerable question we abstain on scores F1 0 today; 0.646 on average with the
best pack session cited). Posted on the channel 02:17 UTC.

**Local state (Karol's machine):** `C:\Users\karol\data\dev_hard` = v2 with all 135 exclusions; `dev_hard_long`
(1.1 GB); `dev_hard_v1` kept (R7 reads it); traps `data\poligon_runs\traps.jsonl` (local only); R1 runs under
`data\poligon_runs\r1*`. Stand-in: llama-server on 8897 (started by Karol, 13 GB private memory; its 4 slots share
one 4,096-token context: send at most 2 long prompts at once). R1-side venv: `C:\Users\karol\venv-poligon`.

**Not done:** audit rounds 8+ (needs Karol's OK after the memory reap), a dev-hard-trap split build (the probe does
not need one), measuring cite_expand on top of the reply fallback (needs cal39 predictions with the fallback).
