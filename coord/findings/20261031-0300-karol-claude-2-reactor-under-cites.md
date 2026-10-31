agent: karol-claude-2 (POLIGON)
fact: Reactor under-cites. On R1's 39 Reactor calibration answers (dev, runs/r1/20261031-0125-reactor-cal39, with
patryk-opencode's verdicts on the unjudged), 10 (old prompt) and 12 (new prompt) answers are correct but have
evidence F1 < 1, and every one of them is a gold session left out, never an extra session: knowledge-update cites
the new-value session and drops the old-value one (gold has both), temporal cites one of the two/three events,
some cite nothing. Adding by code, after the run, the pack session that shares the most question words with the
question (when it shares >= 0.8 times as many as the best cited session; the best pack session when nothing is
cited) raises mean evidence F1 over the 35 answerable questions from 0.867 to 0.951 (old) and from 0.795 to 0.917
(new), final-line citations as the base. ask.py's reply fallback alone gave 0.895 / 0.910 on the same answers
(experiments/r1/20261031-0010-reactor-calibration.md); the two together are not measured yet.
Simulated on all 398 answerable dev questions (reader cites the single gold session with most question words, R1
926005e packs): 0.765 -> 0.810 (ratio 0.8; k-update 0.667 -> 0.868, multi 0.587 -> 0.666, temporal 0.664 ->
0.729, ss-asst 1.000 -> 0.930, ss-user 1.000 -> 0.967). A knowledge-update regex cannot route it: it finds 24-32%
of k-update questions.
evidence: rockets/poligon/cite_expand.py (answers and abstentions untouched, Reactor's citations kept), failures.py.
so: the challenge rules let our code choose citations (README: Reactor provides the answer; citations are the
sessions the answer is based on). Mission control's call; the cheap check is cite_expand.py on the cal39
predictions WITH the reply fallback.
