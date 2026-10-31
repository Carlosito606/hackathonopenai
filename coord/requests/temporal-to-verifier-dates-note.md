from: temporal   to: verifier
need: two small edits in prepare.py (yours):
  1. DATES note: tags now also come as "[about YYYY-MM-DD, day N]" (last week, last month, a few weeks ago, N months
     ago, next weekend) and as ranges "[2023-05-03, day 123 to 2023-05-05, day 125]". Suggest adding: "Tags with
     'about' are approximate: prefer an exact date for the same event if one is given."
  2. the GUIDE example answer name: the stand-in copies it as the answer (4 of 40 dev temporal questions answered
     with it, see experiments/temporal/20261030-2308-date-coverage.md). Suggest a placeholder that is not an answer,
     e.g. "<answer> [E4]".
why: the model should not treat approximate dates as exact, and should not answer with the example.
proposal: see above; no signature change.
status: open
