agent: karol-claude
fact: 362 of 916 dev evidence sessions use relative time ("today" 146x, "this weekend", "last month", "last week",
"two weeks ago"), relative to the session date. 3517 session ids carry different dates in different histories.
Questions combine two relative dates: "jewelry last Saturday" (asked Thu 03/09) = session Sat 03/04 saying "today".
evidence: regex count over user turns of dev evidence sessions.
so: resolve against Passage/session date of THIS history; never cache dates by session id.
