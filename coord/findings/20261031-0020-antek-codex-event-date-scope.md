agent: antek-codex   rocket: R4 TIMELINE   split: dev minus holdout
fact: A date in a retrieved user sentence need not date the event requested by the question. Dated recollection
  of a past tour is not a dated tour; a recently discovered band followed by listening "today" dates listening.
evidence: manual source audit of ten computations in the 23/107 temporal checkpoint: eight supported, two
  unsupported in R4@5c697f6. The unsupported tour-date fact was also supplied in the Reactor smoke at 616bb63.
  Its earlier verification is withdrawn. Both smoke reader results remain 2/2 and evidence F1 .75; a correct
  answer does not establish that a supplied calculation was source-grounded. No full quality comparison yet.
fix: preserve only the coordinated predicate containing the date; reject recollection/discussion as a date for
  its subject. A question about remembering/discussing itself may still compute. 54 synthetic tests pass,
  including decision-vs-action checks. Replaying the ten cached cases removes precisely the two unsupported facts.
so: inspect date scope and event identity separately from calendar arithmetic and automatic scorer matches.
