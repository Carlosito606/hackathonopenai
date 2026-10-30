# AGENTS.md — rules for every coding agent in this repo

Shared operating manual for all AI coding agents here (Claude Code, Codex, Codex cloud, Cursor, ...), on any
number of accounts. `CLAUDE.md` imports it, so Claude and OpenAI agents follow the same rules. Read it fully
before your first change in a session. If a request conflicts with it, stop and ask your human.

## 1. What we are building

A system for the Memory Retrieval Challenge (https://github.com/RxAI-dev/memory-challenge): answer questions over
long, noisy multi-session chat histories, cite the session ids the answer relies on, and abstain when the history
does not contain the answer. Final answers must come from our Reactor agent, produced by this repo's code.
Scores: answer accuracy (LLM judge), evidence F1 on cited sessions, abstention. README.md describes the pipeline:
`retrieval.py` → `dates.py` → `evidence.py` (re-exported by `memsys.py`) → `prepare.py` (plan with answering
notes) → `ask.py` (Reactor) → `reactor/predictions.py` (submission). Before the split PR is merged, all three
live in `memsys.py`.

Known traps in the data (from our dev analysis; design against them). New ones go to `coord/findings/`:
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

## 2. Areas, leads and agents

Work is split by **area**, not by person. Each area has one human **lead** and any number of agents. Every agent
works on exactly one task at a time.

| Area | Lead | Files | Goal |
|---|---|---|---|
| `retrieval` | <lead> | `retrieval.py`, `eval_retrieval.py` | all gold sessions in the evidence, esp. multi-session and temporal |
| `temporal` | <lead> | `dates.py` | relative dates, value updates (latest wins), durations/counts computed in code |
| `verify` | <lead> | `evidence.py`, `prepare.py` (incl. `GUIDE`), `verify.py` | abstain correctly, choose excerpts, cite the right sessions |
| `integration` | <lead> | `ask.py`, `memsys.py`, `config.py`, `README.md`, `requirements.txt`, `.gitignore`, `.github/`, `AGENTS.md`, `CLAUDE.md`, `experiments/LEADERBOARD.md` | main always runnable; merges; eval protocol; final predictions |
| `analysis` | <lead> | only `coord/findings/` and `experiments/analysis/` (no code in the pipeline) | failure analysis of runs and data, feeding ideas to the other areas |

`reactor/` is the organisers' kit and stays unchanged. Special roles, one person each:
- **Reactor operator** (`<name>`): the only one who runs Reactor (section 5). One per Reactor agent id.
- **Integrator** (`<name>`, lead of `integration`): merges PRs into `main` (section 7).

**Agent id.** Every agent session has an id `<person>-<vendor>[-<n>]` (e.g. `karol-claude-2`, `antek-codex`).
Put it in the issue comment when you take a task, in the PR title (`[karol-claude-2] verify: entity check`) and in
handoffs.

**Inside an area**, several agents may work at once, but never on the same function at the same time. Prefer new
code in a new function or file behind a flag (section 7) over editing an existing function another agent may be
changing. If two tasks must change the same function, the lead sequences them.

Need a change outside your area? Do not make it: open or comment on an issue for that area and tell your human.

## 3. Git rules (hard)

- Never commit to `main` directly, never `push --force` to `main` or someone else's branch, never rewrite
  published history, never delete branches you did not create.
- One task = one issue = one agent = one branch = one PR. Branch: `<area>/<issue#>-<topic>`
  (e.g. `verify/12-entity-check`).
- One working tree per agent session: `git worktree add .worktrees/<area>-<issue#> -b <branch> origin/main`
  (cloud agents are already isolated; just use the branch name).
- Before a PR: `git fetch && git rebase origin/main`, then the checks in section 6. Small PRs (aim < 300 changed
  lines), squash-merge. A function signature used outside your area changes only with the integrator's OK.
- Do not add dependencies yourself: ask on the issue; the integrator edits `requirements.txt`.
- Never commit: data, caches (`*.pkl`), plans/results/predictions (`*.jsonl` outside `reactor/examples/`),
  model weights, `.env`, keys.
- Do not reformat or tidy code you do not own, not even whitespace. Unrelated diffs get the PR rejected.

## 4. Coordination: issues for work, files for knowledge

With many accounts, claims must be visible instantly and atomic. Files on a branch are invisible to others until
merged, so **work is tracked in GitHub Issues**, knowledge in `coord/` files on `main`.

**Issues** (https://github.com/Carlosito606/hackathonopenai/issues), templates in `.github/ISSUE_TEMPLATE/`:
- `idea`: anyone (human or agent) proposes something: hypothesis, which question type and metric it should move,
  dev examples, cost. **Search open issues first**; if it exists, add your evidence as a comment instead.
- `task`: a triaged idea, ready to work on. Only an area lead turns an idea into a task. Do not start work on an
  untriaged idea.
- Labels: `area:<area>`, `type:idea|task|finding|bug`, `needs:reactor`, `status:claimed|blocked`.
- **Claiming:** a task is yours only when its assignee is your human and your agent id is in a comment
  ("claimed by karol-claude-2"). Agents without GitHub access: your human claims it for you. If it is already
  claimed, pick another task.
- **WIP limit:** at most 3 claimed tasks per area at once. Leads triage ideas at least every hour.

**Files on `main`** (one new file per record, so they never conflict):
- `coord/findings/<YYYYMMDD-HHMM>-<agent-id>-<slug>.md`: a fact others should know (a data trap, a metric
  surprise, a dead end and why). Max ~15 lines. **Read the newest 20 findings at the start of every session.**
- `coord/handoffs/<YYYY-MM-DD>-<agent-id>-<issue#>.md`: when you stop: done, not done, learned, next.
- `experiments/<area>/<YYYYMMDD-HHMM>-<agent-id>-<issue#>.md`: results in the format of section 6.
- Findings and handoffs may go to `main` in their own tiny PR, so they are visible before your code PR lands.

## 5. Reactor: one shared, stateful, slow resource

Our Reactor agent takes one dataset history and one question at a time; a `--new-history` from anyone breaks a
run in progress (`history_changed`). Answers take tens of seconds (client timeout 300 s): a full dev run (526
questions) is several hours, a test run (146) one to two hours. Reactor time is the scarcest thing we have.

- **Only the Reactor operator runs `ask.py` against Reactor** or anything else that uses `REACTOR_ACCESS_KEY`.
  Nobody else holds the key. Agents never read, print or store it; the operator enters it at the hidden prompt
  from the kit's QUICKSTART, in a terminal the operator controls.
- If the team has several agent ids, the operator runs one process per agent id, each on different dataset
  histories, in parallel. Never two processes on one agent id.
- **Queue:** issues labelled `needs:reactor`, with branch, commit sha and flags (section 7). The integrator orders
  the queue; the operator runs it one at a time.
- **Budget:** Reactor evaluations use `splits/reactor_mini.txt` (64 stratified dev questions, about half an hour).
  Full dev runs only for the top candidates. The test run is scheduled by the integrator with hours of buffer
  before the deadline; nothing else runs on Reactor then.
- Everyone else tests end-to-end with a local stand-in: `ask.py ... --local http://127.0.0.1:8899` (any
  OpenAI-compatible server), then `score.py` from the challenge repo.

## 6. Experiments that can be compared

With many agents, numbers are useless unless measured the same way:
- **Retrieval:** `eval_retrieval.py` on all of dev minus `splits/dev_holdout.txt`, never a smaller sample.
- **End-to-end local:** the stand-in model named in `experiments/LEADERBOARD.md` (one model for the whole team),
  same questions as above or `splits/reactor_mini.txt`.
- **Always measure the baseline yourself:** `origin/main` at a named sha and your branch, same machine, same
  model, same command. Report both.
- Experiment file format:
  ```
  issue: #12   agent: karol-claude-2   branch: verify/12-entity-check @ <sha>   baseline: main @ <sha>
  command: ...
  split: dev minus holdout (423 q) | reactor_mini (64 q)
  per question type: <metric> baseline → branch (for each type, including the ones that got worse)
  verdict: keep | drop | needs-reactor
  ```
- Checks before every PR: `python -m py_compile` on every `.py` you touched, plus the experiment file.
- Models default to `mps` (Apple Silicon); use the device setting in `config.py` (or a local edit you do not
  commit) on other machines.
- Never tune on `splits/dev_holdout.txt`. Never hard-code answers, ids or gold patterns; never hand-edit
  predictions: predictions must come from running this code, and organisers may re-run it.

## 7. Integration: flags and merge trains

- **New behaviour goes behind a flag** in `config.py` (default off), e.g. `VERIFY_ENTITY_CHECK = False`. Competing
  ideas can then live on `main` together and be compared on Reactor by flags alone, without new branches.
  The integrator turns a flag on by default only when the leaderboard shows it helps.
- **Merge trains:** the integrator merges approved PRs at fixed times (e.g. every hour on the hour), then
  re-runs the retrieval eval on `main` and updates `experiments/LEADERBOARD.md`. A PR that makes `main` worse
  is reverted, not fixed forward.
- **Review:** the area lead approves PRs in their area; the integrator checks cross-area effects and merges.
- Data lives outside the repo (`../data/dev`, `../data/dev-large`, `../data/test`). Dev is LongMemEval with gold.

## 8. Stop and ask your human before

Editing outside your area, changing a function signature others call, adding a dependency, calling Reactor,
deleting or moving files, touching git settings or CI, starting an untriaged idea, or when `main` is broken.

## 9. Done means

A task issue claimed by you; changes only in your area, new behaviour behind a flag; checks pass; an experiment
file with baseline and branch numbers; a finding if you learned something others need; a handoff; a PR to
`main` that names the issue (`Closes #12`).
