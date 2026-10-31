done: memsys.py split into retrieval.py (RETRIEVAL), dates.py (TEMPORAL), evidence.py (VERIFIER build_evidence); memsys.py re-exports every name, so prepare.py and eval_retrieval.py are unchanged.
not done: device still hard-coded to mps (next INTEGRATOR task: env var).
learned: parse_date now lives in dates.py; evidence.py imports _mark, annotate_dates, parse_date from it.
next: new code imports from the module of its role (from retrieval import retrieve, ...).
