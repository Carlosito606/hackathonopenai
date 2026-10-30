# The launch pad contract: stages and artifacts every rocket shares

Rockets differ inside; they must agree on these two things, or their parts cannot be combined at the end.
Frozen at kickoff. Changes only through mission control (AGENTS.md section 6), additive whenever possible.

## 1. Four stages

Every rocket is a pipeline of four stages. A rocket may implement any subset and use another rocket's stage (or
the default from R1 HYBRID) for the rest. All values are plain JSON-serialisable dicts and lists.

```python
q = {"question_id", "history_id", "question", "question_date"}          # a questions.jsonl row
h = {"history_id", "sessions": [{"session_id", "date", "turns": [...]}]} # a histories.jsonl row

def retrieve(q, h) -> list[Cand]          # S1: ranked candidates, best first, at most 200
def enrich(q, h, cands) -> list[Cand]     # S2: same list, with facts added to cand["notes"]; may reorder or drop
def assemble(q, h, cands) -> Pack         # S3: what goes to Reactor
def decide(q, h, cands, pack) -> Ask      # S4: the final question text and the abstention policy

Cand = {"session_id": str,               # required: always a real session id of THIS history
        "turn": int | None,              # turn index in that session, None for session/fact/observation units
        "kind": "turn" | "session" | "fact" | "observation" | "event",
        "role": "user" | "assistant" | None,
        "text": str,                     # what was matched (a turn, a fact, an observation)
        "score": float,
        "notes": dict}                   # S2 output, e.g. {"date": "2023-03-04", "superseded_by": "...", "entities": [...]}

Pack = {"evidence": [{"id": session_id, "date": session date as in h, "text": str}],   # the client's format
        "facts": str}                    # computed facts stated to Reactor (dates, durations, counts, latest values)

Ask = {"question": str,                  # text sent with --question (question + facts + answering notes)
       "abstain": bool,                  # True: do not ask Reactor, submit an abstention
       "after": str | None}              # optional post-rule name, e.g. "abstain_if_insufficient"
```

Rules that keep parts swappable:
- `session_id` in every Cand and evidence item is a session id of the question's own history. Citations depend on it.
- Dates come from `h` (this history), never from a cache keyed by session id.
- A stage never calls Reactor. Only `ask.py`, run by the Reactor operator, does.
- A stage is a pure function of its inputs plus files it loads itself (models, indexes it builds under `cache/`).
- A rocket exposes its stages in `rockets/<slug>/rocket.py` as `STAGES = {"retrieve": fn, ...}` (only the ones it has).

## 2. Run artifacts (what makes comparison and permutation possible)

Every run on dev writes a folder `runs/<rocket>/<run_id>/` (`run_id` = `YYYYMMDD-HHMM-<shortsha>`):

| File | One line per question | Size note |
|---|---|---|
| `meta.json` | `{rocket, run_id, git_sha, stages: {retrieve: "r1", ...}, split, reader: "reactor" or stand-in model name, flags}` | one object |
| `candidates.jsonl` | `{"question_id", "ranked": [[session_id, turn_or_null, score], ...]}`, top 100, no text | ~2 MB per dev run |
| `evidence.jsonl` | `{"question_id", "sessions": [ids in the pack, in order], "chars": n}` | small |
| `predictions.jsonl` | the submission format: `{"question_id", "abstain", "answer", "citations"}` | small |
| `details.jsonl` | `score.py ... --details` output | small |

Commit at most three milestone runs per rocket (keep `candidates.jsonl` gzipped if it passes 5 MB). These files
are what `core/permlab.py` combines: retrieval fusions of any subset of rockets, and per-question-type
"which rocket answers best" without spending Reactor time.

Never commit test-split predictions except the final submission, and never commit gold or data files.
