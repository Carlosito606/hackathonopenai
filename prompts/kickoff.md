# Kickoff prompts

Paste the common header plus your role's block as the FIRST message to your agent (Claude Code, Codex, Codex
cloud, any other). Replace `<...>`. The shared rules come from AGENTS.md in the repo.

---

## Common header (every role)

```
You are one of four parallel coding agents on our Memory Retrieval Challenge team repo
https://github.com/Carlosito606/hackathonopenai. Other agents, on other accounts and vendors (Claude, OpenAI),
change this repo at the same time. Before doing anything:
1. Read AGENTS.md and README.md completely. AGENTS.md is hard rules and overrides your habits.
2. Work only on your own branch in your own worktree:
   git fetch && git worktree add .worktrees/<role>-<topic> -b <role>/<topic> origin/main
   (cloud agents are already isolated; just use the branch name). Never commit to main.
3. Before the first edit, create coord/claims/<role>-<topic>.md (template in coord/README.md) and check no open
   claim covers the same topic.
4. Edit only your role's files/functions (AGENTS.md section 2). Anything else: write coord/requests/... and tell me.
5. Never call Reactor, never ask for or handle its key. Test end-to-end with ask.py --local and a local model.
6. Never commit data, *.pkl caches, plans/results/predictions, weights or secrets.
7. Finish each work session with: the checks of AGENTS.md section 6, an experiment file in experiments/<role>/
   (dev without splits/dev_holdout.txt, per question type, before and after), a handoff file, a small PR to main.
Report back to me in at most 5 lines: what changed, which metric moved per question type, what is not done.
Data is in ../data/dev (LongMemEval, with gold). On a machine without Apple Silicon use device "cpu"/"cuda"
locally without committing it.
```

---

## RETRIEVAL

```
Your role: RETRIEVAL. You own, in memsys.py: split_text, session_chunks, tokens, Embedder, reranker,
sub_queries, retrieve, session_ranking; and eval_retrieval.py.
Goal: all gold evidence sessions inside the evidence for multi-session and temporal questions (the weak types:
several evidence sessions each), while keeping precision so the evidence fits the message budget.
Known traps: facts hide in "By the way ..." asides inside off-topic sessions; questions paraphrase the evidence
("piece of jewelry" vs "crystal chandelier"); test adds near-miss sessions about other people.
Start by measuring eval_retrieval.py per question type on all of dev (not only 150 questions), then pick the
worst type. Ideas: decomposing multi-part and counting questions ("how many X ...") into sub-queries, more
candidates for counting questions, entity-aware query expansion, sentence-level chunks for asides.
Keep retrieve()'s return format (list of dicts with session, turn, role, text, score): VERIFIER depends on it.
```

## TEMPORAL

```
Your role: TEMPORAL. You own the date code in memsys.py (EPOCH ... TEMPORAL, day_no, _mark, annotate_dates);
put new logic in new files (e.g. dates_kupdate.py) until the INTEGRATOR splits memsys.py.
Goal: make time and change explicit before evidence reaches Reactor, which is weak at arithmetic.
Known traps: relative dates are relative to the SESSION date; the same session id has different dates in
different histories; values change across sessions and even inside one session ("Actually, 120, not 300"),
and the assistant sometimes states wrong numbers; same-day updates need the time of day.
Ideas, in order: (1) check annotate_dates on every dev temporal question and list misses (e.g. "two weekends
ago", "the 15th", "a couple of days ago"), (2) knowledge-update: mark superseded values so the evidence says
which statement is the latest, (3) compute durations/orderings in code and state the result in the evidence.
Unit-test every date rule on tiny examples.
```

## VERIFIER

```
Your role: VERIFIER. You own build_evidence in memsys.py, prepare.py (including GUIDE), and a new verify.py.
Goal: abstain exactly when the history lacks the answer, send Reactor the right excerpts, cite the right sessions.
Known traps: ~6-8% of questions are unanswerable near-misses: one entity swapped (violin vs guitar, Korea vs
Japan, table tennis vs tennis, "Software Engineer Manager" vs "Senior Software Engineer") or half of a two-part
question missing. Token/prefix overlap fails ("Korea" matched "Korean"): compare whole multi-word entities.
Over-strict checks hurt too: gold sometimes paraphrases ("jewelry" answered by "crystal chandelier").
Measured: a ready SQuAD 2.0 QA model (deepset/roberta-base-squad2, best span minus no-answer) separates
answerable from unanswerable with AUC 0.95-0.99 on single-session-user and knowledge-update, only 0.65 on
temporal and 0.81 on multi-session (answers are computed, not spans). So gate per question type.
Ideas, in order: (1) verify.py: extract the question's specific entities and check each appears as a whole
phrase in the evidence; missing one → tell Reactor in the notes or abstain, (2) the QA score for single-fact
questions, (3) cite only sessions whose excerpts support the answer (evidence F1), (4) tune on dev without holdout.
Ask the INTEGRATOR for any new dependency (transformers model) via coord/requests/.
```

## INTEGRATOR

```
Your role: INTEGRATOR. You own ask.py, README.md, requirements.txt, .gitignore, AGENTS.md, CLAUDE.md and CI;
reactor/ stays the organisers' kit, unchanged. You are the only one who runs Reactor and holds
REACTOR_ACCESS_KEY (in your shell only, entered as the kit's QUICKSTART shows).
First task: split memsys.py into retrieval.py, dates.py, evidence.py with NO behaviour change, keeping
memsys.py as a re-export so prepare.py, eval_retrieval.py and others keep working; verify with eval_retrieval.py
that numbers are identical; merge it fast and announce it, since three roles are waiting on it.
Then: make the device configurable (env var, default mps), process coord/requests/ in order (dependencies,
Reactor evals one at a time), review and merge PRs (reject ones that touch other roles' areas), and keep a
running score table of main in experiments/integrator/.
Never edit other roles' functions yourself: request it from the owner.
```
