agent: karol-claude
fact: Injected near-miss sessions (POLIGON dev-hard v1) defeat both cheap abstention signals. The entity gate
catches 6 of dev's 25 unanswerable questions on dev but 1 of the same 25 on dev-hard (the injected sessions carry
the missing names). On the evidence-removed variants SQuAD 2.0's best span comes from an injected session in 30 of
32 scored questions, often confidently ("previous occupation" -> "software developer" 5.6, "painting worth" ->
"$250" 10.4). Also: experiments/analysis/karol-claude/verify.py puts the session date before each chunk and SQuAD
then answers "how long / how often" with that date; drop it (rockets/r7/qa.py DATE_PREFIX).
evidence: rockets/r7 runs 20261030-2336-6b9dc3c (dev-hard, milestone-2 code, in git history at aac6aeb) and 20261031-0021/0055-aac6aeb (fixed code),
manifest.jsonl used for analysis only.
so: span confidence cannot tell "my answer" from "someone else's answer"; an abstention signal must check that the
supporting session is about this user, or leave it to the reader. Measure gates on dev-hard, not dev.
