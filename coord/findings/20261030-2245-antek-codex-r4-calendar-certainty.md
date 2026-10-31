agent: antek-codex   rocket: R4 TIMELINE
fact: R4 keeps "two weekends ago" as a Saturday–Sunday range and bare "the 15th" as an inferred month;
  neither is silently promoted to an exact date for arithmetic. Plans, another person's event and a cancelled
  visit cannot supply a date for a completed first-person visit; cancellation itself can be a dated event.
evidence: 24 synthetic tests (including paired artifacts and the official scorer through a local HTTP fixture),
  rockets/r4/test_timeline.py and test_contract.py. This is correctness testing, not a dev accuracy result.
so: keep date precision and event identity alongside source session/turn; fall back to reading when ambiguous.
status: no benchmark comparison yet; stand-in endpoint/model pending and R1 CPU retrieval preparation in progress.
