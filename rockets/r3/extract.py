"""Atomic fact extraction per session with a local LLM (llama.cpp GGUF), cached by session id.

A session id always names the same content, but not the same date (it differs between histories), so the cache
holds only what the text says: {subject, attribute, value, said_by, turn, is_correction, when}. `when` is the raw
time phrase ("last Saturday", "June 3rd"), resolved against the session date of the question's own history at
use time (rocket.py).

    python rockets/r3/extract.py ../data/dev cache/r3/r1_cands.jsonl --top 15 --model ~/models/qwen2.5-3b-instruct-q4_k_m.gguf
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import memsys  # noqa: E402

CACHE = ROOT / "cache" / "r3" / "facts"
USER_CHARS, ASSIST_CHARS, SESSION_CHARS = 1200, 300, 9000

SYSTEM = """You extract personal facts from a chat log, one per line, in the form:
<turn number> | <user or assistant> | <attribute> | <value>
attribute: whose property and what, in a few words. value: copied from the chat, with units.
Facts are things about the user's own life: possessions, purchases, numbers, amounts, counts, durations, prices,
names of people, pets and places, jobs, plans, events, preferences, dates. Include numbers the assistant states about
the user's situation. Skip generic advice, small talk and facts about the world. At most 12 lines, no other text."""

PROMPT = """CHAT LOG:
{chat}

List the user's personal facts from this chat log, one per line: <turn number> | <user or assistant> | <attribute> | <value>"""


def render(session):
    """User turns, and only those assistant turns that state a number (CPU budget: ~3-4x less text)."""
    lines, used = [], 0
    for i, t in enumerate(session["turns"]):
        if t["role"] != "user" and not re.search(r"\d", t["content"][:ASSIST_CHARS]):
            continue
        limit = USER_CHARS if t["role"] == "user" else ASSIST_CHARS
        text = t["content"] if len(t["content"]) <= limit else t["content"][:limit] + " …"
        line = f"[{i}] {t['role']}: {text}"
        if used + len(line) > SESSION_CHARS:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


CORRECTION = re.compile(r"\b(actually|correction|i meant|i misspoke|scratch that|sorry,? (?:it|i)|not \S+,? but)\b", re.I)
WHEN = re.compile(memsys._REL.pattern + "|" + memsys._MD.pattern + "|" + memsys._ISO.pattern, re.I)


def parse(raw, session):
    """`turn | speaker | attribute | value` lines -> facts. Complete lines survive a cut-off output, repeats are
    dropped. is_correction and when come from the source turn's text, not from the model."""
    turns = session["turns"]
    out, seen = [], set()
    for line in raw.splitlines():
        parts = [x.strip() for x in line.strip().strip("-* ").split("|")]
        m = re.match(r"\[?(\d+)\]?$", parts[0]) if parts else None
        if len(parts) < 4 or not m or not parts[3] or parts[3] in ("-", "value"):
            continue
        turn = int(m.group(1))
        if turn >= len(turns):
            continue
        attr = re.sub(r"^(my|the user's|user's)\s+", "", parts[2], flags=re.I)
        key = (attr.lower(), parts[3].lower())
        if key in seen:
            continue
        seen.add(key)
        text = turns[turn]["content"]
        when = WHEN.search(text)
        out.append({"subject": "user", "attribute": attr, "value": parts[3],
                    "said_by": "assistant" if parts[1].lower().startswith("a") else turns[turn]["role"],
                    "turn": turn, "is_correction": bool(CORRECTION.search(text)),
                    "when": when.group(0) if when else ""})
    return out


class Extractor:
    def __init__(self, model_path, threads=8, ctx=4096):
        from llama_cpp import Llama
        self.name = Path(model_path).name
        self.llm = Llama(model_path=str(model_path), n_ctx=ctx, n_threads=threads, verbose=False)

    def __call__(self, session):
        msg = PROMPT.format(chat=render(session))
        r = self.llm.create_chat_completion([{"role": "system", "content": SYSTEM}, {"role": "user", "content": msg}], temperature=0, max_tokens=300,
                                            repeat_penalty=1.15)
        return r["choices"][0]["message"]["content"]


def cached(session_id):
    p = CACHE / f"{session_id}.json"
    return json.loads(p.read_text())["facts"] if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("cands", help="r1_cands.jsonl: sessions to extract are each question's top sessions")
    ap.add_argument("--model", required=True)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--types", help="comma-separated question types to extract for (uses gold.jsonl types, dev only)")
    args = ap.parse_args()
    hist, qs, gold = memsys.load_split(args.split)
    by_q = {q["question_id"]: q for q in qs}
    types = set(args.types.split(",")) if args.types else None
    sessions, order = {}, []
    for line in open(args.cands):
        row = json.loads(line)
        if types and gold[row["question_id"]]["question_type"] not in types:
            continue
        h = hist[by_q[row["question_id"]]["history_id"]]
        byid = {s["session_id"]: s for s in h["sessions"]}
        ranked = memsys.session_ranking([dict(c, score=c["score"]) for c in row["cands"]])[:args.top]
        for rank, sid in enumerate(ranked):
            if sid not in sessions:
                sessions[sid] = byid[sid]
                order.append((rank, sid))
    # best-ranked sessions first, so a partial run already covers every question's top hits
    todo = [sid for _, sid in sorted(order) if cached(sid) is None][:args.limit]
    print(f"{len(sessions)} sessions, {len(todo)} to extract", flush=True)
    ex = Extractor(args.model, args.threads)
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for i, sid in enumerate(todo, 1):
        s = sessions[sid]
        raw = ex(s)
        facts = parse(raw, s)
        (CACHE / f"{sid}.json").write_text(json.dumps({"model": ex.name, "facts": facts, "raw": raw}))
        print(f"{i}/{len(todo)} {sid} {len(facts)} facts {(time.time() - t0) / i:.1f}s/session", flush=True)


if __name__ == "__main__":
    main()
