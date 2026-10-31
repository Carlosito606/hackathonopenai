# Memory Retrieval Challenge: R1 HYBRID (team Vibers)

Finds the few turns of a long chat history that answer a question, packs them with dates computed in code, and
asks Reactor, which writes the answer, cites the sessions, or abstains. Submission: `ship/predictions.jsonl`.

## Pipeline

1. **Retrieval** (`retrieval.py`): every turn is a chunk (long turns are split into ~900-character windows). Each
   chunk is scored by BM25 and by dense embeddings (`BAAI/bge-base-en-v1.5`), fused by reciprocal rank; the top 80
   are reranked by a cross-encoder (`BAAI/bge-reranker-v2-m3`). Two-event questions ("how many days between A and
   B") are also searched for A and B separately. Questions that name a period ("since March", "in August", "two
   weeks ago", resolved against the question date) add the best chunks from sessions inside that period, and
   counting questions spread the pack over more sessions instead of more chunks of the top session.
2. **Evidence** (`evidence.py`): the best chunks up to 18,000 characters, one excerpt per session, oldest first,
   in the client's format (`id` = session id, `date` = session date). An assistant chunk brings the start of the
   user turn before it; every chunk brings the start of the next user turn, where the user answers or corrects.
   The whole message is kept under 29,000 characters (Reactor's server limit is 32,000).
3. **Dates in code** (`dates.py`): for temporal questions every explicit date ("2023-06-10", "June 3rd", "7 May
   2023", "May 3-5") and relative date ("yesterday", "last Friday", "last weekend", "3 days ago", "last month",
   resolved against the session date, across the new year) is tagged `[YYYY-MM-DD, day N]`, so Reactor only
   subtracts two day numbers. Tests: `python tests/test_dates.py`.
4. **Answering notes** (`prepare.py`): appended to the question: near misses (other people's things, plans,
   undone changes) do not count, the most recent conversation wins, one short answer with its `[E#]` labels on the
   last line, `INSUFFICIENT_EVIDENCE` only when nothing states it about the user; counting questions list the items
   first.
5. **Reactor** (`ask.py`): one Reactor history per dataset history, questions one at a time through the kit's
   `client.py` (`--max-chars 30000`), one retry after a timeout; resumable (a rerun asks only unanswered questions).
   When Reactor cites only in its reasoning and not on the final line, the citations are taken from its whole reply.
6. **Submission**: the kit's `predictions.py` with `--abstain-on agent,no-answer`, then
   `rockets/poligon/cite_expand.py --abstentions-only`: where we abstain, cite the pack session sharing the most
   question words. Answers and abstentions do not change; evidence F1 counts answerable questions we abstained on
   (0 without a citation). Expanding the citations of answered questions is not used: it cites near misses
   (`experiments/r1/20261031-0220-cite-expand.md`).

## Run

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
# data from https://github.com/RxAI-dev/memory-challenge/releases into ../data/{dev,test}
# models run on Apple Silicon (mps) by default; elsewhere: export MEMSYS_DEVICE=cpu (or cuda)

python prepare.py ../data/test plan-test.jsonl --cache ../cache/test.pkl         # retrieval -> plan

printf 'Access key: '; read -rs REACTOR_ACCESS_KEY; echo; export REACTOR_ACCESS_KEY
python ask.py plan-test.jsonl results-test.jsonl --base-url https://tNN.api.reactor-hackathon.rxai.dev --agent-id agt_...

# the kit's predictions.py reads --histories with str.splitlines(), which also cuts at U+2028 inside the chats;
# give it a file with the session ids only
python -c "import json,sys;o=open(sys.argv[2],'w',encoding='utf-8');[o.write(json.dumps({'session_id':s['session_id']})+'\n') for l in open(sys.argv[1],encoding='utf-8') for s in json.loads(l)['sessions']]" ../data/test/histories.jsonl ../data/test/session_ids.jsonl
python reactor/predictions.py results-test.jsonl --histories ../data/test/session_ids.jsonl \
    --out predictions-raw.jsonl --abstain-on agent,no-answer
python rockets/poligon/cite_expand.py predictions-raw.jsonl plan-test.jsonl ../data/test/histories.jsonl \
    --out predictions.jsonl --abstentions-only
python experiments/r1/check_predictions.py ../data/test predictions.jsonl
```

Development without Reactor: `ask.py plan-dev.jsonl results-dev.jsonl --local http://127.0.0.1:8899` asks a local
OpenAI-compatible model with the client's own message format (we used `mlx_lm.server --model
mlx-community/Qwen2.5-7B-Instruct-4bit`); `score.py` from the challenge repo scores it. Retrieval only:
`eval_retrieval.py`, `experiments/r1/compare_evidence.py`, `experiments/r1/compare_budget.py`.

`reactor/` is the organisers' participant kit, unchanged.

## Numbers (details and commands in `experiments/`)

| what | result | file |
|---|---|---|
| Reactor, 39 dev questions (no holdout) | answers ~92-95% right after reading score.py's unjudged ones; 0 false abstentions; abstention 3/4; evidence F1 0.910 | `experiments/r1/20261031-0010-reactor-calibration.md` |
| all gold sessions in the pack, dev (398 answerable) | 0.952 | `experiments/r1/20261030-2320-dev-hard.md` |
| same on dev-hard (dev + injected near-miss sessions) | 0.889; multi-session 0.753 | same |
| counting questions on dev-hard after date windows and session diversity | multi-session 0.714 -> 0.914 | `experiments/r1/20261031-0030-budget.md` |
| date expressions tagged in test user turns | 37% -> 67% | `experiments/temporal/20261030-2308-date-coverage.md` |
| independent audit of the test evidence (two GPT agents) | generic failure patterns, acted on in code | `experiments/r1/20261030-2300-gpt-audit-test-evidence.md` |
| final test run on Reactor (31.10, 01:37-05:57 UTC) | 146/146 answered by Reactor, 12 abstentions (8.2%), every answer cited (1.57 sessions per answer; 3 citations taken from the reply), each abstention cited by `cite_expand.py --abstentions-only`, median latency 75 s; `check_predictions.py` passes; no gold for test | `ship/predictions.jsonl`, `experiments/r1/20261031-0600-final-run.md` |

## Reproducing the submission

`ship/predictions.jsonl` (tag `submission`) comes from the code at git tag `final-run-code` (fee061f; the plan was built at bcdc526,
whose `.py` files outside `experiments/` are identical): `git checkout final-run-code`, then the steps under "Run".
`main` moves on after the run (e.g. a wider reranker pool for counting questions); the submission does not use
those changes. The last step, citing abstentions, uses `rockets/poligon/cite_expand.py` at tag `submission`.
`experiments/r1/check_predictions.py` checks the file before submitting.

## Known limitations

- "The most recent conversation wins" can mislead questions about a previous value ("previous", "originally",
  "before") (R3 dead end, `coord/findings/20261031-0105-patryk2-claude-fact-ledger-extraction.md`).
- A conversation that recalls an older event is not that event's date; the answering notes fall back to the
  conversation date when no date is stated (R4 finding).
- Questions whose premise was never mentioned can still get an answer from a near miss (1 of 4 abstention
  questions in the Reactor calibration).
- Facts said in passing inside off-topic sessions can still fall outside the 18,000-character pack (independent
  audit of the test evidence, `experiments/r1/20261030-2300-gpt-audit-test-evidence.md`).

Team process and other rockets: `rockets/README.md`, `AGENTS.md`, `coord/`.
