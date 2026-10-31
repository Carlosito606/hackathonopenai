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
    # Both the original monolith and the split R1 cache this public factory.
    # The split memsys facade intentionally does not export `_reranker`.
    module.reranker(device=device)
    return [{**c, 'kind': 'turn', 'notes': {}} for c in module.retrieve(
        h, q['question'], _emb, question_date=q['question_date'])][:200]


def enrich(q, h, cands):
    sessions = {s['session_id']: s for s in h['sessions']}
    form = classify(q['question'])
    enriched = []
    for c in cands:
        session = sessions[c['session_id']]
        event_role = c['role'] if c['kind'] == 'turn' and c['turn'] is not None else None
        extracted = events(c['text'], session['date'], c['session_id'], c['turn'], event_role)
        # R1 brings up to 300 characters of the preceding user turn with an assistant
        # candidate. These are real source events, even if that user turn was not ranked.
        if c['role'] == 'assistant' and c['turn'] is not None and c['turn'] > 0:
            previous = session['turns'][c['turn'] - 1]
            if previous['role'] == 'user':
                extracted += events(previous['content'][:300], session['date'], c['session_id'], c['turn'] - 1, 'user')
        enriched.append({**c, 'notes': {**c.get('notes', {}), 'timeline': extracted, 'question_form': form}})
    return enriched


def baseline_assemble(q, h, cands):
    module = r1()
    return {'evidence': compatible_evidence(h, cands, dates=bool(module.TEMPORAL.search(q['question']))), 'facts': ''}


def compatible_evidence(h, cands, dates=False):
    """Adapt contract Cand values without relying on R1's private `si` field.

    The R1 turn path stays identical. Session/fact units with turn=None remain
    valid inputs for docking, but cannot ground exact user-event arithmetic.
    """
    sessions = {s['session_id']: (index, s) for index, s in enumerate(h['sessions'])}
    turns, other = [], []
    for c in cands:
        if c['session_id'] not in sessions:
            raise ValueError('candidate session is not part of this history')
        index, session = sessions[c['session_id']]
        turn = c['turn']
        if turn is None:
            other.append(c)
            continue
        if type(turn) is not int or not 0 <= turn < len(session['turns']):
            raise ValueError('candidate turn is not part of its source session')
        turns.append({**c, 'si': index, 'role': session['turns'][turn]['role']})
    evidence = r1().build_evidence(h, turns, dates=dates)
    used = sum(len(item['text']) + 60 for item in evidence)
    by_id = {item['id']: item for item in evidence}
    for c in other:
        text = c['text'][:1000]
        session = sessions[c['session_id']][1]
        if dates:
            text = r1().annotate_dates(text, r1().parse_date(session['date']))
        text = f'{c["kind"]}: {text}'
        if used + len(text) + 60 > 18000:
            continue
        if c['session_id'] in by_id:
            by_id[c['session_id']]['text'] += '\n' + text
        else:
            by_id[c['session_id']] = {'id': c['session_id'], 'date': session['date'], 'text': text}
        used += len(text) + 60
    return sorted(by_id.values(), key=lambda item: sessions[item['id']][0])


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
    evidence = compatible_evidence(h, cands, dates=False)
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
    if not facts:
        return baseline_assemble(q, h, cands)
    # Labels refer to the final evidence order, not the ranked candidates.
    for index, item in enumerate(evidence, 1):
        facts = facts.replace('source ' + item['id'] + ',', f'source [E{index}],')
    return {'evidence': evidence, 'facts': facts}


def baseline_decide(q, h, cands, pack):
    prepare = importlib.import_module('prepare')
    # Neutral format-only example in both variants; never seed an answer with a name
    # that might occur in the challenge's test data.
    guide = re.sub(r'e\.g\.\s*"[^"\n]*?\[E\d+\][^"\n]*"', 'e.g. "<answer> [E4]"', prepare.GUIDE)
    extra = prepare.DATES.format(today=r1().day_no(r1().parse_date(q['question_date']))) if r1().TEMPORAL.search(q['question']) else ''
    if prepare.COUNTING.search(q['question']) and not re.search(r'how many (days|weeks|months|years)', q['question'], re.I):
        extra += prepare.COUNT
    return {'question': q['question'].strip() + '\n' + guide.format(extra=extra),
            'abstain': False, 'after': 'abstain_if_insufficient'}


def decide(q, h, cands, pack):
    baseline = baseline_decide(q, h, cands, pack)
    if not pack['facts']:
        return baseline
    text = baseline['question']
    if pack['facts']:
        text += ('\nCalendar computations for the matched events in the supplied excerpts:\n' + pack['facts'] +
                 '\nUse these computations only for the events named above. Keep their evidence labels in the final answer line.')
    text += ('\nDate ranges and dates labelled inferred are not exact event dates. '
             'Do not replace an event date with its conversation date unless the text says it happened that day.')
    return {'question': text, 'abstain': False, 'after': 'abstain_if_insufficient'}


STAGES = {'retrieve': retrieve, 'enrich': enrich, 'assemble': assemble, 'decide': decide}
