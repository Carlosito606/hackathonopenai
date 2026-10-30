# Dev data analysis and answerability test (karol-claude, 2026-10-30)

Scripts behind the findings in `coord/findings/20261030-*-karol-claude-*.md` and the research notes in
`coord/research/2026-10-30-karol-claude-research.md`. Standard library unless noted. Run from the folder that
holds the dev split, passing the split dir and this folder:

```sh
cd ../data                                   # contains dev/histories.jsonl, questions.jsonl, gold.jsonl
S=../hackathonopenai/experiments/analysis/karol-claude
python -I $S/a1.py dev $S    # sizes, types, evidence counts, session reuse across histories
python -I $S/a2.py dev $S    # BM25 rank of gold sessions per type (all turns vs user turns)
python -I $S/a3.py dev $S    # all 30 unanswerable questions with gold explanations
python -I $S/a4.py dev $S    # knowledge-update gaps, temporal phrasing, question vs session dates
python -I $S/a5.py dev $S    # uncued rephrasings, filler style, relative-time words in evidence
python -I $S/a7.py dev $S    # evidence vs distractor snippets, aside and correction markers
python -I $S/a8.py dev $S    # evidence text of paraphrased questions
python -I $S/mkruns.py dev $S <out_dir>   # smoke-test runs (3 BM25 variants) in the core/CONTRACT.md format
```

`verify.py` (needs `torch` and `transformers`; on Windows with an old VC++ runtime use `torch==2.6.0`):
BM25 top-8 turn chunks per question (no gold used), scored by `deepset/roberta-base-squad2` (best span minus
no-answer) and by lexical coverage; about 11 minutes on CPU for 526 questions. `eval_verify.py verify_rows.json`
prints AUC per method and type and every unanswerable question's scores. The saved output is
`verify_rows.json.gz` (gunzip first).

Dev was built with the challenge's `convert_longmemeval.py` from `longmemeval_s_cleaned.json` (salt `dev`), so
question ids match the released dev split and `splits/*.txt`.
