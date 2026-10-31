"""A/B on Reactor: two plans (e.g. R1 and R3) for the same questions -> one plan where every question is asked once
per arm, each arm in its own Reactor history (so one answer never sees the other), arms alternating per question.
After ask.py, `split` turns the results back into one predictions-ready results file per arm.

    python rockets/r3/ab.py merge ab_plan.jsonl r1=runs/r1/<id>/plan.jsonl r3=runs/r3/<id>/plan.jsonl
    python rockets/r3/ab.py split ab_results.jsonl r1=runs/r1/<id>/results.jsonl r3=runs/r3/<id>/results.jsonl
"""
import json
import sys


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def arms(specs):
    return [s.split("=", 1) for s in specs]


def merge(out, specs):
    plans = [(name, {p["question_id"]: p for p in read(path)}) for name, path in arms(specs)]
    ids = [q for q in plans[0][1] if all(q in p for _, p in plans)]
    with open(out, "w", encoding="utf-8") as f:
        for i, q in enumerate(ids):
            order = plans if i % 2 == 0 else plans[::-1]
            for name, p in order:
                row = dict(p[q], question_id=f"{q}#{name}", history_id=f"{p[q]['history_id']}#{name}")
                f.write(json.dumps(row) + "\n")
    print(f"{len(ids)} questions x {len(plans)} arms -> {out}")


def split(results, specs):
    rows = read(results)
    for name, path in arms(specs):
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                q, _, arm = r["question_id"].rpartition("#")
                if arm == name:
                    f.write(json.dumps(dict(r, question_id=q)) + "\n")
        print(name, sum(r["question_id"].endswith("#" + name) for r in rows), "->", path)


if __name__ == "__main__":
    {"merge": merge, "split": split}[sys.argv[1]](sys.argv[2], sys.argv[3:])
