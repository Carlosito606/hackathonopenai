[LESSON] R1 HYBRID / pw-claude (verifier) | dev minus holdout, 100 q (25 abstention), stand-in Qwen2.5-7B | 5b5d038
what: the stand-in writes "# FINAL ANSWER: INSUFFICIENT_EVIDENCE" at once, without reasoning, when the evidence is
  long. Asking it to quote the answering sentences first (with labels) and cutting evidence 18k -> 8k chars cuts
  false abstention; near-miss warnings in the GUIDE do the opposite.
numbers: old main 0.52 -> 0.20-0.24 false abstention, acc 0.32 -> 0.43, evidence F1 0.32 -> 0.61;
  on patryk/rakieta R1 0.65 -> 0.45, acc 0.24 -> 0.31, evidence F1 0.16 -> 0.41. Cost: abstention recall
  0.76-0.80 -> 0.52-0.72. A "Check: same thing as the question?" step: false abstention 0.47 -> 0.65 (DEADEND).
also: ask.py's ref = hash(qid) changes per process; PYTHONHASHSEED=0 makes local runs comparable (noise ±0.04).
  Capitalized question names absent from my turns (verify.missing_names) flag 6/25 abstention vs 2/398 answerable
  dev questions; lower-case words or word pairs flag 90-100% of answerable ones (DEADEND).
details: experiments/verify/20261031-0214-abstention.md, 20261031-0330-final-line-labels.md, 20261031-0600-port-rakieta.md
