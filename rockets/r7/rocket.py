"""R7 GUARDIAN: verification first. Retrieval and evidence are R1's; the decide stage checks that every specific
entity of the question occurs in the assembled evidence and abstains (or warns the reader) when one does not."""
import re
import sys
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from memsys import TEMPORAL, build_evidence, session_chunks, sub_queries, tokens  # noqa: E402  (R1, read-only)

import entities  # noqa: E402

# Policies of the decide stage (run.py --policy):
#   none        never abstain before the reader (R1's behaviour)
#   pack        abstain when a proper or quoted entity has a word missing from the evidence pack
#   pack-strict also when such an entity is not one phrase, or a noun phrase's head noun is missing
#   warn        never abstain; tell the reader which entities the excerpts do not mention
POLICIES = ("none", "pack", "pack-strict", "warn")
POLICY = "pack"


def retrieve(q, h):
    """R1's chunking and query split with BM25 only (no dense model or reranker: CPU machine).
    Forked from memsys.retrieve; use run.py --cands to read R1's own candidates.jsonl instead."""
    rows = [{"si": si, "session_id": s["session_id"], "turn": ti, "role": role, "text": text, "kind": "turn"}
            for si, s in enumerate(h["sessions"]) for ti, role, text in session_chunks(s)]
    bm25 = BM25Okapi([tokens(r["text"]) or ["_"] for r in rows])
    queries = sub_queries(q["question"])
    fused = np.zeros(len(rows))
    for k, qq in enumerate(queries):
        scores = bm25.get_scores(tokens(qq))
        ranks = np.empty(len(rows))
        ranks[np.argsort(-scores)] = np.arange(len(rows))
        fused += (1.0 if k == 0 else 0.5) / (60 + ranks)
    top = np.argsort(-fused)[:200]
    return [dict(rows[i], score=float(fused[i]), notes={}) for i in top]


def assemble(q, h, cands):
    """R1's evidence pack (18k chars, date tags for temporal questions)."""
    return {"evidence": build_evidence(h, cands, dates=bool(TEMPORAL.search(q["question"]))), "facts": ""}


def verify(q, pack):
    """Entities of the question with how each occurs in the pack ("phrase", "words" or None)."""
    tag = re.compile(r"\[\d{4}-\d\d-\d\d, day -?\d+\]|\(this conversation: [^)]*\)")
    return entities.check(q["question"], {e["id"]: tag.sub("", e["text"]) for e in pack["evidence"]})


# Questions about what the assistant said paraphrase freely; head-noun checks skip them.
ASSISTANT = re.compile(r"\byou\b|\byour\b|remind me|our (previous )?(conversation|chat)", re.I)


def missing(checked, policy, question=""):
    """Entities that make the decide stage abstain (pack, pack-strict) or warn the reader (warn).
    Content-word runs never count: verbs and frame words are often absent from excerpts (28% false abstention
    when they counted, dev minus holdout)."""
    names = [e for e in checked if e["kind"] in ("proper", "quoted")]
    out = [e for e in names if e["found"] is None]
    if policy in ("pack-strict", "warn"):
        out += [e for e in names if e["found"] == "words" and len(e["words"]) > 1]
        if not ASSISTANT.search(question):
            out += [e for e in checked if e["kind"] == "np" and not e["head_found"]]
    return out


def decide(q, h, cands, pack, policy=None):
    policy = policy or POLICY
    checked = verify(q, pack)
    miss = missing(checked, policy, q["question"]) if policy != "none" else []
    question = q["question"].strip()
    if policy == "warn" and miss:
        names = ", ".join(f'"{e["text"]}"' for e in miss)
        question += (f"\n(Check: the excerpts never mention {names}. If the question depends on it, the answer is "
                     "INSUFFICIENT_EVIDENCE.)")
        return {"question": question, "abstain": False, "after": "abstain_if_insufficient", "checked": checked}
    return {"question": question, "abstain": policy in ("pack", "pack-strict") and bool(miss),
            "after": "abstain_if_insufficient", "checked": checked}


STAGES = {"retrieve": retrieve, "assemble": assemble, "decide": decide}
