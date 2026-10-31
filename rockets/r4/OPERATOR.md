# R4 paired Reactor packet

The human already authorized using Reactor when free. This helper prepares reviewable inputs offline and
leaves credential entry and execution with the human operator, as required by AGENTS.md section 5.
It does not reserve Reactor or infer that a previously announced free window is still free.

The current private packet contains all 12 supplied computations from the full 107-question temporal dev
split, holdout excluded. Its 24 selected plans are drawn from 214 plans checked against the frozen local
benchmark. Every computed claim matches an exact supported source audit. Selection never uses gold answers.
This is a computation-subset diagnostic; its scores cannot be presented as full-type temporal accuracy.

Run the helper as a standalone file. `--source-root` chooses the immutable stage implementation; the operator
script is separate so the ongoing local benchmark's worktree stays unchanged.

```bash
python rockets/r4/reactor_window.py prepare \
  --source-root /path/to/frozen-stage-worktree --source-sha FULL_COMMIT_SHA \
  --data /path/to/dev --manifest /path/to/verified-temporal-chunk-export \
  --plan-cache /path/to/frozen-stage-worktree/rockets/r4/cache/candidates \
  --source-audit /path/to/exact-claim-source-audit.json --scorer /path/to/score.py \
  --out /path/to/private-packet
```

Preparation verifies all selected exports, the stage commit and clean code, all cached R1/R4 plans, the
30,000-character message limit, holdout exclusion and every supplied fact's audit. It writes separate R1/R4
plans plus contract metadata, candidates, evidence and computation records. It sends no remote requests.
The packet records hashes of the plans and operator code; changing either requires fresh preparation.

After confirming and announcing an exclusive reservation, the human runs:

```bash
python rockets/r4/reactor_window.py run --prepared /path/to/private-packet \
  --base-url https://YOUR-REACTOR-HOST --agent-id YOUR-AGENT-ID \
  --start 2026-10-31T06:30:00Z --end 2026-10-31T07:30:00Z
```

The dates above are syntax examples, not an announced reservation. A real interactive terminal is required.
The credential is entered through a hidden prompt and passed only to the official client's child environment;
it is not accepted in arguments, read from a credential file or written to an artifact. No key belongs in chat.

The operator alternates arm order by question. Each arm/question calls the source worktree's unchanged
`ask.py` with a single-question plan and a new Reactor history. Thus one arm cannot inherit the other's answer,
and both receive ask.py's existing reply-citation fallback. There is no word-overlap citation expansion.
Completed answers can resume without another question; failed/incomplete results require inspection.
Before starting a question, the helper leaves room for the client's retry and a further timeout buffer.
Interrupts/deadlines stop only that client's process group, including descendants. A timeout is not proof that
the remote task has ended: inspect it before announcing RELEASE or allowing another operator to start.

On completion, `artifacts/{r4,baseline-r1}/` holds generated predictions and official score.py details/tables.
Unjudged answers still need the team's local judge or human review. Raw replies/plans remain private.
Only findings and aggregate diagnostics should be committed for this packet: preserve the three committed
milestone-run limit for the historical smoke and full temporal/multi-session comparisons.
