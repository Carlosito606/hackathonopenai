agent: karol-claude-2 (POLIGON)
fact: An LLM category expansion of the question recovers paraphrased gold sessions for BM25 on test-length
histories. The stand-in (Qwen2.5-7B Q4_K_M) lists up to 10 words a person might have used about what the question
asks ("three trips I took" -> "vacations Europe hiking Paris Italy Spain backpacking ..."; told not to answer); BM25
over question + expansion vs the question alone, dev-hard-long, 398 answerable inject questions, all gold sessions
in the top 10 sessions: all 0.809 -> 0.857, multi 0.588 -> 0.701, temporal 0.716 -> 0.755, k-update 0.897 -> 0.948,
single-session unchanged (1.000 / 0.989 -> 1.000). Top 5: all 0.681 -> 0.704, temporal 0.471 -> 0.598, but multi
0.392 -> 0.351 and ss-user 0.961 -> 0.922. RRF of the two rankings sits in between (top 10 all 0.842).
Same on the other splits (all, top 5 / top 10): dev 0.844 / 0.907 -> 0.889 / 0.947 (multi top 5 0.670 -> 0.794,
temporal 0.725 -> 0.784); dev-hard v2 0.714 / 0.852 -> 0.764 / 0.905 (k-update top 5 0.845 -> 0.948, temporal
0.529 -> 0.627). The expansion alone beats RRF everywhere.
evidence: rockets/poligon/expand_probe.py (one short stand-in call per question, cached; BM25 from bm25_run.py).
gbrain's LongMemEval-S report found LLM expansion harmful for its hybrid retriever (93% -> 55%); here it helps
plain BM25 at depth 10. Not measured: R1's dense + reranker pipeline, which already catches part of the paraphrase.
[DEADEND] for R1: fusing that expanded-BM25 session ranking with the final R1 ranking (RRF, c=60) LOSES gold:
all gold in the top 8 sessions dev 0.967 -> 0.962, dev-hard v2 0.920 -> 0.892, dev-hard-long 0.882 -> 0.864; top 12
long 0.920 -> 0.897 (multi 0.856 -> 0.763). R1's dense retrieval and reranker already find what the expansion
adds to BM25, and the fused BM25 list brings in near-misses.
so: LLM category expansion is a cheap fix for a lexical-only retriever, not for R1. If R1 tries it, use it inside
the reranker's query (or as a weighted sub-query), never as an equal RRF partner, and measure on dev-hard-long.
