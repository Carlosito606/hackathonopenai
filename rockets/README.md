# The fleet: one rocket per machine

Each machine (a person and all their accounts) builds ONE rocket: a complete pipeline from a dataset history to
`predictions.jsonl`, built around one idea that no other rocket uses. All rockets share the launch pad
(`core/CONTRACT.md`: four stages and the run artifacts), so at the end their best parts can be combined into one
ship. Why this works and where it breaks: section "Why" below.

## Portfolio

Each rocket takes a different cell on three axes, so the fleet covers the space instead of converging on one idea:
**unit** (what is indexed and retrieved), **reading** (how evidence becomes an answer), **memory build** (what is
computed before questions arrive).

| # | Rocket | Machine | Unit | Reading | Memory build | Bet: which question types it should win | Lineage |
|---|---|---|---|---|---|---|---|
| R1 | HYBRID | <zeemowo> | turn chunks | single shot, dates tagged | embeddings | single-session, baseline for all | current pipeline at repo root |
| R2 | SESSION-RANK | <machine> | turns matched, sessions scored (NDCG over reranked turns) | short notes, then answer | embeddings | multi-session, knowledge-update | Emergence AI (82-86% LongMemEval) |
| R3 | FACT-LEDGER | <machine> | atomic dated facts extracted per session, pointing to turns | facts + source turns | local LLM extraction | knowledge-update ("latest wins" in code), single-session-user | LongMemEval fact-augmented keys, Mem0 |
| R4 | TIMELINE | <machine> | events with absolute dates | code computes order, durations, counts; Reactor phrases and cites | event extraction + date resolver | temporal, counting multi-session | Zep/Graphiti temporal graph |
| R5 | OBSERVER | <machine> | dated observation log (history compressed ~5x) | observations + raw turns for citations | local LLM observer/reflector | multi-session, temporal | Mastra Observational Memory |
| R6 | AGENTIC | <machine> | any (start from R1) | iterative: model proposes follow-up searches, 2-3 rounds | none | multi-session, paraphrased questions | ReAct; Reactor can browse a public search URL |
| R7 | GUARDIAN | <machine> | R1 candidates | verification first: whole-entity check, QA/NLI gate per type, citation pruning | none | abstention, near-misses, evidence F1 (every type) | SQuAD 2.0, Self-RAG |
| R8 | ROUTER | <machine> | per type | question-type classifier (test has no labels) + per-type budgets and prompts | none | all: picks the best tactic per type | needed by the final ship |
| P | POLIGON (test range) | <machine> | - | - | - | builds `dev-hard` (dev + injected near-miss sessions, like test), a local LLM judge for score.py's "unjudged", failure analysis | not a rocket |

More machines than rows: R9 FULL-MEMORY (load whole histories into Reactor's own memory, the official baseline;
costly in Reactor time, so test on 2 histories first) or a second POLIGON. Fewer machines: drop R6, then R5.
Several accounts on one machine: they all work inside that rocket; the machine's owner splits the work.

## A rocket's folder

```
rockets/<slug>/
  README.md     mission, current design, numbers (keep the top 20 lines current: others read them)
  rocket.py     STAGES = {"retrieve": ..., "enrich": ..., "assemble": ..., "decide": ...}  (what it has)
  run.py        dev or test split -> runs/<slug>/<run_id>/ artifacts (core/CONTRACT.md section 2)
  LOG.md        append-only: what was tried, numbers, kept or dropped
```

Start end-to-end fast: on day one a rocket may use R1's stages for everything except its own idea, so it can
produce predictions and be measured within hours. Then it replaces the defaults it wants to own.

## Why, and the conditions it needs

Independent exploration that shares lessons and occasionally swaps parts is the island model of evolutionary
search (FunSearch, AlphaEvolve-style systems: islands evolve separately and periodically migrate their best
candidates), and the way Kaggle teams build ensembles from diverse models. It only pays off if:
1. **Parts fit together:** the four-stage contract and the artifact format are fixed from the start.
2. **One judge:** same splits, same stand-in model, same scorer, baseline measured on the same machine.
3. **Diversity is designed, not hoped for:** population-based search converges early without it. That is why each
   rocket owns a different cell above, and why parts may only migrate at sync points (AGENTS.md section 4).
4. **Reactor is budgeted:** one stateful agent, one question at a time (AGENTS.md section 5).
5. **Dev is not test:** dev has no near-miss distractors and 30 unanswerable questions in all; POLIGON's `dev-hard`
   and the holdout keep the final choice honest.
