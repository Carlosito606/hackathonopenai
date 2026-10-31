"""Recover only complete paired questions after an interrupted local run."""
import json


def read_checkpoint(path):
    if not path.exists():
        return []
    # JSON permits U+2028/U+0085 inside strings; only actual JSONL record
    # newlines delimit rows. str.splitlines() would corrupt such answers.
    with path.open(encoding='utf-8') as source:
        lines = list(source)
    items = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            # A process can be interrupted midway through its last append. Earlier
            # corruption is not a recoverable checkpoint and must remain visible.
            if index != len(lines) - 1 or line.endswith('\n'):
                raise
    return items


def recover(folder, question_ids, with_answers):
    """Keep the common ordered prefix; never treat one variant as a completed pair."""
    names = ['candidates.jsonl', 'evidence.jsonl']
    if with_answers:
        names += ['predictions.jsonl']
    paths = [base / name for base in [folder, folder / 'baseline-r1'] for name in names]
    paths += [folder / 'computations.jsonl']
    if with_answers:
        paths += [folder / 'reader_status.jsonl']
    records = {path: read_checkpoint(path) for path in paths}
    for path, items in records.items():
        ids = [item['question_id'] for item in items]
        if ids != question_ids[:len(ids)]:
            raise ValueError(f'checkpoint order or question ids differ: {path}')
    count = min(map(len, records.values()))
    for path, items in records.items():
        path.write_text(''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in items[:count]),
                        encoding='utf-8')
    computations = records[folder / 'computations.jsonl'][:count]
    statuses = records.get(folder / 'reader_status.jsonl', [])[:count]
    return count, computations, statuses


def validate_resume(previous, current):
    for key in ['git_sha', 'split', 'question_types', 'questions', 'reader', 'baseline_sha', 'candidate_manifest']:
        if previous.get(key) != current.get(key):
            raise ValueError(f'cannot resume with changed {key}')
    if previous.get('source_dirty') or current.get('source_dirty'):
        raise ValueError('resume requires clean source files at the recorded commit')
    for key in ['data', 'local', 'reader_revision', 'candidate_cache', 'prepare_only']:
        if previous['flags'].get(key) != current['flags'].get(key):
            raise ValueError(f'cannot resume with changed {key}')
