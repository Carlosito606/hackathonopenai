"""Give every abstention the top sessions of a retriever's ranking as citations.

    python rockets/r7/cite_on_abstain.py predictions.jsonl candidates.jsonl predictions_cited.jsonl [--k 2]

Evidence F1 is scored on every answerable question, abstained or not, and not on unanswerable ones (challenge
README, score.py), so an abstention with empty citations scores 0 when the question was answerable and nothing is
lost by citing when it was not. With R1's ranking the top 2 sessions give evidence F1 0.787 on dev's answerable
questions and 0.616 on dev-hard v1 (BM25: 0.732, 0.544). Answers and abstention flags are copied unchanged; only
abstentions with no citations get them. candidates.jsonl is a run artifact (core/CONTRACT.md section 2).
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("candidates")
    ap.add_argument("out")
    ap.add_argument("--k", type=int, default=2)
    args = ap.parse_args()
    top = {}
    with open(args.candidates, encoding="utf-8") as f:
        for c in map(json.loads, f):
            order = []
            for sid, *_ in c["ranked"]:
                if sid not in order:
                    order.append(sid)
                if len(order) == args.k:
                    break
            top[c["question_id"]] = order
    cited = missing = 0
    with open(args.predictions, encoding="utf-8") as f, open(args.out, "w", encoding="utf-8") as out:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            if p["abstain"] and not p["citations"]:
                if p["question_id"] in top:
                    p = {**p, "citations": top[p["question_id"]]}
                    cited += 1
                else:
                    missing += 1
            out.write(json.dumps(p) + "\n")
    print(f"{cited} abstentions given citations, {missing} abstentions without a ranking")


if __name__ == "__main__":
    main()
