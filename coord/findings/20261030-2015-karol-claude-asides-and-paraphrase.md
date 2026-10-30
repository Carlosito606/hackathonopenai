agent: karol-claude
fact: 66% of evidence sessions contain an aside marker ("By the way", "Speaking of") vs 30% of other sessions:
facts are slipped into off-topic chats. Gold also paraphrases: "a piece of jewelry last Saturday" is answered by
"a crystal chandelier from my aunt".
evidence: dev, user turns; question "I received a piece of jewelry last Saturday from whom?".
so: index turns/sentences, not whole sessions; an over-strict entity check will abstain on paraphrases, so
calibrate it on dev, do not hard-fail on every missing word.
