# coord/: coordination as one file per record

Nobody edits a shared list, so parallel agents never conflict here. Copy a template, fill it, commit it on your
task branch (or a tiny `coord/<role>-<topic>` branch if you need it on main fast).

## claims/<role>-<topic>.md
```
owner: <human> (<agent: claude|codex|...>)
branch: <role>/<topic>
status: in-progress | blocked | done | dropped
goal: <one sentence, which metric/question type it should move>
expected: <time>
```

## requests/<from>-to-<to>-<topic>.md
```
from: <role>   to: <role>
need: <what, e.g. a new field on Candidate, a dependency, a Reactor eval of branch X at sha Y on split Z>
why: <one sentence>
proposal: <signature / snippet>
status: open | accepted | rejected | done
```

## handoffs/<YYYY-MM-DD>-<role>-<topic>.md
```
done: ...
not done: ...
learned: <what surprised you in the data or the metrics>
next: <the next concrete step>
```
