"""R3 (or the R1 baseline, from the same cached R1 candidates) on a list of dev questions -> runs/<rocket>/<run_id>/
artifacts (core/CONTRACT.md section 2) + plan.jsonl for ask.py.

    python rockets/r3/run.py ../data/dev rockets/r3/m1_questions.txt --r1-cands cache/r3/r1_cands.jsonl --variant r3
    python ask.py runs/r3/<id>/plan.jsonl runs/r3/<id>/results.jsonl --local http://127.0.0.1:8899
    python reactor/predictions.py runs/r3/<id>/results.jsonl --out runs/r3/<id>/predictions.jsonl --abstain-on agent
    python ../memory-challenge/score.py ../data/dev/gold.jsonl runs/r3/<id>/predictions.jsonl --details runs/r3/<id>/details.jsonl
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rocket  # noqa: E402
from rocket import ROOT, memsys, prepare  # noqa: E402


def r1_stages(q, h):
    """R1 exactly as prepare.plan_question, on the cached candidates."""
    cands = rocket._r1(q, h)
    temporal = bool(memsys.TEMPORAL.search(q["question"]))
    evidence = memsys.build_evidence(h, cands, dates=temporal)
    ranked = [[c["session_id"], c["turn"], c["score"]] for c in cands]
    return ranked, evidence, _r1_question(q)


def _r1_question(q):
    temporal = bool(memsys.TEMPORAL.search(q["question"]))
    extra = prepare.DATES.format(today=memsys.day_no(memsys.parse_date(q["question_date"]))) if temporal else ""
    if prepare.COUNTING.search(q["question"]) and not prepare.re.search(r"how many (days|weeks|months|years)",
                                                                        q["question"], prepare.re.I):
        extra += prepare.COUNT
    return q["question"].strip() + "\n" + prepare.GUIDE.format(extra=extra)


def r3_stages(q, h):
    s = rocket.STAGES
    cands = s["enrich"](q, h, s["retrieve"](q, h))
    pack = s["assemble"](q, h, cands)
    ask = s["decide"](q, h, cands, pack)
    ranked = [[c["session_id"], c["turn"], round(c["score"], 6)] for c in cands]
    return ranked, pack["evidence"], ask["question"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("ids")
    ap.add_argument("--r1-cands", required=True)
    ap.add_argument("--variant", choices=["r3", "r1"], default="r3")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--reader", default="stand-in")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    rocket.DEVICE = args.device
    for line in open(args.r1_cands):
        row = json.loads(line)
        rocket.R1_CACHE[row["question_id"]] = row["cands"]
    hist, qs, _ = memsys.load_split(args.split)
    ids = set(Path(args.ids).read_text().split())
    qs = [q for q in qs if q["question_id"] in ids and q["question_id"] in rocket.R1_CACHE]
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                         cwd=ROOT).stdout.strip()
    run_id = f"{datetime.now():%Y%m%d-%H%M}-{sha}{args.tag}"
    out = ROOT / "runs" / args.variant / run_id
    out.mkdir(parents=True, exist_ok=True)
    stages = {k: ("r3" if args.variant == "r3" and k != "retrieve" else "r1") for k in rocket.STAGES}
    if args.variant == "r3":
        stages["retrieve"] = "r3 (r1 turns + fact keys)"
    meta = {"rocket": args.variant, "run_id": run_id, "git_sha": sha, "stages": stages, "split": Path(args.ids).name,
            "reader": args.reader, "flags": {"top_sessions": rocket.TOP_SESSIONS,
                                             "fact_min_score": rocket.FACT_MIN_SCORE, "device": args.device}}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    fn = r3_stages if args.variant == "r3" else r1_stages
    with open(out / "candidates.jsonl", "w") as fc, open(out / "evidence.jsonl", "w") as fe, \
            open(out / "plan.jsonl", "w") as fp:
        for i, q in enumerate(qs, 1):
            ranked, evidence, question = fn(q, hist[q["history_id"]])
            fc.write(json.dumps({"question_id": q["question_id"], "ranked": ranked[:100]}) + "\n")
            fe.write(json.dumps({"question_id": q["question_id"], "sessions": [e["id"] for e in evidence],
                                 "chars": sum(len(e["text"]) for e in evidence)}) + "\n")
            fp.write(json.dumps({"question_id": q["question_id"], "history_id": q["history_id"],
                                 "question_date": q["question_date"], "question": question,
                                 "evidence": evidence}) + "\n")
            if i % 20 == 0:
                print(f"{i}/{len(qs)}", flush=True)
    print(out)


if __name__ == "__main__":
    main()
