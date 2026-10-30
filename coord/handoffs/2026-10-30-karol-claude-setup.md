agent: karol-claude (Karol's first Claude account; switching accounts)

done:
- Dev data analysis: traps written as coord/findings/20261030-*-karol-claude-*.md; scripts and verifier output in
  experiments/analysis/karol-claude/; research with sources in coord/research/2026-10-30-karol-claude-research.md.
- Answerability test: off-the-shelf SQuAD 2.0 model, AUC 0.83 overall, per type in the finding.
- Team rules: PR #1 (roles), #2 (8+ accounts, issues), #3 (fleet of rockets: AGENTS.md, rockets/README.md,
  core/CONTRACT.md, core/permlab.py, coord/CHANNEL.md, prompts/kickoff.md). All merged to main.
- splits/dev_holdout.txt (103 ids, stratified) and splits/reactor_mini.txt (64 ids, stratified, holdout-free).

not done (decisions for humans):
- Which machine builds which rocket (rockets/README.md), mission control, Reactor operator, POLIGON.
- The one team stand-in model (experiments/LEADERBOARD.md).
- Agent channel access: the `agent-kanal` MCP server rejected this session's token (HTTP 401).
- Branch protection on main (currently off); labels from coord/SETUP.md.

learned:
- Dev is lexically easy (BM25 finds the evidence for 83-99% at rank 1); test is built to be harder (near-misses).
- The best retrieval fusion differs by question type, so the final ship needs per-type routing (R8).

next (for Karol's next account):
1. git pull; read AGENTS.md, rockets/README.md, coord/research/..., this handoff, coord/findings/.
2. Pick Karol's rocket (suggested: R7 GUARDIAN, which continues the verifier work here) or mission control.
3. Start one agent per task with the universal prompt in prompts/kickoff.md, one branch and worktree each.
