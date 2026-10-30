done: dates.py annotate_dates rewritten as one pass over all patterns (longest match wins), same signature and
  exported names. New: last/this/next/this past weekend, N weekends ago; on/by/until/before/due/next/this + weekday
  (past or future from the tense of the sentence); "Wednesday last week"; a couple of / a few days/weeks ago,
  N months/years ago, last/next week/month/year (tagged "about"); last night, the day before yesterday; ranges
  "May 3-5", "the 20th to the 27th of April"; "on 3/22"; "the 5th of last month"; "on the 10th" when the sentence
  names the month ("In March ..."); dates without a year pick the year by tense (fixes the new-year wrap).
  TEMPORAL also routes "last Saturday/week/month", "most recently", "who ... first ... or ...".
  tests/test_dates.py (python tests/test_dates.py), experiments/temporal/coverage.py, judge.py, reannotate.py.
  Coverage of date phrases: dev temporal gold sessions 57% -> 86%, test 37% -> 67%.
not done: holidays (Black Friday, Easter, Thanksgiving); "this week/month"; bare weekdays without a preposition;
  "on the 15th" without a month in the sentence; durations ("for 3 days") and event-relative dates ("two days
  after the party"). No Reactor evaluation: the 7B stand-in is too noisy (50% false abstention) to see the effect.
learned: in LongMemEval dev most events are "today" in their session, so the session date tag does most of the
  work; test states explicit dates ("on 2023-06-10", "23 April 2023") that were already tagged. The stand-in
  answers "Sombra" (the GUIDE example) 4/40 times: request to VERIFIER filed.
next: INTEGRATOR: a Reactor run of temporal questions (reactor_mini) before/after this branch. TEMPORAL: compute
  "How many days between A and B" in code when both events get a tag (pair the two events from the question
  with the tagged sentences) and give the model the number.
