# Memory Retrieval Challenge: retrieval + Reactor

Finds the few turns of a long chat history that answer a question, and asks Reactor with them.

1. **Retrieval** (`memsys.py`): every turn is a chunk (long turns are split into ~900-character windows). Each chunk
   is scored by BM25 and by dense embeddings (`BAAI/bge-base-en-v1.5`), fused by reciprocal rank, and the top 80 are
   reranked by a cross-encoder (`BAAI/bge-reranker-v2-m3`). Two-event questions ("how many days between A and B")
   are also searched for A and B separately.
2. **Evidence** (`build_evidence`): the best chunks up to ~18,000 characters, one excerpt per session, oldest
   first, in the client's format (`id` = session id, `date` = session date). An assistant chunk brings the start of
   the user turn before it.
3. **Date arithmetic in code**: for temporal questions every explicit date ("2023-06-10", "June 3rd", "7 May
   2023") and relative date ("yesterday", "last Friday", "3 days ago", resolved against the session date) is tagged
   `[YYYY-MM-DD, day N]`, so Reactor only subtracts two day numbers.
4. **Answering notes** (`prepare.py`): appended to the question: near misses, latest mention wins, one short answer
   with its `[E#]` labels, `INSUFFICIENT_EVIDENCE` only when nothing states the answer; counting questions list
   items first.
5. **Reactor** (`ask.py`): one Reactor history per dataset history, questions one at a time through the kit's
   `client.py` (`--max-chars 30000`, server limit 32,000), one retry after a timeout; resumable.
6. **Submission**: the kit's `predictions.py` with `--abstain-on agent`.

## Run

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
# data from https://github.com/RxAI-dev/memory-challenge/releases into ../data/{dev,test}

python eval_retrieval.py ../data/dev ../cache/dev.pkl 150                       # session recall on dev
python prepare.py ../data/test plan-test.jsonl --cache ../cache/test.pkl         # retrieval -> plan

printf 'Access key: '; read -rs REACTOR_ACCESS_KEY; echo; export REACTOR_ACCESS_KEY
python ask.py plan-test.jsonl results-test.jsonl --base-url https://tNN.api.reactor-hackathon.rxai.dev --agent-id agt_...
python reactor/predictions.py results-test.jsonl --out predictions.jsonl --abstain-on agent
```

Dev without a Reactor key: `ask.py plan-dev.jsonl results-dev.jsonl --local http://127.0.0.1:8899` asks a local
OpenAI-compatible model (e.g. `mlx_lm.server --model mlx-community/Qwen2.5-7B-Instruct-4bit --port 8899`) with the
client's own message format, then `score.py` from the challenge repo scores it.

Models run on Apple Silicon (`mps`) by default; elsewhere set `MEMSYS_DEVICE=cpu` (or `cuda`).

`predictions.py` is run without `--histories`: the kit reads histories.jsonl with `str.splitlines()`, which also
splits on Unicode line separators inside the conversations, and fails on both dev and test files. Our citations
are session ids taken from histories.jsonl, so the check it skips is not needed.

`reactor/` is the organizers' participant kit, unchanged.

## Dev retrieval (150 answerable dev questions, 50 sessions per history)

| | R@1 | R@3 | R@5 | gold sessions in evidence |
|---|---|---|---|---|
| BM25 + dense | 0.643 | 0.954 | 0.965 | 0.980 |
| + reranker | 0.673 | 0.956 | 0.982 | 0.988 |
