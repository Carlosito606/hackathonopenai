# Kickoff prompts

Paste the universal prompt plus your area's block as the FIRST message to your agent (Claude Code, Codex, Codex
cloud, any other). Replace `<...>`. The rules themselves live in AGENTS.md; these prompts only point to them.

---

## Universal prompt (every agent)

```
You are agent <person>-<vendor>[-n] on our Memory Retrieval Challenge team repo
https://github.com/Carlosito606/hackathonopenai. Many agents on other accounts and vendors (Claude, OpenAI)
change this repo at the same time. Your area: <retrieval | temporal | verify | integration | analysis>.
Your task: issue #<n> (if none yet: pick nothing, ask me).
Before doing anything:
1. git fetch. Read AGENTS.md completely (hard rules, they override your habits), README.md, your area's block
   in prompts/kickoff.md, the issue, and the newest 20 files in coord/findings/.
2. Check the issue is claimed for you (assignee is me, your agent id in a comment). If it is claimed by someone
   else, stop and tell me.
3. Branch <area>/<issue#>-<topic> in your own worktree, never main. Edit only your area's files; put new
   behaviour behind a flag in config.py (default off); if config.py does not exist yet, ask me.
4. Never run Reactor, never read, print or store REACTOR_ACCESS_KEY. Test end-to-end with ask.py --local.
5. Never commit data, *.pkl caches, plans/results/predictions, weights or secrets.
6. Measure as AGENTS.md section 6 says: baseline origin/main and your branch, same machine, same command.
7. When you stop: experiment file, a finding if others need to know something, a handoff, a PR "Closes #<n>".
First reply: in 3 lines, what you understood the task to be and how you will measure it. Then wait for my OK.
```

---

## retrieval

```
Area block: retrieval. Files: retrieval.py, eval_retrieval.py (before the split PR: the retrieval functions in
memsys.py). Keep retrieve()'s return format (list of dicts with session, turn, role, text, score): verify and
evidence code depend on it. Weak spots: multi-session and temporal questions with several evidence sessions.
Relevant findings: asides-and-paraphrase, near-miss-abstentions.
```

## temporal

```
Area block: temporal. File: dates.py (before the split PR: the date code in memsys.py). Reactor is weak at
arithmetic: resolve dates, mark superseded values, and compute durations/orderings/counts here, stating the
result in the evidence. Unit-test every date rule on tiny examples.
Relevant findings: relative-dates, in-session-corrections.
```

## verify

```
Area block: verify. Files: evidence.py, prepare.py (incl. GUIDE), verify.py. Decide abstain vs answer, choose
excerpts, cite only sessions that support the answer (evidence F1). Gate any answerability score by question
type. New models are dependencies: ask on the issue.
Relevant findings: near-miss-abstentions, squad2-verifier, asides-and-paraphrase.
```

## integration (integrator)

```
Area block: integration. Files: ask.py, memsys.py, config.py, README.md, requirements.txt, .gitignore, .github/,
AGENTS.md, CLAUDE.md, experiments/LEADERBOARD.md. Keep main runnable end-to-end. Create config.py (flags,
device setting) if missing. Merge trains at fixed times; after each, re-run eval_retrieval.py on main and
update the leaderboard; revert PRs that make main worse. Order the needs:reactor queue. Never edit other areas'
files yourself: open a task for their lead.
```

## analysis

```
Area block: analysis. You change no pipeline code. Inputs: dev data, results-*.jsonl and score.py output the
team shares, experiment files. Find where and why answers fail (per question type: retrieval miss, wrong date,
stale value, near-miss accepted, false abstention, citation miss), and write each pattern as a finding in
coord/findings/ and, where it suggests a fix, an idea issue for the right area with dev question ids as evidence.
Scripts you write go to experiments/analysis/.
```

## Reactor operator (a person, not an agent)

```
Not for an agent. The operator runs Reactor by hand, in their own terminal: key entered at the kit's hidden
prompt, one process per Reactor agent id, issues labelled needs:reactor one at a time, on
splits/reactor_mini.txt unless the integrator says otherwise. Results go to the issue as a comment (accuracy,
abstention, evidence F1 per type from score.py), never the key or the raw environment.
```
