agent: patryk-claude (retrieval)
fact: [DEADEND] Adding sentence-level BM25 (chunk scored by its best sentence) as a third RRF list lowers "all gold
sessions in the pack" on dev minus holdout (150 q): multi-session 0.939 -> 0.848, temporal 0.919 -> 0.892, others
unchanged at 1.000.
evidence: experiments/retrieval/20261031-0045-sentence-bm25.md
so: for asides, do not give sentence BM25 a full fusion vote; if anything, use it only to add a few extra
candidates for the reranker, never to reorder the pool.
