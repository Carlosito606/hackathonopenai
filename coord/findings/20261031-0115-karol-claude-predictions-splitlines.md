agent: karol-claude
fact: reactor/predictions.py reads --histories (and results) with str.splitlines(), which also splits at U+2028
(and other Unicode line separators) inside chat text. Test histories.jsonl holds U+2028 in 2 of its 15 lines,
dev in 17 of 470, dev-hard in 15 of 505, so `predictions.py ... --histories ../data/test/histories.jsonl` stops
with "Unterminated string" and writes no predictions.
evidence: str.splitlines() on test/histories.jsonl gives 23 pieces for 15 lines, 13 of them valid JSON.
so: never change reactor/; pass a file of session ids in the same field instead (predictions.py reads
"session_id" at any depth):
  python -c "import json,sys;o=open(sys.argv[2],'w',encoding='utf-8');[o.write(json.dumps({'session_id':s['session_id']})+'\n') for l in open(sys.argv[1],encoding='utf-8') for s in json.loads(l)['sessions']]" ../data/test/histories.jsonl ../data/test/session_ids.jsonl
  python reactor/predictions.py results.jsonl --histories ../data/test/session_ids.jsonl --out predictions.jsonl
Checked on dev: predictions written, 0 skipped; the one-liner gives all 3000 test session ids. results.jsonl from
ask.py is safe: json.dumps escapes U+2028 by default.
