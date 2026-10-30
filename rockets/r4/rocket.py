"""R4 TIMELINE: R1 retrieval, forked temporal enrichment, conservative code computations."""
import importlib
import os
import re
import sys
from pathlib import Path

from .dates import annotate_dates
from .timeline import classify, compute, events

ROOT = Path(__file__).resolve().parents[2]
_emb = None


def r1():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module('memsys')


def retrieve(q, h):
    global _emb
    module = r1()
    device = os.environ.get('R4_DEVICE', 'cpu')
    if _emb is None:
        _emb = module.Embedder(os.environ.get('R4_EMBED_CACHE', str(ROOT / 'rockets/r4/cache/embeddings.pkl')), device=device)
    if module._reranker is None:
        module.reranker(device=device)
    return [{**c, 'kind': 'turn', 'notes': {}} for c in module.retrieve(h, q['question'], _emb)][:200]


def enrich(q, h, cands):
    sessions = {s['session_id']: s for s in h['sessions']}
    form = classify(q['question'])
    enriched = []
    for c in cands:
        session = sessions[c['session_id']]
        extracted = events(c['text'], session['date'], c['session_id'], c['turn'], c['role'])
        enriched.append({**c, 'notes': {**c.get('notes', {}), 'timeline': extracted, 'question_form': form}})
    return enriched


def baseline_assemble(q, h, cands):
    module = r1()
    return {'evidence': module.build_evidence(h, cands, dates=bool(module.TEMPORAL.search(q['question']))), 'facts': ''}


def grounded_computation(q, cands, evidence):
    selected_ids = {item['id'] for item in evidence}
    # Compute only from text that is actually in the evidence pack, never from omitted candidates.
    pool = []
    for c in cands:
        if c['session_id'] not in selected_ids:
            continue
        for event in c.get('notes', {}).get('timeline', []):
            normalized = annotate_dates(event['text'], event['session_date'])
            if any(item['id'] == event['session_id'] and normalized in item['text'] for item in evidence):
                pool.append(event)
    return compute(q['question'], q['question_date'], pool)


def assemble(q, h, cands):
    # Select the same excerpts as R1 before adding the fork's date annotations.
    evidence = r1().build_evidence(h, cands, dates=False)
    bounded, used = [], 0
    for item in evidence:
        item['text'] = annotate_dates(item['text'], item['date'])
        cost = len(item['text']) + len(item['date']) + 40
        if used + cost <= 24000:
            bounded.append(item)
            used += cost
    evidence = bounded
    computation = grounded_computation(q, cands, evidence)
    facts = computation['facts']
    # Labels refer to the final evidence order, not the ranked candidates.
    for index, item in enumerate(evidence, 1):
        facts = facts.replace('source ' + item['id'] + ',', f'source [E{index}],')
    return {'evidence': evidence, 'facts': facts}


def baseline_decide(q, h, cands, pack):
    prepare = importlib.import_module('prepare')
    extra = prepare.DATES.format(today=r1().day_no(r1().parse_date(q['question_date']))) if r1().TEMPORAL.search(q['question']) else ''
    if prepare.COUNTING.search(q['question']) and not re.search(r'how many (days|weeks|months|years)', q['question'], re.I):
        extra += prepare.COUNT
    return {'question': q['question'].strip() + '\n' + prepare.GUIDE.format(extra=extra),
            'abstain': False, 'after': 'abstain_if_insufficient'}


def decide(q, h, cands, pack):
    text = baseline_decide(q, h, cands, pack)['question']
    if pack['facts']:
        text += ('\nVerified calendar computations from the supplied excerpts:\n' + pack['facts'] +
                 '\nUse these computations only for the events named above. Keep their evidence labels in the final answer line.')
    text += ('\nDate ranges and dates labelled inferred are not exact event dates. '
             'Do not replace an event date with its conversation date unless the text says it happened that day.')
    return {'question': text, 'abstain': False, 'after': 'abstain_if_insufficient'}


STAGES = {'retrieve': retrieve, 'enrich': enrich, 'assemble': assemble, 'decide': decide}
