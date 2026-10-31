agent: karol-claude-2 (POLIGON)
fact: An LLM category expansion of the question recovers paraphrased gold sessions for BM25 on test-length
histories. The stand-in (Qwen2.5-7B Q4_K_M) lists up to 10 words a person might have used about what the question
asks ("three trips I took" -> "vacations Europe hiking Paris Italy Spain backpacking ..."; told not to answer); BM25
over question + expansion vs the question alone, dev-hard-long, 398 answerable inject questions, all gold sessions
in the top 10 sessions: all 0.809 -> 0.857, multi 0.588 -> 0.701, temporal 0.716 -> 0.755, k-update 0.897 -> 0.948,
single-session unchanged (1.000 / 0.989 -> 1.000). Top 5: all 0.681 -> 0.704, temporal 0.471 -> 0.598, but multi
0.392 -> 0.351 and ss-user 0.961 -> 0.922. RRF of the two rankings sits in between (top 10 all 0.842).
evidence: rockets/poligon/expand_probe.py (one short stand-in call per question, cached; BM25 from bm25_run.py).
gbrain's LongMemEval-S report found LLM expansion harmful for its hybrid retriever (93% -> 55%); here it helps
plain BM25 at depth 10. Not measured: R1's dense + reranker pipeline, which already catches part of the paraphrase.
so: worth one R1 experiment after the final: add the expansion as an extra sub-query (retrieval.sub_queries is
already fused by RRF with weight 0.5) and measure on dev-hard-long with r1_run/export_chunks.
