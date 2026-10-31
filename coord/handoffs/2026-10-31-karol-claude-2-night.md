# Handoff: POLIGON night shift (karol-claude-2, 2026-10-31, written from 01:20 UTC on)

**Merged on main (PR #7, #8):** local judge (`judge.py`, selftest 0.951 on Qwen2.5-7B Q4_K_M), injection audit
(`check_injections.py`), failure analysis (`failures.py`), R1 pack budget study (`pack_budget.py`), findings
20261031-0110 (budget) and 20261031-0115 (near-miss crowding).

**Open: PR #15** (branch poligon/dev-hard-v2; merged by patryk-opencode's review process, not by me):
- dev-hard v2: 135 LLM-audited exclusions (`exclude_v2.jsonl`), new ids (`splits/dev_hard_ids.txt`). Audit rounds
  93, 20, 8, 4, 4, 3, 2, 1; stopped in round 8 when the machine ran out of memory (not converged to zero).
- dev-hard-long (`--pad-to 200`, `splits/dev_hard_long_ids.txt`), test-like traps (`make_traps.py`, `--traps`,
  `reader_probe.py`), sessdiv pack study (`pack_policies.py`, finding 20261031-0125), r1_run.py with question_date,
  PITCH.md (Polish slide "5a. Poligon" for docs/PRESENTATION.md).

**Asked on the channel (01:18 UTC):** patryk-opencode to run R1's final code on dev-hard v2 and dev-hard-long with
r1_run.py (Mac GPU idle during the final) and to share the 39 Reactor calibration answers with hand verdicts (to
validate the judge); patryk-claude to take the slide.

**Local state (Karol's machine):** `C:\Users\karol\data\dev_hard` is v2 built with 134 of the 135 exclusions
(one pair behind the committed list; rebuild when memory allows); `dev_hard_v1` is kept (R7's NLI run reads it).
Traps: `data\poligon_runs\traps.jsonl` (83: 43 other-person, 40 plan; local only). Model server: llama-server on
port 8897 (started by Karol; 13 GB private memory with the Vulkan build); R7 runs its own on 8899 (6 GB). Free
memory went under 2 GB at night; Claude Code reaped the audit loop once.

**Not done:** audit rounds 8+ (memory), a dev-hard-long build and its BM25 numbers (1.1 GB, memory), reader
probe results (see LOG.md if it finished).
