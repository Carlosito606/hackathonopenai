"""Dev-only paired R1/R4 artifacts. Requires --local for answers; never calls Reactor.

python -m rockets.r4.run --data /path/dev --scorer /path/score.py --local http://host:8899 --reader MODEL
Use --prepare-only for retrieval/evidence/computation artifacts while waiting for the team reader.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import rocket
from .checkpoint import recover, validate_resume
from .manifest import CandidateManifest

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


def prediction(result):
    """A missing final answer is an empty, non-abstained response, scored as a failure.

    Never turn a parser/transport failure into a claim that the evidence is insufficient.
    The raw status is retained separately in the ignored result cache and summary counts.
    """
    answered = result.get('status') == 'answered'
    abstained = answered and result.get('abstained', False)
    citations = [c['id'] for c in result.get('citations', []) if c.get('id')] if answered else []
    answer = result.get('answer', '') if answered else ''
    answer = re.sub(r'\[[^\[\]]*\bE\d+\b[^\[\]]*\]', '', answer).strip()
    return {'question_id': result['question_id'], 'abstain': abstained,
            'answer': '' if abstained else answer, 'citations': list(dict.fromkeys(citations))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--local', help='team stand-in OpenAI-compatible endpoint; no Reactor endpoints accepted')
    parser.add_argument('--reader', help='exact team model name, required for measured answer runs')
    parser.add_argument('--reader-revision', help='optional exact model repository revision for reproducibility')
    parser.add_argument('--scorer', type=Path, help='official memory-challenge/score.py')
    parser.add_argument('--types', default='temporal-reasoning', help='comma-separated dev types, or all')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--resume', action='store_true', help='resume this --run-id at the identical clean source commit and reader')
    parser.add_argument('--candidate-cache', type=Path, default=ROOT / 'rockets/r4/cache/candidates')
    parser.add_argument('--candidate-manifest', type=Path,
                        help='R1 export folder with explicit chunk indices, evidence.jsonl and meta.json')
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
    manifest = CandidateManifest(args.candidate_manifest) if args.candidate_manifest else None
    manifest_cands = {}
    if manifest:
        manifest.verify_source(ROOT)
        # Fail before any reader calls if even one question cannot be reproduced.
        manifest_cands = {q['question_id']: manifest.rebuild(q, histories[q['history_id']]) for q in questions}
        print(f'Verified {len(manifest_cands)} exported R1 evidence manifests.', flush=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    out = ROOT / 'runs/r4' / (args.run_id + '-' + sha[:7])
    if out.exists() and not args.resume:
        parser.error(f'run folder exists: {out}; use a new --run-id')
    if args.resume and not out.exists():
        parser.error(f'no checkpoint at {out}')
    out.mkdir(parents=True, exist_ok=args.resume)
    metadata = {'rocket': 'r4', 'run_id': out.name, 'git_sha': sha,
                            'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', '--',
                                'rockets/r4', 'memsys.py', 'prepare.py', 'ask.py', 'retrieval.py', 'dates.py',
                                'evidence.py', 'reactor/client.py'], cwd=ROOT)),
                            'stages': {'retrieve': 'r1', 'enrich': 'r4', 'assemble': 'r4', 'decide': 'r4'},
                            'baseline_sha': sha, 'split': 'dev minus splits/dev_holdout.txt',
                            'candidate_manifest': manifest.provenance if manifest else None,
                            'question_types': sorted(types), 'questions': len(questions),
                            'reader': args.reader, 'flags': vars(args) | {'data': str(args.data), 'scorer': str(args.scorer),
                                                                      'candidate_cache': str(args.candidate_cache),
                                                                      'candidate_manifest': str(args.candidate_manifest) if manifest else None},
                            'retrieval_device': os.environ.get('R4_DEVICE', 'cpu'),
                            'cpu_threads': os.environ.get('OMP_NUM_THREADS'),
                            'complete': False}
    baseline = out / 'baseline-r1'
    baseline.mkdir(exist_ok=args.resume)
    if args.resume:
        validate_resume(json.loads((out / 'meta.json').read_text()), metadata)
    else:
        write(out / 'meta.json', metadata)
        write(baseline / 'meta.json', {'rocket': 'r1', 'run_id': out.name + '/baseline-r1', 'git_sha': sha, 'baseline_sha': sha,
                                  'stages': dict.fromkeys(['retrieve', 'enrich', 'assemble', 'decide'], 'r1'),
                                  'split': 'dev minus splits/dev_holdout.txt', 'reader': args.reader,
                                  'candidate_manifest': manifest.provenance if manifest else None,
                                  'question_types': sorted(types), 'questions': len(questions),
                                  'complete': False})
    args.candidate_cache.mkdir(parents=True, exist_ok=True)
    ask = None if args.prepare_only else __import__('ask')
    stats = Counter()
    start = 0
    if args.resume:
        start, computations, statuses = recover(out, [q['question_id'] for q in questions], ask is not None)
        stats['questions'] = start
        stats['computed'] = sum(item['computed'] for item in computations)
        for item in statuses:
            stats['shared_reader_results'] += item.get('shared_identical_plan', False)
            for name in ['r1', 'r4']:
                stats['reader_no_final_' + name] += item[name] != 'answered'
        print(f'Resuming after {start} complete paired questions.', flush=True)
    for index, q in enumerate(questions[start:], start + 1):
        h = histories[q['history_id']]
        cache = args.candidate_cache / (candidate_key(q, h) + '.json')
        if manifest:
            cands = manifest_cands[q['question_id']]
        elif cache.exists():
            cands = json.loads(cache.read_text())
        else:
            cands = rocket.retrieve(q, h)
            write(cache, cands)
        enriched = rocket.enrich(q, h, cands)
        packs = {'r1': rocket.baseline_assemble(q, h, cands), 'r4': rocket.assemble(q, h, enriched)}
        reader_status = {'question_id': q['question_id']}
        baseline_plan = baseline_result = None
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
                if name == 'r4' and plan == baseline_plan:
                    result = {**baseline_result, 'reused_from': 'r1-identical-plan'}
                    reader_status['shared_identical_plan'] = True
                    stats['shared_reader_results'] += 1
                else:
                    result = ask.local(args, plan)
                if name == 'r1':
                    baseline_plan, baseline_result = plan, result
                write(args.candidate_cache / f'{q["question_id"]}-{name}-result.json', result)
                if result.get('status') != 'answered':
                    stats['reader_no_final_' + name] += 1
                reader_status[name] = result.get('status', 'unknown')
                append(folder / 'predictions.jsonl', prediction(result))
        computed = bool(packs['r4']['facts'])
        computation = rocket.grounded_computation(q, enriched, packs['r4']['evidence'])
        stats['questions'] += 1
        stats['computed'] += computed
        append(out / 'computations.jsonl', {'question_id': q['question_id'], **computation})
        if ask is not None:
            append(out / 'reader_status.jsonl', reader_status)
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
