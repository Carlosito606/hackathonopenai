agent: antek-codex   rocket: R4 TIMELINE   branch: r4/order-direction, base dc59bf0
fact: The list-order path always answered in ascending order even for a descending request. A title containing
  latest could also reverse a first-winner question; order in a title could change its output into a list.
change: Parse explicit direction independently of quoted titles and alternative names; reverse the answer list
  when requested, retain ascending source chronology, and decline conflicting explicit directions.
numbers: 99 synthetic tests pass on this branch. For all 107 temporal dev questions minus holdout, named R1
  fee061f manifests reproduce session order/chars; R1 107/107 and R4 107/107 plans are identical to frozen
  42ab798. Computed facts remain 12/107. No extra reader calls or measured answer-accuracy gain.
provenance: diagnostic used the full final-dev export and replay verifier from 5ebc2d2 (R4 PR #24), permitting
  only the unused retrieve-body difference. The source timeline.py hash is
  00c87868135e6ea5a020c1996a2a102d2b8e88eb4835d1dcbe391b99e4a7f582.
so: Test the requested output direction separately from the dates' chronology. A bug fix need not move dev scores.
