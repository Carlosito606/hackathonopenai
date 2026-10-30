# coord/: shared knowledge, one file per record

Work (ideas, tasks, claims, Reactor queue) lives in GitHub Issues: see AGENTS.md section 4. This folder holds
knowledge that every agent should read, as one new file per record so parallel agents never conflict.
`claims/` and `requests/` are from the first version of the rules; new claims and requests go to issues.

## findings/<YYYYMMDD-HHMM>-<agent-id>-<slug>.md
Read the newest 20 at the start of every session. Max ~15 lines.
```
agent: <agent-id>   issue: #<n> (optional)
fact: <one or two sentences: what is true about the data, a metric, a model, or the tooling>
evidence: <command, numbers, dev question ids>
so: <what others should do or avoid because of it>
```

## handoffs/<YYYY-MM-DD>-<agent-id>-<issue#>.md
```
done: ...
not done: ...
learned: <also file a finding if others need it>
next: <the next concrete step>
```
