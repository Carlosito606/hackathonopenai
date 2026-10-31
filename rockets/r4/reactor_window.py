"""Prepare an offline R4/R1 packet; a human runs it within a Reactor reservation.

Run this file directly, not with -m: --source-root pins the stage implementation.
prepare never accesses credentials or Reactor. run requires a real operator TTY
and reads the credential only through getpass, never from an agent argument/file.
"""
import argparse
import getpass
import hashlib
import importlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def rows(path):
    with Path(path).open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def jsonl(path, values):
    Path(path).write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values), encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(root, expected):
    root = Path(root).resolve()
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if actual != expected:
        raise ValueError('stage source commit changed')
    if subprocess.check_output(['git', 'status', '--porcelain', '--', 'rockets/r4',
                                'retrieval.py', 'dates.py', 'evidence.py', 'memsys.py',
                                'prepare.py', 'ask.py', 'reactor/client.py'], cwd=root):
        raise ValueError('stage source must be clean')
    if 'rockets.r4' in sys.modules:
        raise ValueError('run this standalone file so --source-root owns the imported stages')
    sys.path.insert(0, str(root))
    return importlib.import_module('rockets.r4.rocket'), importlib.import_module('ask')


def prepare(args):
    if args.out.exists():
        raise ValueError('output exists; use a fresh preparation folder')
    rocket, ask = load_source(args.source_root, args.source_sha)
    manifest_module = importlib.import_module('rockets.r4.manifest')
    report = importlib.import_module('rockets.r4.report')
    manifest = manifest_module.CandidateManifest(args.manifest)
    manifest.verify_source(args.source_root)
    holdout = set((args.source_root / 'splits/dev_holdout.txt').read_text().split())
    types = {g['question_id']: g['question_type'] for g in rows(args.data / 'gold.jsonl')
             if g['question_id'] not in holdout}
    questions = [q for q in rows(args.data / 'questions.jsonl')
                 if types.get(q['question_id']) == 'temporal-reasoning']
    needed = {q['history_id'] for q in questions}
    histories = {h['history_id']: h for h in rows(args.data / 'histories.jsonl') if h['history_id'] in needed}
    reviews = json.loads(args.source_audit.read_text())['reviews']
    plans = {'r1': [], 'r4': []}
    artifacts = {'r1': [], 'r4': []}
    computations = []
    checked_plans = 0
    for q in questions:
        h = histories[q['history_id']]
        cands = manifest.rebuild(q, h)
        enriched = rocket.enrich(q, h, cands)
        packs = {'r1': rocket.baseline_assemble(q, h, cands), 'r4': rocket.assemble(q, h, enriched)}
        computation = rocket.grounded_computation(q, enriched, packs['r4']['evidence'])
        pair = {}
        for name in ['r1', 'r4']:
            stage_cands = cands if name == 'r1' else enriched
            decision = (rocket.baseline_decide if name == 'r1' else rocket.decide)(q, h, stage_cands, packs[name])
            plan = {**q, 'question': decision['question'], 'evidence': packs[name]['evidence']}
            cached = args.plan_cache / f'{q["question_id"]}-{name}-plan.json'
            if plan != json.loads(cached.read_text()):
                raise ValueError('prepared plan differs from the frozen local benchmark')
            checked_plans += 1
            passages = ask.kit.load_evidence(json.dumps(plan['evidence']))
            if len(ask.kit.build_message(plan['question'], passages, '00000000',
                                        ask.kit.parse_question_date(q['question_date']))) > 30000:
                raise ValueError('prepared message exceeds the client limit')
            pair[name] = plan
        if not packs['r4']['facts']:
            continue
        if not computation['computed'] or report.source_verdict({'question_id': q['question_id'], **computation}, reviews) != 'supported':
            raise ValueError('every supplied computation needs an exact supported source audit')
        computations.append({'question_id': q['question_id'], **computation})
        for name in ['r1', 'r4']:
            plans[name].append(pair[name])
            artifacts[name].append(({'question_id': q['question_id'], 'ranked':
                                      [[c['session_id'], c['turn'], c['score']] for c in cands[:100]]},
                                     {'question_id': q['question_id'], 'sessions': [e['id'] for e in packs[name]['evidence']],
                                      'chars': sum(len(e['text']) for e in packs[name]['evidence'])}))
    if not computations:
        raise ValueError('no source-audited computations to compare')
    args.out.mkdir(parents=True)
    for name in ['r1', 'r4']:
        jsonl(args.out / f'{name}-plan.jsonl', plans[name])
        folder = args.out / 'artifacts' / ('baseline-r1' if name == 'r1' else 'r4')
        folder.mkdir(parents=True)
        jsonl(folder / 'candidates.jsonl', [c for c, e in artifacts[name]])
        jsonl(folder / 'evidence.jsonl', [e for c, e in artifacts[name]])
    jsonl(args.out / 'artifacts/r4/computations.jsonl', computations)
    reference = manifest.provenance['source_git_sha'].split()[0]
    baseline_reference = subprocess.check_output(['git', 'rev-parse', reference + '^{commit}'],
                                                  cwd=args.source_root, text=True).strip()
    meta = {'run_id': args.out.name, 'source_root': str(args.source_root), 'source_sha': args.source_sha,
            'baseline_sha': args.source_sha, 'baseline_reference_sha': baseline_reference,
            'source_dirty': False, 'question_types': ['temporal-reasoning'],
            'operator_sha256': digest(__file__), 'data': str(args.data), 'scorer': str(args.scorer),
            'question_ids': [p['question_id'] for p in plans['r4']], 'questions': len(computations),
            'all_temporal_questions_verified': len(questions), 'cached_plans_matched': checked_plans,
            'candidate_manifest': manifest.provenance, 'source_audit_sha256': digest(args.source_audit),
            'plans_sha256': {name: digest(args.out / f'{name}-plan.jsonl') for name in ['r1', 'r4']},
            'selection': 'all computed-in-pack temporal dev questions, holdout excluded; no gold-answer filtering',
            'reader': 'reactor', 'reader_executed': False, 'complete': False,
            'flags': {'prepare_only': True, 'operator_pending': True, 'credential_source': 'human hidden terminal prompt'},
            'caution': 'Selected computation subset, not full-type answer accuracy. Preparation sends no requests.'}
    write(args.out / 'prepared.json', meta)
    for name in ['r1', 'r4']:
        folder = args.out / 'artifacts' / ('baseline-r1' if name == 'r1' else 'r4')
        write(folder / 'meta.json', {**meta, 'rocket': name, 'git_sha': args.source_sha,
                                   'stages': dict(retrieve='r1', enrich=name, assemble=name, decide=name),
                                   'split': 'dev temporal computed subset minus holdout'})
    print(json.dumps({'prepared': str(args.out), 'questions': len(computations),
                      'cached_plans_matched': checked_plans, 'reactor_requests': 0}))


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError('reservation times must explicitly use UTC')
    return result


def child(command, env, cwd, seconds):
    proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=seconds)
    except BaseException as error:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
        if isinstance(error, subprocess.TimeoutExpired):
            raise TimeoutError('operator deadline reached; stopped only this client process group') from None
        raise
    if proc.returncode:
        raise RuntimeError(f'operator client failed with exit code {proc.returncode}; inspect its private result file')


def run(args):
    if not sys.stdin.isatty():
        raise ValueError('a human must run this in an interactive terminal; never send the credential in chat')
    meta = json.loads((args.prepared / 'prepared.json').read_text())
    if meta['operator_sha256'] != digest(__file__):
        raise ValueError('operator code changed since preparation')
    rocket, ask = load_source(Path(meta['source_root']), meta['source_sha'])
    prediction = importlib.import_module('rockets.r4.run').prediction
    plans = {name: rows(args.prepared / f'{name}-plan.jsonl') for name in ['r1', 'r4']}
    for name in plans:
        if digest(args.prepared / f'{name}-plan.jsonl') != meta['plans_sha256'][name]:
            raise ValueError('prepared plan changed')
    start, end = utc(args.start), utc(args.end)
    if not 0 < args.timeout <= 300:
        raise ValueError('operator timeout must be 1..300 seconds')
    if end <= start or datetime.now(timezone.utc) >= end:
        raise ValueError('invalid or expired reservation')
    print('Use only a window already announced by your human on the agent channel.', flush=True)
    secret = getpass.getpass('Reactor credential (hidden; retained only for this operator process): ')
    if not secret:
        raise ValueError('empty operator credential')
    env = {k: os.environ[k] for k in ['PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR'] if k in os.environ}
    env['REACTOR_ACCESS_KEY'] = secret
    raw = args.prepared / 'raw'
    raw.mkdir(exist_ok=True)
    results = {'r1': {}, 'r4': {}}
    try:
        while datetime.now(timezone.utc) < start:
            time.sleep(max(0, min(5, (start - datetime.now(timezone.utc)).total_seconds())))
        for index, qid in enumerate(meta['question_ids']):
            order = ['r1', 'r4'] if index % 2 == 0 else ['r4', 'r1']
            for name in order:
                path = raw / f'{qid}-{name}-result.jsonl'
                if path.exists():
                    saved = rows(path)
                    if len(saved) != 1 or saved[0].get('status') != 'answered':
                        raise ValueError('failed or incomplete result needs operator inspection before any retry')
                    results[name][qid] = saved[0]
                    continue
                remaining = (end - datetime.now(timezone.utc)).total_seconds()
                # ask.py can retry once; keep a further full query timeout as a
                # buffer before anybody else's reservation, even on slow replies.
                if remaining < 3 * args.timeout + 30:
                    raise TimeoutError('not enough reserved time for another question and its safety buffer')
                plan = raw / f'{qid}-{name}-plan.jsonl'
                jsonl(plan, [plans[name][index]])
                command = [sys.executable, str(rocket.ROOT / 'ask.py'), str(plan), str(path),
                           '--base-url', args.base_url, '--agent-id', args.agent_id, '--timeout', str(args.timeout)]
                child(command, env, rocket.ROOT, remaining - args.timeout)
                saved = rows(path)
                if len(saved) != 1 or saved[0].get('question_id') != qid:
                    raise ValueError('unexpected operator result')
                results[name][qid] = saved[0]
                print(qid, name, saved[0].get('status'), flush=True)
    finally:
        env.pop('REACTOR_ACCESS_KEY', None)
        secret = ''
        for name in results:
            folder = args.prepared / 'artifacts' / ('baseline-r1' if name == 'r1' else 'r4')
            ordered = [results[name][qid] for qid in meta['question_ids'] if qid in results[name]]
            jsonl(folder / 'predictions.jsonl', [prediction(r) for r in ordered])
            recorded = json.loads((folder / 'meta.json').read_text())
            recorded.update(complete=len(ordered) == meta['questions'],
                            reader_executed=bool(ordered),
                            reservation_start=start.isoformat(), reservation_end=end.isoformat(),
                            client_statuses=[r.get('status') for r in ordered])
            recorded['flags'].update(prepare_only=False, operator_pending=False)
            write(folder / 'meta.json', recorded)
        meta['complete'] = all(len(results[name]) == meta['questions'] for name in results)
        meta['reader_executed'] = any(results.values())
        meta['flags'].update(prepare_only=False, operator_pending=False)
        write(args.prepared / 'prepared.json', meta)
    if meta['complete']:
        selected = set(meta['question_ids'])
        with tempfile.TemporaryDirectory() as temporary:
            gold = Path(temporary) / 'gold.jsonl'
            jsonl(gold, [g for g in rows(Path(meta['data']) / 'gold.jsonl') if g['question_id'] in selected])
            for name in results:
                folder = args.prepared / 'artifacts' / ('baseline-r1' if name == 'r1' else 'r4')
                scored = subprocess.run([sys.executable, meta['scorer'], str(gold), str(folder / 'predictions.jsonl'),
                                         '--details', str(folder / 'details.jsonl')], capture_output=True, text=True, check=True)
                (folder / 'summary.txt').write_text(scored.stdout)
        print('Paired operator run complete; score.py outputs are in artifacts/. Announce RELEASE after checking no task remains.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    for name in ['source-root', 'data', 'manifest', 'plan-cache', 'source-audit', 'scorer', 'out']:
        prep.add_argument('--' + name, required=True, type=Path)
    prep.add_argument('--source-sha', required=True)
    operator = sub.add_parser('run')
    operator.add_argument('--prepared', required=True, type=Path)
    operator.add_argument('--base-url', required=True)
    operator.add_argument('--agent-id', required=True)
    operator.add_argument('--start', required=True)
    operator.add_argument('--end', required=True)
    operator.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    (prepare if args.action == 'prepare' else run)(args)


if __name__ == '__main__':
    main()
