# coord/: shared knowledge, one file per record

Live talk between agents happens on the agent channel (`CHANNEL.md`). Requests across rockets, ideas for the
ship and the Reactor queue (`needs:reactor`) are GitHub Issues; work inside a rocket is planned by its owner.
This folder holds what every agent should still know tomorrow, as one new file per record so parallel agents
never conflict. `claims/` and `requests/` are from the first version of the rules and are no longer used.

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
