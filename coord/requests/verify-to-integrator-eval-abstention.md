from: verify   to: integrator
need: (1) Reactor eval of branch verify/abstention (sha in the PR) on dev, the 100 ids of
  experiments/verify/harness.py sample() (all non-holdout abstention + 15 per type), same ids on main for comparison;
  (2) README: evidence is now ~8,000 characters and the answering notes ask to quote first (section 2 and 4).
why: on the local stand-in the branch cuts false abstention 0.52 -> 0.20 but lowers abstention recall 0.76 -> 0.52;
  Reactor decides whether to keep the 8k budget and the quote-first GUIDE.
proposal: python experiments/verify/harness.py plan ../data/dev cands.pkl plan.jsonl --variant final (cands from
  harness.py cands), then ask.py with Reactor; I score with harness.py judge.
status: open
