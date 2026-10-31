"""R3 FACT-LEDGER: atomic facts extracted per session (extract.py) as extra retrieval keys pointing to their source
turns, and "latest value wins" resolved in code.

retrieve: R1's turn candidates (root memsys.retrieve, or a cached copy) + fact candidates from the facts of R1's top
          sessions, reranked with R1's cross-encoder; the two lists are RRF-fused.
enrich:   each fact gets the date of its session in THIS history, its `when` resolved against that date, and
          `superseded_by` when a later statement of the same attribute exists.
assemble: R1's evidence builder, with the source turns of the kept facts forced in; Pack.facts is the ledger
          ("Latest: X (said <date>, [E#]), earlier: Y (<date>, [E#])").
decide:   the question + ledger + R1's answering notes (prepare.GUIDE).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import memsys  # noqa: E402
import prepare  # noqa: E402

from extract import cached  # noqa: E402

TOP_SESSIONS = 2  # CPU budget on this machine; the milestone asked for 15
FACT_MIN_SCORE = -1.0  # cross-encoder logit; facts below it never reach the ledger
LEDGER_FACTS = 8
DEVICE = "mps"
_emb = None
R1_CACHE = {}  # question_id -> R1 candidates (memsys dicts), filled by run.py


def embedder():
    global _emb
    if _emb is None:
        _emb = memsys.Embedder(ROOT / "cache" / "dev.pkl", device=DEVICE)
    return _emb


def reranker():
    if memsys._reranker is None:
        memsys.reranker(DEVICE)
    return memsys._reranker


def fact_text(f):
    return f"{f['subject']} {f['attribute']}: {f['value']}".strip()


def _r1(q, h):
    if q["question_id"] not in R1_CACHE:
        R1_CACHE[q["question_id"]] = memsys.retrieve(h, q["question"], embedder())
    return R1_CACHE[q["question_id"]]


def retrieve(q, h):
    r1 = _r1(q, h)
    turns = [{"session_id": c["session_id"], "turn": c["turn"], "kind": "turn", "role": c["role"], "text": c["text"],
              "score": c["score"], "notes": {}} for c in r1]
    facts = []
    for sid in memsys.session_ranking(r1)[:TOP_SESSIONS]:
        for f in cached(sid) or []:
            facts.append({"session_id": sid, "turn": f["turn"], "kind": "fact", "role": f["said_by"],
                          "text": fact_text(f), "score": 0.0, "notes": {"fact": f}})
    if facts:
        raw = reranker().predict([(q["question"], c["text"]) for c in facts], batch_size=64)
        for c, s in zip(facts, raw):
            c["score"] = float(s)
        facts.sort(key=lambda c: -c["score"])
    fused = {}
    for ranked in (turns, facts):
        for i, c in enumerate(ranked):
            fused[id(c)] = fused.get(id(c), 0.0) + 1 / (60 + i)
    out = sorted(turns + facts, key=lambda c: -fused[id(c)])
    for c in out:
        c["notes"]["own_score"] = c["score"]
        c["score"] = fused[id(c)]
    return out[:200]


def _key(f):
    return set(memsys.tokens(f"{f['subject']} {f['attribute']}")) - {"user"}


def enrich(q, h, cands):
    dates = {s["session_id"]: s["date"] for s in h["sessions"]}
    order = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
    facts = [c for c in cands if c["kind"] == "fact"]
    for c in facts:
        f, sd = c["notes"]["fact"], memsys.parse_date(dates[c["session_id"]])
        c["notes"]["date"] = f"{sd:%Y-%m-%d}"
        c["notes"]["pos"] = (memsys.day_no(sd), order[c["session_id"]], f["turn"] if f["turn"] is not None else 99)
        if f["when"]:
            tagged = memsys.annotate_dates(f["when"], sd)
            m = re.search(r"\[(\d{4}-\d\d-\d\d), day", tagged)
            if m:
                c["notes"]["happened"] = m.group(1)
    relevant = [c for c in facts if c["notes"]["own_score"] >= FACT_MIN_SCORE]
    for c in relevant:
        k = _key(c["notes"]["fact"])
        for o in relevant:
            if o is c or not k:
                continue
            ko = _key(o["notes"]["fact"])
            same = len(k & ko) / len(k | ko) >= 0.5 if ko else False
            if same and o["notes"]["pos"] > c["notes"]["pos"] and o["role"] == "user" \
                    and o["notes"]["fact"]["value"].lower() != c["notes"]["fact"]["value"].lower():
                c["notes"]["superseded_by"] = o["notes"]["fact"]["value"]
                break
    return cands


def ledger_facts(cands):
    facts = [c for c in cands if c["kind"] == "fact" and c["notes"]["own_score"] >= FACT_MIN_SCORE]
    facts.sort(key=lambda c: -c["notes"]["own_score"])
    return facts[:LEDGER_FACTS]


def assemble(q, h, cands):
    kept = ledger_facts(cands)
    sidx = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
    forced = []
    for c in kept:
        t = c["notes"]["fact"]["turn"]
        if t is not None:
            text = h["sessions"][sidx[c["session_id"]]]["turns"][t]["content"]
            forced.append({"si": sidx[c["session_id"]], "session_id": c["session_id"], "turn": t, "role": c["role"],
                           "text": memsys.split_text(text)[0], "score": 100.0})
    r1 = [{"si": sidx[c["session_id"]], "session_id": c["session_id"], "turn": c["turn"], "role": c["role"],
           "text": c["text"], "score": c["notes"]["own_score"]} for c in cands if c["kind"] == "turn"]
    temporal = bool(memsys.TEMPORAL.search(q["question"]))
    evidence = memsys.build_evidence(h, forced + r1, dates=temporal)
    label = {e["id"]: f"E{i}" for i, e in enumerate(evidence, 1)}
    return {"evidence": evidence, "facts": render_ledger(kept, label)}


def render_ledger(kept, label):
    groups = []
    for c in sorted(kept, key=lambda c: c["notes"]["pos"]):
        k = _key(c["notes"]["fact"])
        for g in groups:
            gk = g["key"]
            if k and gk and len(k & gk) / len(k | gk) >= 0.5:
                g["items"].append(c)
                break
        else:
            groups.append({"key": k, "items": [c]})
    lines = []
    for g in groups:
        items = g["items"]

        def say(c):
            f = c["notes"]["fact"]
            bits = [f"said {c['notes']['date']}"]
            if c["notes"].get("happened"):
                bits.append(f"happened {c['notes']['happened']}")
            if f["said_by"] == "assistant":
                bits.append("by the assistant")
            if f["is_correction"]:
                bits.append("a correction")
            if c["session_id"] in label:
                bits.append(f"[{label[c['session_id']]}]")
            return f"{f['value']} ({', '.join(bits)})"

        users = [c for c in items if c["role"] == "user"] or items
        latest = users[-1]
        head = items[0]["notes"]["fact"]
        earlier = [c for c in items if c is not latest]
        if not earlier:  # one value seen: the extractor may have missed a newer one, so claim nothing about recency
            lines.append(f"- {head['subject']} / {head['attribute']}: {say(latest)}")
            continue
        lines.append(f"- {head['subject']} / {head['attribute']}: Latest: {say(latest)}; earlier: "
                     + "; ".join(say(c) for c in reversed(earlier)))
    return "\n".join(lines)


NOTE = """
(Facts extracted automatically from my chats; they can be incomplete. Where a line has "Latest", the value changed and my latest statement wins. The excerpts are the source: check every fact against them, prefer a newer excerpt that the facts miss, and cite the excerpts.)
{facts}"""


def decide(q, h, cands, pack):
    temporal = bool(memsys.TEMPORAL.search(q["question"]))
    extra = prepare.DATES.format(today=memsys.day_no(memsys.parse_date(q["question_date"]))) if temporal else ""
    if prepare.COUNTING.search(q["question"]) and not re.search(r"how many (days|weeks|months|years)",
                                                                q["question"], re.I):
        extra += prepare.COUNT
    text = q["question"].strip()
    if pack["facts"]:
        text += "\n" + NOTE.format(facts=pack["facts"])
    return {"question": text + "\n" + prepare.GUIDE.format(extra=extra), "abstain": False, "after": None}


STAGES = {"retrieve": retrieve, "enrich": enrich, "assemble": assemble, "decide": decide}
