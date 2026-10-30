"""Build dev-hard: dev questions with injected near-miss sessions, plus unanswerable variants (local data only).

    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --ids splits/dev_hard_ids.txt
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --check     # verify an existing build

Every non-holdout dev question gets one "inject" variant: its history plus 3-5 sessions from OTHER histories that
are similar by BM25 (question words plus the evidence sessions' distinctive words), are no dev question's evidence,
do not contain the gold answer, have no first-person user sentence holding most of the question's words, and are
not near-copies of a session already there. They are dated inside the history's span (knowledge-update: before
its first evidence session, so "latest wins" still holds). A seeded, per-type quarter of the answerable ones also gets a "remove" variant: the same injected
history without its evidence sessions (gold: abstain, evidence empty), kept only if the answer no longer occurs.

Deterministic for a given --seed: ids are hashes, randomness comes from per-question seeded generators.
Writes questions.jsonl, histories.jsonl, gold.jsonl (dev format) and manifest.jsonl (source question, variant,
injected sessions; never give it to a pipeline). Standard library only. --exclude takes a manifest-like JSONL of
{"source_qid", "source_session"} pairs to never inject (e.g. distractors a judge found to answer the question).
"""
import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

FMT = "%Y/%m/%d (%a) %H:%M"
TYPES = ("knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
         "temporal-reasoning")
STOP = set("""the a an of to and in on for is it i my me you your was what how many did do does with at that this
from by be are have has as or which when who where were can could would should will just about some any all also
so if but not no than then there their they them we our us he she his her its been being had am more most much
very get got like know think want need make made one two use using really well too into out up down over""".split())
ABSTAIN_ANSWER = "You did not mention this information."

# normalize() and aliases() are copied from the challenge's score.py, so containment means what the scorer means.
NUMBERS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
NUMBERS.update({w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)})
TOKEN = re.compile(r"\d+(?:[.,:/]\d+)*|[^\W\d_]+(?:-[^\W\d_]+)*")
THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})+")
ARTICLES = {"a", "an", "the"}
ALSO_OK = re.compile(r"^(.+?)\.\s+(.+?)\s*\(including the last day\) is also acceptable\.?$", re.I)
OR_PAREN = re.compile(r"^(.+?)\s*\(or (.+?)\)\s*$", re.I)


def normalize(text):
    out = []
    for tok in TOKEN.findall(text.lower()):
        if tok[0].isdigit():
            out.append(tok.replace(",", "") if THOUSANDS.fullmatch(tok) else tok)
        elif all(part in NUMBERS for part in tok.split("-")):
            out.append(str(sum(NUMBERS[part] for part in tok.split("-"))))
        else:
            out.extend(w for w in tok.split("-") if w not in ARTICLES)
    return " ".join(out)


def aliases(answer):
    for pattern in (ALSO_OK, OR_PAREN):
        m = pattern.match(answer.strip())
        if m:
            return [answer, m.group(1), m.group(2)]
    return [answer]


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def wj(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def hid(prefix, *parts):
    return prefix + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def rng_for(seed, *parts):
    return random.Random(int(hashlib.sha1("|".join(map(str, (seed,) + parts)).encode()).hexdigest()[:16], 16))


def words(text):
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 2]


def stext(s, role=None):
    return "\n".join(t["content"] for t in s["turns"] if role is None or t["role"] == role)


def chash(s):
    return hashlib.sha1(json.dumps(s["turns"], ensure_ascii=False).encode()).hexdigest()


def near_key(s):
    """Sessions reused across LongMemEval histories differ in small edits; their opening user words match."""
    return " ".join(words(stext(s, "user"))[:40])


FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'd|my|me|mine|we|our)\b", re.I)


def self_overlap(question, s):
    """Largest share of the question's content words in one first-person user sentence of s: a high value means
    s states a fact about "me" on the question's subject, i.e. it may contradict the gold, not merely be near it."""
    qw = set(words(question))
    if len(qw) < 2:
        return 0.0
    best = 0.0
    for t in s["turns"]:
        if t["role"] != "user":
            continue
        for sent in re.split(r"(?<=[.!?\n])\s+", t["content"]):
            if FIRST_PERSON.search(sent):
                best = max(best, len(qw & set(words(sent))) / len(qw))
    return round(best, 3)


class AnswerMatcher:
    """Whether a text contains the gold answer: whole-phrase match of a normalized alias (what score.py accepts),
    or, for long descriptive answers, most of their distinctive words. Bare numbers are not checkable."""

    def __init__(self, gold):
        self.phrases, self.bags = [], []
        if gold["abstain"]:
            return
        for a in aliases(gold["answer"]) + gold.get("aliases", []):
            n = normalize(a)
            toks = n.split()
            content = [t for t in toks if not t.isdigit() and t not in STOP and len(t) > 2]
            if not content:
                continue  # a bare number or unit: any session with "3" would match, so it cannot be checked
            if len(toks) <= 6:
                self.phrases.append(f" {n} ")
            else:
                self.bags.append(set(t for t in content if len(t) > 3))

    def __call__(self, text):
        n = f" {normalize(text)} "
        if any(p in n for p in self.phrases):
            return True
        have = set(n.split())
        return any(b and len(b & have) / len(b) >= 0.7 for b in self.bags)


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.len = [len(d) for d in docs]
        self.avg = sum(self.len) / max(1, len(docs))
        self.post = defaultdict(list)
        for i, d in enumerate(docs):
            for w, c in Counter(d).items():
                self.post[w].append((i, c))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - len(p) + .5) / (len(p) + .5)) for w, p in self.post.items()}

    def scores(self, qweights):
        sc = defaultdict(float)
        for w, qw in qweights.items():
            idf = self.idf.get(w)
            if idf is None:
                continue
            for i, c in self.post[w]:
                sc[i] += qw * idf * c * (self.k1 + 1) / (c + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return sc


def fmt_date(d):
    return d.strftime(FMT)


def pick_date(rng, lo, hi):
    span = int((hi - lo).total_seconds() // 60)
    return lo + timedelta(minutes=rng.randint(1, span - 1)) if span > 2 else lo + timedelta(minutes=1)


def build(args):
    src = Path(args.src)
    hist = {h["history_id"]: h for h in rj(src / "histories.jsonl")}
    questions = rj(src / "questions.jsonl")
    gold = {g["question_id"]: g for g in rj(src / "gold.jsonl")}
    holdout = set(Path(args.holdout).read_text(encoding="utf-8").split())
    excluded = set()
    if args.exclude:
        excluded = {(r["source_qid"], r["source_session"]) for r in rj(args.exclude)}
    keep = sorted((q for q in questions if q["question_id"] not in holdout), key=lambda q: q["question_id"])
    print(f"{len(keep)} questions after excluding {len(questions) - len(keep)} holdout", flush=True)

    # Pool of distractor sessions: unique by content and never any dev question's evidence. LongMemEval reuses one
    # event in slightly edited evidence sessions of sibling questions ("I recently ran a 5K charity run"), so an
    # evidence session injected elsewhere restates or contradicts that question's fact instead of nearly missing it.
    all_ev = {sid for g in gold.values() for sid in g["evidence"]}
    pool, seen = [], set()
    for h in sorted(hist.values(), key=lambda h: h["history_id"]):
        for s in h["sessions"]:
            c = chash(s)
            if c in seen or s["session_id"] in all_ev:
                continue
            seen.add(c)
            pool.append({"sid": s["session_id"], "hash": c, "near": near_key(s), "s": s})
    print(f"{len(pool)} unique pool sessions", flush=True)
    index = {role: BM25([words(stext(p["s"], role)) for p in pool]) for role in ("user", "assistant")}
    df = {role: {w: len(p) for w, p in index[role].post.items()} for role in index}
    n_pool = len(pool)

    # Which answerable questions also get an unanswerable "remove" variant: a seeded quarter per type.
    by_type = defaultdict(list)
    for q in keep:
        g = gold[q["question_id"]]
        if not g["abstain"] and g["evidence"]:
            by_type[g["question_type"]].append(q["question_id"])
    remove_set = set()
    for t, ids in sorted(by_type.items()):
        r = rng_for(args.seed, "remove", t)
        remove_set |= set(r.sample(ids, round(len(ids) * args.remove_frac)))

    out_q, out_h, out_g, manifest, skipped = [], [], [], [], Counter()
    for q in keep:
        qid, g = q["question_id"], gold[q["question_id"]]
        h = hist[q["history_id"]]
        role = "assistant" if g["question_type"] == "single-session-assistant" else "user"
        match = AnswerMatcher(g)
        ev = set(g["evidence"])
        own_ids = {s["session_id"] for s in h["sessions"]}
        own_hash = {chash(s) for s in h["sessions"]}
        near_seen = {near_key(s) for s in h["sessions"]}

        qw = Counter({w: 2.0 for w in words(q["question"])})
        ans_words = set(words(" ".join(aliases(g["answer"])))) if not g["abstain"] else set()
        ev_words = Counter(w for s in h["sessions"] if s["session_id"] in ev for w in words(stext(s, role)))
        tfidf = {w: c * math.log(n_pool / (1 + df[role].get(w, 0))) for w, c in ev_words.items() if w not in ans_words}
        for w in sorted(tfidf, key=lambda w: (-tfidf[w], w))[:args.ev_terms]:
            qw[w] += 1.0
        scored = index[role].scores(qw)
        ranked = sorted(scored, key=lambda i: (-scored[i], pool[i]["sid"]))

        cands = []
        for i in ranked:
            p = pool[i]
            if p["sid"] in own_ids or p["hash"] in own_hash or p["sid"] in ev or (qid, p["sid"]) in excluded:
                continue
            if p["near"] in near_seen:
                skipped["candidate_near_duplicate"] += 1
                continue
            if match(stext(p["s"])):
                skipped["candidate_contains_answer"] += 1
                continue
            risk = self_overlap(q["question"], p["s"])
            if risk >= args.max_self_overlap:
                skipped["candidate_states_own_fact"] += 1
                continue
            near_seen.add(p["near"])
            cands.append((i, round(scored[i], 3), risk))
            if len(cands) >= args.top:
                break
        rng = rng_for(args.seed, qid)
        k = rng.randint(args.min_inject, args.max_inject)
        chosen = sorted(rng.sample(cands, min(k, len(cands))), key=lambda c: -c[1])

        dates = [datetime.strptime(s["date"], FMT) for s in h["sessions"]]
        lo, hi = min(dates), max(dates)
        if g["question_type"] == "knowledge-update" and ev:
            first_ev = min(datetime.strptime(s["date"], FMT) for s in h["sessions"] if s["session_id"] in ev)
            if first_ev - lo > timedelta(days=1):
                hi = first_ev

        new_hid = hid("h_", args.seed, qid, "inject")
        injected = []
        for i, score, risk in chosen:
            s = pool[i]["s"]
            new_sid = hid("s_", args.seed, new_hid, s["session_id"])
            injected.append({"session_id": new_sid, "date": fmt_date(pick_date(rng, lo, hi)),
                             "turns": [{**t, "turn_id": hid("t_", new_sid, j)} for j, t in enumerate(s["turns"])],
                             "_source": s["session_id"], "_score": score, "_risk": risk})
        sessions = sorted(h["sessions"] + [{k: v for k, v in s.items() if not k.startswith("_")} for s in injected],
                          key=lambda s: datetime.strptime(s["date"], FMT))
        info = [{"session_id": s["session_id"], "source_session": s["_source"], "bm25": s["_score"],
                 "self_overlap": s["_risk"], "date": s["date"]} for s in injected]

        variants = [("inject", sessions, g)]
        if qid in remove_set:
            rest = [s for s in sessions if s["session_id"] not in ev]
            if any(match(stext(s)) for s in rest):
                skipped["remove_answer_still_present"] += 1
            else:
                variants.append(("remove", rest, {**g, "abstain": True, "answer": ABSTAIN_ANSWER, "aliases": [],
                                                  "evidence": []}))
        for variant, sess, vg in variants:
            nq, nh = hid("q_", args.seed, qid, variant), hid("h_", args.seed, qid, variant)
            out_q.append({"question_id": nq, "history_id": nh, "question": q["question"],
                          "question_date": q["question_date"]})
            out_h.append({"history_id": nh, "sessions": sess})
            out_g.append({**vg, "question_id": nq})
            manifest.append({"question_id": nq, "source_qid": qid, "source_history": q["history_id"],
                             "variant": variant, "question_type": g["question_type"], "abstain": vg["abstain"],
                             "removed": sorted(ev) if variant == "remove" else [], "injected": info})

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    order = sorted(range(len(out_q)), key=lambda i: out_q[i]["question_id"])
    wj(out / "questions.jsonl", [out_q[i] for i in order])
    wj(out / "gold.jsonl", [out_g[i] for i in order])
    wj(out / "histories.jsonl", sorted(out_h, key=lambda h: h["history_id"]))
    wj(out / "manifest.jsonl", [manifest[i] for i in order])
    if args.ids:
        Path(args.ids).write_text("".join(out_q[i]["question_id"] + "\n" for i in order), encoding="utf-8",
                                  newline="\n")
    counts = Counter((m["question_type"], m["variant"]) for m in manifest)
    print(f"wrote {len(out_q)} questions to {out}; skipped: {dict(skipped)}")
    for t in TYPES:
        print(f"  {t:26s} inject {counts[t, 'inject']:4d}  remove {counts[t, 'remove']:4d}")


def check(args):
    """Invariants of a build; exits non-zero on the first broken one per kind, prints counts."""
    src, out = Path(args.src), Path(args.out)
    sgold = {g["question_id"]: g for g in rj(src / "gold.jsonl")}
    shist = {h["history_id"]: h for h in rj(src / "histories.jsonl")}
    holdout = set(Path(args.holdout).read_text(encoding="utf-8").split())
    qs, gold = rj(out / "questions.jsonl"), {g["question_id"]: g for g in rj(out / "gold.jsonl")}
    hist = {h["history_id"]: h for h in rj(out / "histories.jsonl")}
    man = {m["question_id"]: m for m in rj(out / "manifest.jsonl")}
    errs = Counter()

    def fail(kind, msg):
        if not errs[kind]:
            print(f"FAIL {kind}: {msg}")
        errs[kind] += 1

    if len({q["question_id"] for q in qs}) != len(qs):
        fail("duplicate_qid", "question ids are not unique")
    n_inj = []
    for q in qs:
        qid, g, m, h = q["question_id"], gold[q["question_id"]], man[q["question_id"]], hist[q["history_id"]]
        sg, sh = sgold[m["source_qid"]], shist[m["source_history"]]
        if m["source_qid"] in holdout:
            fail("holdout", qid)
        sids = [s["session_id"] for s in h["sessions"]]
        if len(set(sids)) != len(sids):
            fail("duplicate_session", qid)
        dates = [datetime.strptime(s["date"], FMT) for s in h["sessions"]]
        if dates != sorted(dates):
            fail("unsorted", qid)
        qd = datetime.strptime(q["question_date"], FMT)
        src_dates = [datetime.strptime(s["date"], FMT) for s in sh["sessions"]]
        inj = {i["session_id"] for i in m["injected"]}
        n_inj.append(len(inj))
        keys = Counter(near_key(s) for s in h["sessions"])
        if any(keys[near_key(s)] > 1 for s in h["sessions"] if s["session_id"] in inj):
            fail("inject_near_duplicate", qid)
        if not args.min_inject <= len(inj) <= args.max_inject:
            fail("inject_count", f"{qid}: {len(inj)}")
        src_ids = {s["session_id"] for s in sh["sessions"]}
        match = AnswerMatcher(sg)
        for s in h["sessions"]:
            if s["session_id"] in inj:
                d = datetime.strptime(s["date"], FMT)
                if not (min(src_dates) <= d <= max(src_dates)) or d > qd:
                    fail("inject_date", f"{qid} {s['session_id']} {s['date']}")
                if s["session_id"] in src_ids or s["session_id"] in sg["evidence"]:
                    fail("inject_is_original", qid)
                if match(stext(s)):
                    fail("inject_contains_answer", f"{qid} {s['session_id']}")
                if self_overlap(q["question"], s) >= args.max_self_overlap:
                    fail("inject_states_own_fact", f"{qid} {s['session_id']}")
            elif s["session_id"] not in src_ids:
                fail("unknown_session", f"{qid} {s['session_id']}")
        if m["variant"] == "inject":
            if g["abstain"] != sg["abstain"] or g["evidence"] != sg["evidence"] or g["answer"] != sg["answer"]:
                fail("inject_gold_changed", qid)
            if set(sids) != src_ids | inj:
                fail("inject_lost_sessions", qid)
        else:
            if not g["abstain"] or g["evidence"]:
                fail("remove_gold", qid)
            if set(sids) & set(sg["evidence"]) or set(sids) != (src_ids - set(sg["evidence"])) | inj:
                fail("remove_sessions", qid)
            if any(match(stext(s)) for s in h["sessions"]):
                fail("remove_answer_present", qid)
        if sg["question_type"] == "knowledge-update" and m["variant"] == "inject" and sg["evidence"]:
            first_ev = min(datetime.strptime(s["date"], FMT) for s in sh["sessions"] if s["session_id"] in sg["evidence"])
            if first_ev - min(src_dates) > timedelta(days=1) and any(
                    datetime.strptime(s["date"], FMT) > first_ev for s in h["sessions"] if s["session_id"] in inj):
                fail("ku_inject_after_evidence", qid)
    all_ev = {sid for g in sgold.values() for sid in g["evidence"]}
    for m in man.values():
        if any(i["source_session"] in all_ev for i in m["injected"]):
            fail("inject_from_evidence", m["question_id"])
    expected = {q["question_id"] for q in rj(src / "questions.jsonl") if q["question_id"] not in holdout}
    if {m["source_qid"] for m in man.values() if m["variant"] == "inject"} != expected:
        fail("coverage", "not every non-holdout dev question has an inject variant")
    print(f"{len(qs)} questions, {Counter(m['variant'] for m in man.values())}, injected per question "
          f"{Counter(n_inj)}, abstain {sum(g['abstain'] for g in gold.values())}")
    if errs:
        raise SystemExit(f"broken invariants: {dict(errs)}")
    print("all invariants hold")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="dev split folder (histories.jsonl, questions.jsonl, gold.jsonl)")
    ap.add_argument("out", help="output folder, e.g. ../data/dev_hard")
    ap.add_argument("--holdout", default=str(Path(__file__).resolve().parents[2] / "splits" / "dev_holdout.txt"))
    ap.add_argument("--ids", help="write the generated question ids here (splits/dev_hard_ids.txt)")
    ap.add_argument("--exclude", help="JSONL of {source_qid, source_session} pairs never to inject")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-inject", type=int, default=3)
    ap.add_argument("--max-inject", type=int, default=5)
    ap.add_argument("--top", type=int, default=10, help="sample the injected sessions from this many best matches")
    ap.add_argument("--ev-terms", type=int, default=15, help="distinctive evidence words added to the query")
    ap.add_argument("--max-self-overlap", type=float, default=0.6,
                    help="drop candidates with a first-person user sentence holding this share of question words")
    ap.add_argument("--remove-frac", type=float, default=0.25)
    ap.add_argument("--check", action="store_true", help="verify an existing build instead of writing one")
    args = ap.parse_args()
    check(args) if args.check else build(args)


if __name__ == "__main__":
    main()
