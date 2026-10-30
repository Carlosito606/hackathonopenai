"""Dev-only paired R1/R4 artifacts. Requires --local for answers; never calls Reactor.

python -m rockets.r4.run --data /path/dev --scorer /path/score.py --local http://host:8899 --reader MODEL
Use --prepare-only for retrieval/evidence/computation artifacts while waiting for the team reader.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import rocket

ROOT = rocket.ROOT


def rows(path):
    with Path(path).open(encoding='utf-8') as source:
        return [json.loads(line) for line in source if line.strip()]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def append(path, value):
    with path.open('a', encoding='utf-8') as out:
        out.write(json.dumps(value, ensure_ascii=False) + '\n')


def candidate_key(q, h):
    return hashlib.sha256(json.dumps([q, h], sort_keys=True).encode()).hexdigest()


def verify_reader(endpoint, model):
    # ask.py --local uses the server default. Require a single advertised model so the
    # claimed team reader cannot silently differ between the two variants or machines.
    with urllib.request.urlopen(endpoint.rstrip('/') + '/v1/models', timeout=10) as response:
        models = [item['id'] for item in json.load(response)['data']]
    if models != [model]:
        raise ValueError(f'expected exactly the team reader {model!r}; server advertises {models!r}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--local', help='team stand-in OpenAI-compatible endpoint; no Reactor endpoints accepted')
    parser.add_argument('--reader', help='exact team model name, required for measured answer runs')
    parser.add_argument('--scorer', type=Path, help='official memory-challenge/score.py')
    parser.add_argument('--types', default='temporal-reasoning', help='comma-separated dev types, or all')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--candidate-cache', type=Path, default=ROOT / 'rockets/r4/cache/candidates')
    parser.add_argument('--run-id', default=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    args = parser.parse_args()
    if not args.prepare_only and (not args.local or not args.reader or not args.scorer):
        parser.error('answer runs require --local, --reader and --scorer; otherwise use --prepare-only')
    if args.local and ('reactor-hackathon' in args.local or not args.local.startswith(('http://', 'https://'))):
        parser.error('only a stand-in endpoint is allowed')
    if not (args.data / 'gold.jsonl').exists():
        parser.error('dev gold is required for evaluation; test runs are intentionally unsupported')
    if not args.prepare_only:
        verify_reader(args.local, args.reader)
    holdout = set((ROOT / 'splits/dev_holdout.txt').read_text().split())
    # Gold is used only to select question types and score, never passed into any stage.
    gold = {g['question_id']: g for g in rows(args.data / 'gold.jsonl') if g['question_id'] not in holdout}
    types = set(args.types.split(','))
    questions = [q for q in rows(args.data / 'questions.jsonl') if q['question_id'] in gold and
                 (args.types == 'all' or gold[q['question_id']]['question_type'] in types)]
    needed = {q['history_id'] for q in questions}
    histories = {h['history_id']: h for h in rows(args.data / 'histories.jsonl') if h['history_id'] in needed}
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    out = ROOT / 'runs/r4' / (args.run_id + '-' + sha[:7])
    if out.exists():
        parser.error(f'run folder exists: {out}; use a new --run-id')
    out.mkdir(parents=True)
    write(out / 'meta.json', {'rocket': 'r4', 'run_id': out.name, 'git_sha': sha,
                            'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
                            'stages': {'retrieve': 'r1', 'enrich': 'r4', 'assemble': 'r4', 'decide': 'r4'},
                            'baseline_sha': 'de158d5', 'split': 'dev minus splits/dev_holdout.txt',
                            'question_types': sorted(types), 'questions': len(questions),
                            'reader': args.reader, 'flags': vars(args) | {'data': str(args.data), 'scorer': str(args.scorer),
                                                                      'candidate_cache': str(args.candidate_cache)},
                            'complete': False})
    baseline = out / 'baseline-r1'
    baseline.mkdir()
    write(baseline / 'meta.json', {'rocket': 'r1', 'run_id': out.name + '/baseline-r1', 'git_sha': sha,
                                  'stages': dict.fromkeys(['retrieve', 'enrich', 'assemble', 'decide'], 'r1'),
                                  'split': 'dev minus splits/dev_holdout.txt', 'reader': args.reader,
                                  'question_types': sorted(types), 'questions': len(questions),
                                  'complete': False})
    args.candidate_cache.mkdir(parents=True, exist_ok=True)
    ask = None if args.prepare_only else __import__('ask')
    stats = Counter()
    for index, q in enumerate(questions, 1):
        h = histories[q['history_id']]
        cache = args.candidate_cache / (candidate_key(q, h) + '.json')
        if cache.exists():
            cands = json.loads(cache.read_text())
        else:
            cands = rocket.retrieve(q, h)
            write(cache, cands)
        enriched = rocket.enrich(q, h, cands)
        packs = {'r1': rocket.baseline_assemble(q, h, cands), 'r4': rocket.assemble(q, h, enriched)}
        for name, folder, stages in [('r1', baseline, cands), ('r4', out, enriched)]:
            pack = packs[name]
            decision = (rocket.baseline_decide if name == 'r1' else rocket.decide)(q, h, stages, pack)
            append(folder / 'candidates.jsonl', {'question_id': q['question_id'], 'ranked':
                   [[c['session_id'], c['turn'], c['score']] for c in cands[:100]]})
            append(folder / 'evidence.jsonl', {'question_id': q['question_id'], 'sessions':
                   [e['id'] for e in pack['evidence']], 'chars': sum(len(e['text']) for e in pack['evidence'])})
            # Plans contain dataset text: untracked cache only, not run artifacts to commit.
            plan_path = args.candidate_cache / f'{q["question_id"]}-{name}-plan.json'
            plan = {**q, 'question': decision['question'], 'evidence': pack['evidence']}
            write(plan_path, plan)
            if ask is not None:
                result = ask.local(args, plan)
                write(args.candidate_cache / f'{q["question_id"]}-{name}-result.json', result)
                citations = [c['id'] for c in result.get('citations', []) if c.get('id')]
                answer = result.get('answer', '')
                if result.get('status') != 'answered':
                    raise RuntimeError(f'{q["question_id"]}: reader returned no final answer; run is incomplete')
                answer = re.sub(r'\[[^\[\]]*\bE\d+\b[^\[\]]*\]', '', answer).strip()
                append(folder / 'predictions.jsonl', {'question_id': q['question_id'], 'abstain': result['abstained'],
                       'answer': '' if result['abstained'] else answer, 'citations': list(dict.fromkeys(citations))})
        computed = bool(packs['r4']['facts'])
        computation = rocket.grounded_computation(q, enriched, packs['r4']['evidence'])
        stats['questions'] += 1
        stats['computed'] += computed
        append(out / 'computations.jsonl', {'question_id': q['question_id'], **computation})
        print(f'{index}/{len(questions)} computed={stats["computed"]}', flush=True)
    if ask is not None:
        with tempfile.TemporaryDirectory() as tmp:
            selected_gold = Path(tmp) / 'gold.jsonl'
            for q in questions:
                append(selected_gold, gold[q['question_id']])
            for folder in [baseline, out]:
                result = subprocess.run([sys.executable, str(args.scorer), str(selected_gold),
                                         str(folder / 'predictions.jsonl'), '--details', str(folder / 'details.jsonl')],
                                        capture_output=True, text=True, check=True)
                (folder / 'score.txt').write_text(result.stdout)
    write(out / 'summary.json', dict(stats) | {'answer_scoring_complete': ask is not None})
    meta = json.loads((out / 'meta.json').read_text())
    meta['complete'] = ask is not None
    write(out / 'meta.json', meta)
    baseline_meta = json.loads((baseline / 'meta.json').read_text())
    baseline_meta['complete'] = ask is not None
    write(baseline / 'meta.json', baseline_meta)
    print(out)


if __name__ == '__main__':
    main()
