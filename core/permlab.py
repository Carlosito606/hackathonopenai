"""Permutation lab: compare rockets and their combinations on dev from run artifacts, without Reactor.

  python core/permlab.py retrieval --gold ../data/dev/gold.jsonl r1=runs/r1/<id>/candidates.jsonl r2=runs/r2/...
  python core/permlab.py answers   --gold ../data/dev/gold.jsonl r1=runs/r1/<id>/details.jsonl r3=runs/r3/...

retrieval: per question type, the share of answerable questions with ALL gold sessions in the top k sessions, for
each rocket and for reciprocal-rank fusion of every subset of rockets (best combinations first).
answers: per question type, correct share per rocket, the oracle (any rocket correct), and a per-type router
(best rocket per type) scored honestly by 2-fold cross-validation, plus which pairs complement each other.
The holdout (splits/dev_holdout.txt) is excluded unless --include-holdout. Standard library only.
"""
import argparse
import gzip
import itertools
import json
import random
from collections import defaultdict
from pathlib import Path

HOLDOUT = Path(__file__).resolve().parent.parent / "splits" / "dev_holdout.txt"


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def named(specs):
    """'name=path' arguments to an ordered {name: path}."""
    out = {}
    for s in specs:
        name, _, path = s.partition("=")
        if not path:
            raise SystemExit(f"expected name=path, got {s!r}")
        out[name] = path
    return out


def load_gold(path, include_holdout):
    gold = {g["question_id"]: g for g in read_jsonl(path)}
    if not include_holdout and HOLDOUT.exists():
        for qid in HOLDOUT.read_text().split():
            gold.pop(qid, None)
    return gold


def session_order(ranked):
    """Sessions in order of their first appearance in a ranked candidate list."""
    seen, out = set(), []
    for sid, _turn, _score in ranked:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def rrf(rankings, c=60):
    score = defaultdict(float)
    for r in rankings:
        for i, sid in enumerate(r):
            score[sid] += 1 / (c + i)
    return sorted(score, key=lambda s: -score[s])


SHORT = {"knowledge-update": "k-update", "multi-session": "multi", "single-session-assistant": "ss-asst",
         "single-session-user": "ss-user", "temporal-reasoning": "temporal"}


def table(rows, types):
    width = max(len(name) for name in rows)
    print(f"{'':{width}s}  " + "  ".join(f"{SHORT.get(t, t):>9s}" for t in types))
    for name, vals in rows.items():
        print(f"{name:{width}s}  " + "  ".join(f"{vals.get(t, float('nan')):9.3f}" for t in types))


def retrieval(args):
    gold = load_gold(args.gold, args.include_holdout)
    answerable = {q: g for q, g in gold.items() if not g["abstain"]}
    runs = {}
    for name, path in named(args.runs).items():
        runs[name] = {r["question_id"]: session_order(r["ranked"]) for r in read_jsonl(path)}
    types = sorted({g["question_type"] for g in answerable.values()}) + ["all"]

    def metrics(rank_of):
        hit, n = defaultdict(int), defaultdict(int)
        for qid, g in answerable.items():
            top = set(rank_of(qid)[: args.k])
            ok = set(g["evidence"]) <= top
            for t in (g["question_type"], "all"):
                n[t] += 1
                hit[t] += ok
        return {t: hit[t] / n[t] for t in n}

    rows = {name: metrics(lambda q, r=r: r.get(q, [])) for name, r in runs.items()}
    combos = []
    for size in range(2, len(runs) + 1):
        for names in itertools.combinations(runs, size):
            m = metrics(lambda q, ns=names: rrf([runs[x].get(q, []) for x in ns]))
            combos.append(("+".join(names), m))
    combos.sort(key=lambda c: -c[1]["all"])
    rows.update(dict(combos[: args.top]))
    counts = defaultdict(int)
    for g in answerable.values():
        counts[g["question_type"]] += 1
    print(f"all gold sessions in top {args.k} sessions; answerable questions per type: {dict(counts)}")
    table(rows, types)
    for t in types[:-1]:
        best = max([(n, m) for n, m in combos] + list(rows.items()), key=lambda c: c[1][t])
        print(f"best for {t}: {best[0]} ({best[1][t]:.3f})")


def answers(args):
    gold = load_gold(args.gold, args.include_holdout)
    runs = {}
    for name, path in named(args.runs).items():
        runs[name] = {r["question_id"]: r["answer"] == "correct" for r in read_jsonl(path) if r["question_id"] in gold}
    qids = sorted(gold)
    types = sorted({gold[q]["question_type"] for q in qids})

    def rate(pred, ids):
        return sum(pred(q) for q in ids) / len(ids) if ids else float("nan")

    by_type = {t: [q for q in qids if gold[q]["question_type"] == t] for t in types}
    rows = {name: {t: rate(lambda q, r=r: r.get(q, False), by_type[t]) for t in types} | {"all": rate(
        lambda q, r=r: r.get(q, False), qids)} for name, r in runs.items()}
    rows["oracle (any)"] = {t: rate(lambda q: any(r.get(q) for r in runs.values()), by_type[t]) for t in types}
    rows["oracle (any)"]["all"] = rate(lambda q: any(r.get(q) for r in runs.values()), qids)

    # per-type router, 2-fold cross-validated: pick the best rocket per type on one half, score it on the other
    rnd = random.Random(0)
    shuffled = qids[:]
    rnd.shuffle(shuffled)
    folds = [set(shuffled[::2]), set(shuffled[1::2])]
    correct = defaultdict(int)
    for train, test in (folds, folds[::-1]):
        for t in types:
            tr = [q for q in by_type[t] if q in train]
            pick = max(runs, key=lambda n: rate(lambda q, r=runs[n]: r.get(q, False), tr))
            for q in by_type[t]:
                if q in test:
                    correct[t] += runs[pick].get(q, False)
    rows["router (2-fold CV)"] = {t: correct[t] / len(by_type[t]) for t in types}
    rows["router (2-fold CV)"]["all"] = sum(correct.values()) / len(qids)
    print(f"correct share (score.py 'correct'; unjudged counts as not correct); questions per type: "
          f"{ {t: len(v) for t, v in by_type.items()} }")
    table(rows, types + ["all"])
    print("\npairs: questions only A gets right / only B gets right")
    for a, b in itertools.combinations(runs, 2):
        only_a = sum(runs[a].get(q, False) and not runs[b].get(q, False) for q in qids)
        only_b = sum(runs[b].get(q, False) and not runs[a].get(q, False) for q in qids)
        print(f"  {a} vs {b}: {only_a} / {only_b}")
    print("\nnote: one question is about 1 point on a type with ~100 questions; differences under ~3 points are noise.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["retrieval", "answers"])
    ap.add_argument("--gold", required=True)
    ap.add_argument("--k", type=int, default=10, help="retrieval: top-k sessions")
    ap.add_argument("--top", type=int, default=5, help="retrieval: how many fusion combinations to show")
    ap.add_argument("--include-holdout", action="store_true")
    ap.add_argument("runs", nargs="+", help="name=path pairs")
    args = ap.parse_args()
    (retrieval if args.mode == "retrieval" else answers)(args)


if __name__ == "__main__":
    main()
