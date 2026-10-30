"""Parser diagnostic over all user turns, NOT R1 retrieval or a reader benchmark.

python -m rockets.r4.diagnose --data /path/dev --scorer /path/score.py
Output is ignored cache; it must not be presented as end-to-end answer accuracy.
"""
import argparse
import importlib.util
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .rocket import ROOT
from .timeline import compute, events


def lines(path):
    with path.open(encoding='utf-8') as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--scorer', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'rockets/r4/cache/all-history-diagnostic.json')
    args = parser.parse_args()
    holdout = set((ROOT / 'splits/dev_holdout.txt').read_text().split())
    gold = {g['question_id']: g for g in lines(args.data / 'gold.jsonl') if g['question_id'] not in holdout and
            g['question_type'] == 'temporal-reasoning'}
    by_history = defaultdict(list)
    for q in lines(args.data / 'questions.jsonl'):
        if q['question_id'] in gold:
            by_history[q['history_id']].append(q)
    spec = importlib.util.spec_from_file_location('official_score', args.scorer)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    counts, details = Counter(), []
    for h in lines(args.data / 'histories.jsonl'):
        if h['history_id'] not in by_history:
            continue
        pool = []
        for s in h['sessions']:
            for index, turn in enumerate(s['turns']):
                if turn['role'] == 'user':
                    pool.extend(events(turn['content'], s['date'], s['session_id'], index, 'user'))
        for q in by_history[h['history_id']]:
            result = compute(q['question'], q['question_date'], pool)
            counts['questions'] += 1
            counts['computed'] += result['computed']
            if result['computed']:
                detail = scorer.score_question({'answer': result['answer'], 'abstain': False,
                                                'citations': result['sources']}, gold[q['question_id']])
                counts['scorer_' + detail['answer']] += 1
                details.append({'question_id': q['question_id'], **result, 'score': detail})
    report = {'scope': 'all user turns; NOT R1 retrieval, NOT a reader benchmark',
              'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'counts': dict(counts), 'details': details,
              'caution': 'Automatic partial matches and unjudged answers do not establish fact correctness.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'details'}, indent=2))


if __name__ == '__main__':
    main()
