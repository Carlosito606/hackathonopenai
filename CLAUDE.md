@AGENTS.md

## Claude Code specifics

- Work in a git worktree, never in the main checkout another agent may be using (`claude --worktree` or
  `git worktree add .worktrees/<role>-<topic> -b <role>/<topic> origin/main`).
- Your role is given in your first message. If it is not, ask before editing anything.
- Do not run Reactor or ask for its key unless your role is INTEGRATOR.
