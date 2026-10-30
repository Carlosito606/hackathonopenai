# AGENTS.md — rules for every coding agent in this repo

Shared operating manual for all AI coding agents here (Claude Code, Codex, Codex cloud, Cursor, ...). `CLAUDE.md`
imports it, so Claude and OpenAI agents follow the same rules. Read it fully before your first change in a
session. If a request conflicts with it, stop and ask your human.

## 1. What we are building

A system for the Memory Retrieval Challenge (https://github.com/RxAI-dev/memory-challenge): answer questions over
long, noisy multi-session chat histories, cite the session ids the answer relies on, and abstain when the history
does not contain the answer. Final answers must come from our Reactor agent, produced by this repo's code.
Scores: answer accuracy (LLM judge), evidence F1 on cited sessions, abstention. README.md describes the pipeline:
`memsys.py` (retrieval, dates, evidence) → `prepare.py` (plan with answering notes) → `ask.py` (Reactor) →
`reactor/predictions.py` (submission).

Known traps in the data (from our dev analysis; design against them):
- Unanswerable questions are near-misses: one entity swapped (violin vs guitar, Korea vs Japan, table tennis vs
  tennis, "Software Engineer Manager" vs "Senior Software Engineer") or half of a two-part question missing.
  Similarity alone does not catch them; token/prefix overlap fails too ("Korea" matches "Korean").
- Values change over time and inside one session ("Actually, I need 120 stars, not 300"); the assistant also
  states wrong numbers. The latest user statement wins. Same-day updates need the time of day.
- Relative dates are relative to the SESSION date. The same session id has different dates in different
  histories: never cache dates by session id.
- Facts hide in "By the way ..." asides inside off-topic sessions. Gold sometimes paraphrases ("piece of jewelry"
  answered by "crystal chandelier from my aunt"), so over-strict checks cause false abstentions.
- Test adds near-miss sessions about other people (a cousin's graduation, not the user's).
- A ready SQuAD 2.0 model (roberta-base-squad2) as answerability score: AUC 0.83 overall, 0.95-0.99 on
  single-session-user and knowledge-update, only 0.65 on temporal (answers are computed, not spans).

## 2. Roles and ownership

Four humans, each driving their own agent(s). Each area has one owner; you edit only your role's files/functions.
Everything else is read-only for you.

| Role | Owner | Owns | Goal |
|---|---|---|---|
| **INTEGRATOR** | <name-1> | `ask.py`, `README.md`, `requirements.txt`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, CI; `reactor/` stays the organisers' kit, unchanged | main always runnable end-to-end; the only Reactor runner; final predictions |
| **RETRIEVAL** | <name-2> | in `memsys.py`: `split_text`, `session_chunks`, `tokens`, `Embedder`, `reranker`, `sub_queries`, `retrieve`, `session_ranking`; `eval_retrieval.py` | every gold session in the evidence for multi-session and temporal |
| **TEMPORAL** | <name-3> | in `memsys.py`: date code (`EPOCH` ... `TEMPORAL`, `day_no`, `_mark`, `annotate_dates`) | relative dates, value updates (latest wins), counting/durations computed in code |
| **VERIFIER** | <name-4> | `build_evidence` in `memsys.py`; `prepare.py` (incl. `GUIDE`); new `verify.py` | abstain correctly, choose evidence, cite the right sessions |

`memsys.py` is shared by three roles. **First task of the INTEGRATOR:** split it with no behaviour change into
`retrieval.py`, `dates.py`, `evidence.py`, keeping `memsys.py` as a re-export so imports keep working. Until that
PR is merged, the other roles put new code in new files (e.g. `verify.py`, `dates_kupdate.py`) and keep edits
inside `memsys.py` to their own functions, in small PRs.

Need a change outside your area? Do not make it: write a request (section 4) and tell your human.

## 3. Git rules (hard)

- Never commit to `main` directly, never `push --force` to `main` or someone else's branch, never rewrite
  published history, never delete branches you did not create.
- One branch per task: `<role>/<short-topic>` (e.g. `retrieval/query-split`, `verify/entity-check`).
- One working tree per agent session: `git worktree add .worktrees/<role>-<topic> -b <role>/<topic> origin/main`
  (cloud agents are already isolated; just use the branch name).
- Before a PR: `git fetch && git rebase origin/main`, then the checks in section 6. Small PRs (aim < 300 changed
  lines), one topic, squash-merge. Function signatures used by other roles change only with the INTEGRATOR's OK.
- Do not add dependencies yourself: request them (the INTEGRATOR edits `requirements.txt`).
- Never commit: data, caches (`*.pkl`), plans/results/predictions (`*.jsonl` outside `reactor/examples/`),
  model weights, `.env`, keys.
- Do not reformat or tidy code you do not own, not even whitespace. Unrelated diffs get the PR rejected.

## 4. Coordination without merge conflicts

Every coordination record is its own new file, so parallel agents never edit the same file.

- **Claim before you start:** `coord/claims/<role>-<topic>.md` (owner, branch, goal, status). If an open claim
  covers the same topic, pick another task or ask your human.
- **Requests to another role:** `coord/requests/<from>-to-<to>-<topic>.md`.
- **Handoff when you stop:** `coord/handoffs/<YYYY-MM-DD>-<role>-<topic>.md`: done, not done, learned, next.
- **Experiments:** `experiments/<role>/<YYYYMMDD-HHMM>-<topic>.md` or `.json`: command, git sha, split, metrics
  per question type. Never overwrite an earlier one.
- Edit only your own coord files. Templates: `coord/README.md`.

## 5. Reactor: one shared, stateful resource

Our team has ONE Reactor agent. It takes one history and one question at a time; a `--new-history` from anyone
breaks a run in progress (`history_changed`). Therefore:

- **Only the INTEGRATOR runs `ask.py` against Reactor** or anything else that uses `REACTOR_ACCESS_KEY`. Others
  never hold the key.
- Everyone else tests end-to-end with a local stand-in model: `ask.py ... --local http://127.0.0.1:8899`
  (any OpenAI-compatible server: mlx_lm, llama.cpp, Ollama, vLLM), then `score.py` from the challenge repo.
- For a Reactor evaluation of your branch, write `coord/requests/<role>-to-integrator-eval-<topic>.md` with the
  branch, commit sha, split and question subset. The INTEGRATOR runs the queue one at a time.

## 6. Checks before every PR

- `python -m py_compile memsys.py prepare.py ask.py eval_retrieval.py` (plus any file you added).
- Your metric on dev, without the holdout (`splits/dev_holdout.txt`), per question type, before and after, in an
  experiment file. Retrieval: `eval_retrieval.py`. Answers/abstention: `prepare.py` → `ask.py --local` → `score.py`.
- Models default to `mps` (Apple Silicon). On other machines pass/set `cpu` or `cuda` locally; do not commit
  device changes unless you make them configurable.

## 7. Data and evaluation hygiene

- Data lives outside the repo (`../data/dev`, `../data/dev-large`, `../data/test`). Dev is LongMemEval with gold.
- Never hard-code answers, question ids, or patterns copied from gold; never hand-edit predictions. The rules
  require predictions to come from running this code, and organisers may re-run it.
- Do not tune thresholds or prompts on the holdout ids in `splits/dev_holdout.txt` (103 questions, stratified).
- Report per question type. A change that helps one type and hurts another must say so.

## 8. Stop and ask your human before

Editing outside your area, changing a function signature others call, adding a dependency, calling Reactor,
deleting or moving files, touching git settings or CI, or when `main` is broken.

## 9. Done means

Changes only in your area; checks from section 6 pass; an experiment file with before/after; claim set to
`status: done`; a handoff file; a PR to `main`.
