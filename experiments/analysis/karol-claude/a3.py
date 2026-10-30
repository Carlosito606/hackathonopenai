import sys; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
qbyid={q["question_id"]:q for q in Q}
print("=== ABSTAIN questions (question -> gold explanation)")
for q in Q:
    g=G[q["question_id"]]
    if g["abstain"]: print(f"- [{g['question_type']}] {q['question']}\n    -> {g['answer'][:160]}")
