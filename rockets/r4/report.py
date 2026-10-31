"""Audit a partial or complete R4 run, clearly separating coverage from answer accuracy."""
import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

from .run import ROOT, rows, write


def computation_digest(item):
    claim = {key: item[key] for key in ['facts', 'answer', 'sources']}
    return hashlib.sha256(json.dumps(claim, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_verdict(item, reviews):
    # A review applies to the actual claims and sources, never to a question id
    # alone: later retrieval or parsing can produce a different computation.
    digest = computation_digest(item)
    matches = {r['verdict'] for r in reviews if r['question_id'] == item['question_id'] and
               r['claim_sha256'] == digest}
    if not matches:
        return 'unreviewed'
    if len(matches) != 1 or not matches <= {'supported', 'unsupported'}:
        raise ValueError('invalid or conflicting source-audit verdicts')
    return matches.pop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--scorer', required=True, type=Path)
    parser.add_argument('--source-audit', type=Path, help='manual reviews bound to exact computation hashes; never inference input')
    args = parser.parse_args()
    meta = json.loads((args.run / 'meta.json').read_text())
    holdout = set((ROOT / 'splits/dev_holdout.txt').read_text().split())
    types = set(meta['question_types'])
    gold = {g['question_id']: g for g in rows(args.data / 'gold.jsonl') if g['question_id'] not in holdout and
            ('all' in types or g['question_type'] in types)}
    spec = importlib.util.spec_from_file_location('official_score', args.scorer)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    metrics = defaultdict(Counter)
    for g in gold.values():
        metrics[g['question_type']]['expected_questions'] += 1
    for name in ['r4', 'r1']:
        folder = args.run if name == 'r4' else args.run / 'baseline-r1'
        if not (folder / 'evidence.jsonl').exists():
            continue
        for item in rows(folder / 'evidence.jsonl'):
            g = gold[item['question_id']]
            m = metrics[g['question_type']]
            m[name + '_processed'] += 1
            if not g['abstain']:
                m[name + '_answerable'] += 1
                m[name + '_all_gold_in_pack'] += set(g['evidence']) <= set(item['sessions'])
        if (folder / 'details.jsonl').exists():
            for item in rows(folder / 'details.jsonl'):
                metrics[gold[item['question_id']]['question_type']][name + '_correct'] += item['answer'] == 'correct'
                metrics[gold[item['question_id']]['question_type']][name + '_unjudged'] += item['answer'] == 'unjudged'
    computed_details = []
    reviews = json.loads(args.source_audit.read_text())['reviews'] if args.source_audit else []
    if (args.run / 'computations.jsonl').exists():
        for item in rows(args.run / 'computations.jsonl'):
            if not item['computed']:
                continue
            g = gold[item['question_id']]
            m = metrics[g['question_type']]
            m['computed'] += 1
            if 'answer' not in item:
                m['computation_audit_missing'] += 1
                continue
            m['computed_source_' + source_verdict(item, reviews)] += 1
            detail = scorer.score_question({'answer': item['answer'], 'abstain': False, 'citations': item['sources']}, g)
            m['computed_scorer_matched'] += detail['answer'] == 'correct'
            m['computed_unjudged'] += detail['answer'] == 'unjudged'
            m['computed_gold_abstention'] += g['abstain']
            computed_details.append(detail)
    report = {'run_id': meta['run_id'], 'per_type': dict(metrics), 'answer_scoring_complete': meta['complete'],
              'source_audit': str(args.source_audit) if args.source_audit else None,
              'caution': 'Computed scorer matches are automatic partial matches, not independently judged fact accuracy. '
                         'Source verdicts cover only exact reviewed claims and can be a selected subset. '
                         'Missing reader results are not counted as zero accuracy. No comparison claim on incomplete runs.'}
    write(args.run / 'audit.json', report)
    if computed_details:
        (args.run / 'computed_details.jsonl').write_text(''.join(json.dumps(d) + '\n' for d in computed_details))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
