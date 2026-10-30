"""Second pass over score.py's "unjudged" answers: a number answer is correct when its numbers equal the gold ones,
or its first number is one of the accepted ones ("7 days. 8 days (including the last day) is also acceptable");
other answers are printed for a human verdict.

    python experiments/temporal/judge.py gold.jsonl predictions.jsonl details.jsonl
"""
import json
import re
import sys

NUM = re.compile(r"\d+(?:\.\d+)?")
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}


def numbers(text):
    text = re.sub(r"\b(" + "|".join(WORDS) + r")\b", lambda m: str(WORDS[m.group(1).lower()]), text, flags=re.I)
    return [float(n) for n in NUM.findall(text)]


def main(gold_path, pred_path, details_path):
    gold = {g["question_id"]: g for g in map(json.loads, open(gold_path))}
    pred = {p["question_id"]: p for p in map(json.loads, open(pred_path))}
    correct = manual = 0
    for d in map(json.loads, open(details_path)):
        if d["answer"] != "unjudged":
            continue
        g, p = gold[d["question_id"]], pred[d["question_id"]]
        gn, pn = numbers(g["answer"]), numbers(p["answer"])
        if gn and pn and len(re.findall(r"[a-z]+", g["answer"].lower())) <= 12:
            ok = pn[0] in gn if "also acceptable" in g["answer"] else pn[:len(gn)] == gn
            correct += ok
            print(f"auto {'OK ' if ok else 'BAD'} {d['question_id']}: {p['answer'][:60]!r} vs {g['answer'][:60]!r}")
        else:
            manual += 1
            print(f"MANUAL {d['question_id']}: {p['answer'][:150]!r}\n       gold: {g['answer'][:150]!r}")
    print(f"auto-correct {correct}, manual {manual}")


if __name__ == "__main__":
    main(*sys.argv[1:])
