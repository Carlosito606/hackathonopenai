"""plan.jsonl -> results.jsonl (client.py's lines), one Reactor history per dataset history; resumable.

    python ask.py plan-test.jsonl results-test.jsonl --base-url https://tNN... --agent-id agt_...   # REACTOR_ACCESS_KEY set
    python ask.py plan-dev.jsonl results-dev.jsonl --local http://127.0.0.1:8899                  # stand-in model
    python reactor/predictions.py results-test.jsonl --out predictions.jsonl --abstain-on agent
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

KIT = Path(__file__).resolve().parent / "reactor"
sys.path.insert(0, str(KIT))
import client as kit  # noqa: E402

MAX_CHARS = 30000


def reactor(args, *extra):
    proc = subprocess.run([sys.executable, str(KIT / "client.py"), "--base-url", args.base_url, "--agent-id",
                           args.agent_id, *extra], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"status": "error", "error": (proc.stderr or proc.stdout).strip()[-500:]}


def local(args, p):
    """The stand-in: the client's own message and parsing, answered by an OpenAI-compatible local server."""
    ref = "%08x" % (hash(p["question_id"]) & 0xFFFFFFFF)
    passages = kit.load_evidence(json.dumps(p["evidence"]))
    msg = kit.build_message(p["question"], passages, ref, kit.parse_question_date(p["question_date"]))
    body = json.dumps({"messages": [{"role": "user", "content": msg}], "max_tokens": 600, "temperature": 0}).encode()
    req = urllib.request.Request(args.local + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    t = time.time()
    reply = json.loads(urllib.request.urlopen(req, timeout=600).read())["choices"][0]["message"]["content"]
    finals = kit.final_answers(reply)
    out = {"question_id": p["question_id"], "reply": reply, "latency_s": round(time.time() - t, 1)}
    if ref not in finals:
        return {"status": "timeout", **out}
    cited, unknown = kit.citations(finals[ref], passages)
    return {"status": "answered", "answer": finals[ref], "citations": cited, "unknown_citations": unknown,
            "abstained": bool(kit._INSUFFICIENT.match(finals[ref])), **out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--base-url")
    ap.add_argument("--agent-id")
    ap.add_argument("--local")
    ap.add_argument("--timeout", default="300")
    args = ap.parse_args()
    plan = [json.loads(line) for line in args.plan.read_text(encoding="utf-8").splitlines() if line.strip()]
    done = set()
    if args.out.exists():  # keep answered lines only, so a rerun asks the rest again without duplicate lines
        kept = [line for line in args.out.read_text(encoding="utf-8").splitlines()
                if line.strip() and json.loads(line).get("status") == "answered"]
        args.out.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
        done = {json.loads(line)["question_id"] for line in kept}
    groups = defaultdict(list)
    for p in plan:
        if p["question_id"] not in done:
            groups[p["history_id"]].append(p)
    print(f"{sum(map(len, groups.values()))} question(s) in {len(groups)} histories", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp, args.out.open("a", encoding="utf-8") as out:
        for qs in groups.values():
            if not args.local:
                new = reactor(args, "--new-history")
                if new.get("status") != "history":
                    sys.exit(f"--new-history failed: {new.get('error') or new}")
            for p in qs:
                if args.local:
                    result = local(args, p)
                else:
                    ev = Path(tmp) / "evidence.json"
                    ev.write_text(json.dumps(p["evidence"]), encoding="utf-8")
                    extra = ["--history", new["history_id"], "--question", p["question"], "--question-date",
                             p["question_date"], "--question-id", p["question_id"], "--max-chars", str(MAX_CHARS),
                             "--timeout", args.timeout] + (["--evidence", str(ev)] if p["evidence"] else [])
                    for _ in range(2):  # one more try after a timeout or a closed chat
                        result = reactor(args, *extra)
                        if result.get("status") not in ("timeout", "closed"):
                            break
                result.setdefault("question_id", p["question_id"])
                out.write(json.dumps(result) + "\n")
                out.flush()
                print(f"{p['question_id']}: {result.get('status')} {result.get('answer', '')!s:.70}", file=sys.stderr)


if __name__ == "__main__":
    main()
