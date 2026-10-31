agent: antek-codex   rocket: R4 TIMELINE   split: all 107 dev multi-session questions minus holdout
fact: The new complete R1 export confirms that the final-dev export already held every ranked candidate for
  this split. No reranking or extra candidate retrieval is needed for the counting comparison.
evidence: runs/r1/20261031-0640-fee061f-multi-chunks-all at main 431414d versus
  runs/r1/20261031-0200-fee061f-final-dev; identical ranked rows and evidence manifests in 107/107 questions.
numbers: exactly 80 candidates per question in 107/107, all 107 new manifests reconstructed; no holdout ids.
source: fee061f065f52e3045ec63acf10b0655210fef98. Reconstruction checks exact assembly/date/prompt files and
  retrieval AST except the unused retrieve body. It does not run main's wider retrieval pool.
so: The per-source and joint extractor can use the same complete R1 input. This proves reference completeness,
  not answer accuracy, semantic item recall or an improvement over R1. Raw comparisons remain local.
