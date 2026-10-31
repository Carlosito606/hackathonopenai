agent: karol-claude-2 (POLIGON)
fact: The local judge (rockets/poligon/judge.py, Qwen2.5-7B Q4_K_M, LongMemEval-style prompts) agrees with a
person on 21 of 22 real Reactor answers that score.py left "unjudged" (R1's 39-question calibration on dev, old
and new prompts: 10/11 and 11/11). With the judge, the runs score 0.923 and 0.949 correct; with the human
verdicts 0.949 both. The one disagreement is the borderline yes/no question patryk-opencode flagged: gold "Yes.
(You have a road bike too.)", answer "Road bike"; the person accepted it, the judge did not. Selftest on 490
synthetic cases: 0.951.
evidence: judge.py --human on runs/r1/20261031-0125-reactor-cal39 (predictions, details, verdicts.jsonl).
so: use the judge to score stand-in or Reactor runs on dev without reading every unjudged answer; it is a little
stricter than a person on answers that state the fact instead of the yes/no.
