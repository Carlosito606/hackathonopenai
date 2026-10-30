# Research notes (karol-claude, 2026-10-30)

Everything found while setting up the team, with sources, so it survives account switches. Vendor numbers are
self-reported and measured differently (recall vs accuracy, different readers): compare ideas, not scores.

## 1. The benchmark under the challenge

- Dev = LongMemEval-S (Wu et al., ICLR 2025, https://arxiv.org/abs/2410.10813, repo
  https://github.com/xiaowu0162/LongMemEval). Five abilities: extraction, multi-session reasoning, temporal
  reasoning, knowledge updates, abstention. The paper's own design lessons, worth a direct try:
  round (turn) granularity beats session granularity for indexing; fact-augmented keys (index extracted facts
  next to raw text) raise recall; time-aware query expansion helps temporal questions; Chain-of-Note plus a
  structured evidence format improves reading by up to ~10 points.
- Test = new data, same format, ~200 sessions per history, near-miss sessions on purpose, ~8% unanswerable,
  no type labels.

## 2. Systems and what to borrow (rocket lineage)

| System | Idea | Reported | Borrow for |
|---|---|---|---|
| Emergence AI (https://www.emergence.ai/blog/sota-on-longmemeval-with-rag) | match turns, retrieve whole sessions scored by NDCG of cross-encoder-reranked turns; short CoT; "Accumulator" Chain-of-Note variant 81.8% but 111 s/item | 82.4% Simple, 86% internal; naive turn RAG 52%; full-context GPT-4o 60-64% | R2 |
| Emergence per type (Simple / Internal) | k-update 79.5 / 83.3, multi 73.7 / 81.2, ss-asst 100 / 100, ss-user 95.7 / 98.6, temporal 81.2 / 85.7 | | where the headroom is: multi-session, temporal |
| Mastra Observational Memory (https://mastra.ai/research/observational-memory) | observer turns chats into dated observations, reflector condenses past a threshold (default 40k tokens); ~5-6x compression on LongMemEval | 84.2% gpt-4o, 94.9% gpt-5-mini | R5 |
| Hindsight (https://arxiv.org/html/2512.12818v1) | four memory networks (world facts, experiences, entity summaries, beliefs); retrieval = vector + keyword + graph + temporal filter in parallel | 39.0% -> 83.6% with an open 20B backbone; 91.4% with a large model | R3, R4 |
| Zep / Graphiti (https://arxiv.org/abs/2501.13956, https://github.com/getzep/graphiti) | temporal knowledge graph with validity intervals | | R4 |
| Mem0 (https://arxiv.org/abs/2504.19413) | fact extraction with add/update/delete | | R3 |
| SQuAD 2.0 (https://arxiv.org/abs/1806.03822) | unanswerable questions written to look answerable (negation, antonym, entity swap, mutual exclusion, impossible condition) | 86 F1 on 1.1 -> 66 on 2.0 for the same model | R7 |
| Self-RAG / CRAG (https://arxiv.org/abs/2310.11511, https://arxiv.org/abs/2401.15884) | the model judges whether retrieved text suffices | | R7 |
| HippoRAG 2, A-MEM, RAPTOR, MemGPT | graph/PPR multi-hop, linked notes, summary trees, tiered memory | | R6 ideas |

Leaderboard caution: independent re-runs often fall short of vendor claims
(https://dev.to/gaurav_dadhich/the-state-of-ai-memory-in-2026-claimed-vs-observed-1n94); MemPalace's 100%
claim is disputed.

## 3. Exam-style datasets as training data (question from Karol)

The near-miss unanswerables resemble exam distractors (SAT, Cambridge "not given"). Verdict: useful for a
verifier, not for retrieval or temporal reasoning. SQuAD 2.0 and NLI/FEVER (NOT ENOUGH INFO) fit best; DREAM
(dialogue exams, https://arxiv.org/abs/1902.00164, licence unknown) and RACE (non-commercial research) are
multiple-choice without abstention; real SAT/Cambridge material is copyrighted. Best path: synthetic
near-misses from dev (swap one entity in a real question, label unanswerable) to fine-tune or calibrate.
Measured with an off-the-shelf SQuAD 2.0 model: see finding `squad2-verifier`.

## 4. Fleet strategy grounding (island model)

Independent populations with periodic migration keep diversity in LLM-driven evolutionary search (FunSearch,
AlphaEvolve-style systems; GigaEvo https://arxiv.org/html/2511.17592v1 uses a fixed migration interval and ratio
~0.1; Mind Evolution https://arxiv.org/pdf/2501.09891 adds island resets). Without explicit diversity management
populations converge early (LoongFlow https://arxiv.org/html/2512.24077v1). Hence: designed portfolio, one
migrated part per sync point, mid-flight reset.

## 5. Reactor facts that shape the plan (reactor/PARTICIPANTS.md)

One stateful agent per team: one dataset history and one question at a time; `--new-history` from anyone breaks
a run (`history_changed`); parallelism only across agent ids. Client limit 16,000 chars (`--max-chars`), server
32,000. Default timeout 300 s, answers take tens of seconds. Loading a whole test history: ~65-125 parts, each a
full agent turn. Citations only from `--evidence`; abstention via `INSUFFICIENT_EVIDENCE` and
`predictions.py --abstain-on agent`. The agent can browse public URLs (our own search endpoint is allowed).
