"""Rebuild exported R1 chunks from this history, without embedding models or gold.

Require the chunk index, matching R1 source and matching evidence manifests. A
session/turn-only export cannot identify which window of a long turn was ranked.
"""
import ast
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from . import rocket


def reconstruction_signature(source):
    """Match the entire retrieval module except the unused retrieve body.

    A manifest supplies the ranked candidates; only reconstruction helpers run.
    Keep signatures, defaults, decorators, imports, constants and every other
    function exact, so changing chunking or module initialization is rejected.
    """
    tree = ast.parse(source)
    found = 0
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'retrieve':
            node.body = [ast.Pass()]
            found += 1
    if found != 1:
        raise ValueError('expected one R1 retrieve definition')
    return ast.dump(tree, include_attributes=False)


def records(path):
    with path.open(encoding='utf-8') as source:
        result = {}
        for line in source:
            if not line.strip():
                continue
            item = json.loads(line)
            key = item['question_id']
            if key in result:
                raise ValueError(f'duplicate question in {path.name}: {key}')
            result[key] = item
        return result


class CandidateManifest:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.ranked = records(self.folder / 'candidates.jsonl')
        self.evidence = records(self.folder / 'evidence.jsonl')
        self.meta = json.loads((self.folder / 'meta.json').read_text())
        self.provenance = {
            'source_git_sha': self.meta['git_sha'],
            'sha256': {name: hashlib.sha256((self.folder / name).read_bytes()).hexdigest()
                       for name in ['meta.json', 'candidates.jsonl', 'evidence.jsonl']},
        }

    def verify_source(self, root):
        # Never execute code from an export. Compare its named revision to the
        # R1 files actually imported by this local paired runner.
        revision = self.meta['git_sha'].split()[0]
        if not re.fullmatch(r'[0-9a-f]{7,40}', revision):
            raise ValueError('manifest must name a git source revision')
        for name in ['retrieval.py', 'dates.py', 'evidence.py', 'memsys.py', 'prepare.py']:
            original = subprocess.check_output(['git', 'show', f'{revision}:{name}'], cwd=root)
            current = (root / name).read_bytes()
            equal = (reconstruction_signature(original) == reconstruction_signature(current)
                     if name == 'retrieval.py' else original == current)
            if not equal:
                raise ValueError(f'manifest R1 source differs: {name}')
        self.provenance['resolved_source_git_sha'] = subprocess.check_output(
            ['git', 'rev-parse', f'{revision}^{{commit}}'], cwd=root, text=True).strip()
        self.provenance['reconstruction_verification'] = (
            'retrieval AST except unused retrieve body; byte-identical dates/evidence/facade/prepare')

    def rebuild(self, q, h):
        qid = q['question_id']
        if qid not in self.ranked or qid not in self.evidence:
            raise ValueError(f'manifest does not cover selected question: {qid}')
        sessions = {s['session_id']: (i, s) for i, s in enumerate(h['sessions'])}
        cands = []
        for row in self.ranked[qid]['ranked']:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError('manifest rows require [session_id, turn, chunk_idx, score]')
            sid, turn, chunk, score = row
            if sid not in sessions:
                raise ValueError('manifest session is not part of this history')
            si, session = sessions[sid]
            if type(turn) is not int or not 0 <= turn < len(session['turns']):
                raise ValueError('invalid manifest turn')
            source = session['turns'][turn]
            pieces = rocket.r1().split_text(source['content'])
            if type(chunk) is not int or not 0 <= chunk < len(pieces):
                raise ValueError('invalid manifest chunk index')
            if type(score) not in (int, float) or not math.isfinite(score):
                raise ValueError('invalid manifest score')
            cands.append({'session_id': sid, 'si': si, 'date': session['date'],
                          'turn': turn, 'role': source['role'], 'text': pieces[chunk],
                          'score': score, 'kind': 'turn', 'notes': {}})
        evidence = rocket.baseline_assemble(q, h, cands)['evidence']
        actual = {'question_id': qid, 'sessions': [e['id'] for e in evidence],
                  'chars': sum(len(e['text']) for e in evidence)}
        if actual != self.evidence[qid]:
            raise ValueError(f'rebuilt baseline does not match exported evidence: {qid}')
        return cands
