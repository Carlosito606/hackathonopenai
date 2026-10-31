"""Populate ignored counting caches with the team's local stand-in, never Reactor.

Only existing R1 candidate caches are used. Missing candidates are reported, not
silently replaced with a cheaper retrieval method. This is extraction, not a
paired reader benchmark or independent semantic evaluation.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

from . import rocket
from .count_extract import DECODER_PROFILE, cache_key, closed_list_response, extract_one_source, literal_response_format, requested_window, supports_distinct, validate_response, visible_sources
from .run import candidate_key, rows, verify_reader, write
from .manifest import CandidateManifest
from .timeline import classify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    candidates = parser.add_mutually_exclusive_group(required=True)
    candidates.add_argument('--candidate-cache', type=Path)
    candidates.add_argument('--candidate-manifest', type=Path, help='exact R1 chunk export; all selected packs are verified')
    parser.add_argument('--out', type=Path, default=rocket.ROOT / 'rockets/r4/cache/counting')
    parser.add_argument('--local', required=True)
    parser.add_argument('--reader', required=True)
    parser.add_argument('--reader-revision', help='exact local model revision for extraction provenance')
    parser.add_argument('--types', default='multi-session')
    parser.add_argument('--ids', type=Path, help='optional dev subset; never overrides holdout exclusion')
    parser.add_argument('--max-chars', type=int, default=14000)
    args = parser.parse_args()
    if 'reactor-hackathon' in args.local.lower() or not args.local.startswith(('http://', 'https://')):
        parser.error('only a local stand-in endpoint is allowed')
    if not (args.data / 'gold.jsonl').exists():
        parser.error('development data only')
    verify_reader(args.local, args.reader)
    holdout = set((rocket.ROOT / 'splits/dev_holdout.txt').read_text().split())
    gold = {g['question_id']: g for g in rows(args.data / 'gold.jsonl') if g['question_id'] not in holdout}
    selected = set(args.ids.read_text().split()) if args.ids else None
    questions = [q for q in rows(args.data / 'questions.jsonl') if q['question_id'] in gold and
                 gold[q['question_id']]['question_type'] in args.types.split(',') and
                 (selected is None or q['question_id'] in selected) and classify(q['question'])['form'] == 'count']
    needed = {q['history_id'] for q in questions}
    histories = {h['history_id']: h for h in rows(args.data / 'histories.jsonl') if h['history_id'] in needed}
    manifest = CandidateManifest(args.candidate_manifest) if args.candidate_manifest else None
    manifest_cands = {}
    if manifest:
        manifest.verify_source(rocket.ROOT)
        manifest_cands = {q['question_id']: manifest.rebuild(q, histories[q['history_id']]) for q in questions}
        print(f'Verified {len(manifest_cands)} selected R1 evidence manifests.', flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    write(args.out / 'extraction-meta.json', {
        'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=rocket.ROOT, text=True).strip(),
        'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'rockets/r4'], cwd=rocket.ROOT)),
        'source_sha256': {name: hashlib.sha256((rocket.ROOT / 'rockets/r4' / name).read_bytes()).hexdigest()
                          for name in ['count_extract.py', 'extract_counts.py', 'counting.py']},
        'reader': args.reader, 'reader_revision': args.reader_revision, 'decoder_profile': DECODER_PROFILE,
        'split': 'dev minus holdout, optional --ids subset',
        'candidate_cache': str(args.candidate_cache) if args.candidate_cache else None, 'types': args.types,
        'candidate_provenance': manifest.provenance if manifest else
            'preexisting cache; this extraction CLI does not assert its retrieval source revision',
        'ids': str(args.ids) if args.ids else None})
    stats = Counter(selected_count_questions=len(questions))
    for q in questions:
        h = histories[q['history_id']]
        if not supports_distinct(q['question']):
            stats['unsupported_quantity_kind'] += 1
            continue
        if manifest:
            cands = manifest_cands[q['question_id']]
        else:
            path = args.candidate_cache / (candidate_key(q, h) + '.json')
            if not path.exists():
                stats['missing_candidates'] += 1
                continue
            cands = json.loads(path.read_text())
        evidence = rocket.compatible_evidence(h, cands, dates=False)
        sources = visible_sources(h, cands, evidence)
        key = cache_key(q, h, cands, sources)
        target = args.out / (key + '.json')
        if target.exists():
            cached = json.loads(target.read_text())
            if cached.get('extraction_method') != 'closed-list-rule' and (
                    cached.get('reader') != args.reader or cached.get('reader_revision') != args.reader_revision):
                raise ValueError('existing extraction cache uses another model/revision; use a separate output folder')
            stats['already_cached'] += 1
            continue
        if not requested_window(q['question'], q['question_date'])[0]:
            stats['unsupported_time_scope'] += 1
            continue
        ruled = closed_list_response(q, sources)
        if ruled:
            try:
                record = validate_response(q, h, cands, sources, ruled)
            except ValueError:
                record = None
            if record:
                record.update(extraction_method='closed-list-rule', model_reported_complete=False)
                write(target, record)
                stats['cached_by_rule'] += 1
                continue
        if not sources:
            stats['missing_sources'] += 1
            continue
        all_items, known = [], []
        valid = True
        for index, source in enumerate(sources):
            response_format = literal_response_format(source, known)
            schema_hash = hashlib.sha256(json.dumps(response_format, sort_keys=True).encode()).hexdigest()

            def call(prompt):
                request = urllib.request.Request(args.local.rstrip('/') + '/v1/chat/completions',
                    json.dumps({'model': args.reader, 'messages': [{'role': 'user', 'content': prompt}],
                                'temperature': 0, 'max_tokens': 400, 'response_format': response_format}).encode(),
                    {'Content-Type': 'application/json'})
                stats['local_calls'] += 1
                with urllib.request.urlopen(request, timeout=600) as response:
                    return json.load(response)['choices'][0]['message']['content']

            def audit(attempt, prompt, reply):
                write(args.out / (key + f'-source-{index}-attempt-{attempt}-response.json'), {
                    'question_id': q['question_id'], 'reader': args.reader, 'source': index, 'attempt': attempt,
                    'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'response_format_sha256': schema_hash, 'decoder_profile': DECODER_PROFILE, 'reply': reply})

            extracted, updated, outcome = extract_one_source(q, source, index, known, call, audit, args.max_chars)
            write(args.out / (key + f'-source-{index}-outcome.json'), outcome)
            stats['repair_requests'] += max(0, outcome['attempts'] - 1)
            if outcome['status'] != 'accepted':
                stats[outcome['status'] + '_source'] += 1
                valid = False
                break
            known = updated
            all_items += extracted
            stats['repaired_sources'] += outcome['attempts'] > 1
            print(q['question_id'], f'source {index+1}/{len(sources)}', flush=True)
        if not valid:
            continue
        try:
            record = validate_response(q, h, cands, sources, {'mode': 'distinct', 'complete': True, 'items': all_items})
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            stats['invalid_response'] += 1
            print(q['question_id'], 'invalid_response', type(error).__name__, flush=True)
            continue
        if record:
            record['reader'] = args.reader
            record['reader_revision'] = args.reader_revision
            record['extraction_method'] = 'local-model'
            write(target, record)
            stats['cached'] += 1
        else:
            stats['unresolved'] += 1
        print(q['question_id'], dict(stats), flush=True)
    write(args.out / 'extraction-summary.json', dict(stats))
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
