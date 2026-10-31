"""Count distinct source-grounded entities, not mentions or repeated sessions.

This arithmetic component accepts extracted item spans. Extraction and corpus
coverage must be assessed separately: a count of supplied items does not prove
the history contains no additional items. No gold or question ids are used.
"""
import re
import unicodedata
from collections import defaultdict

from .dates import parse_date, resolve_dates
from .timeline import events


def entity_key(label):
    # Normalize typography/case only. Never collapse near names by token overlap,
    # remove articles, or guess that an acronym names the same entity.
    text = unicodedata.normalize('NFKC', label).casefold().strip()
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', text)


def grounded_items(h, items):
    """Bind each extraction to a literal span in a user turn of THIS history.

    Each item: {session_id, turn, span:[left,right], date_span:[left,right]|None}.
    The label is the span itself, never a model-proposed canonical name. A date
    must resolve in the same asserted event clause as the item. This validates
    literal provenance, not whether extraction selected every relevant entity
    or correctly understood ownership. No implicit conversation-day date.
    """
    sessions = {s['session_id']: s for s in h['sessions']}
    result = []
    for item in items:
        sid, turn = item['session_id'], item['turn']
        if sid not in sessions:
            raise ValueError('count item session is outside this history')
        session = sessions[sid]
        if type(turn) is not int or not 0 <= turn < len(session['turns']):
            raise ValueError('count item turn is outside this session')
        source = session['turns'][turn]
        if source['role'] != 'user':
            raise ValueError('assistant statements cannot establish user inventory')
        span = item['span']
        if not isinstance(span, list) or len(span) != 2 or any(type(x) is not int for x in span):
            raise ValueError('item span must be two integer offsets')
        left, right = span
        if not 0 <= left < right <= len(source['content']):
            raise ValueError('item span is outside its source turn')
        label = source['content'][left:right]
        if not entity_key(label):
            raise ValueError('empty item identity')
        dates = []
        if item.get('date_span') is not None:
            dates = [d for d in resolve_dates(source['content'], session['date'])
                     if d['span'] == item['date_span']]
            if len(dates) != 1:
                raise ValueError('date span does not resolve in this history')
            event = next((e for e in events(source['content'], session['date'], sid, turn, 'user')
                          if e['span'] == item['date_span']), None)
            if event is None or not event['asserted'] or event['ambiguous_clause'] or any(
                    event.get(key) for key in ['recollection', 'decision', 'return', 'cancelled', 'third_party_subjects']):
                raise ValueError('date is not a directly asserted user event')
            clause_starts = [m.start() for m in re.finditer(re.escape(event['text']), source['content'])]
            if not any(a <= left < right <= a + len(event['text']) and
                       a <= item['date_span'][0] < item['date_span'][1] <= a + len(event['text'])
                       for a in clause_starts):
                raise ValueError('date belongs to another event clause')
        result.append({'label': label, 'key': entity_key(label), 'session_id': sid, 'turn': turn,
                       'span': span[:], 'session_date': session['date'],
                       'date': dates[0] if dates else None})
    return result


def count_distinct(h, items, window=None):
    """Return an auditable count of the supplied grounded item set.

    window is an inclusive pair of ISO days. Unknown dates, inferred dates and
    intervals crossing its boundaries leave the period count unresolved. A
    repeated entity with one definitely inside-window occurrence is counted
    once, even if its other mentions have uncertain dates. An unknown entity
    cannot be silently removed from a period count.
    """
    start = end = None
    if window is not None:
        start, end = map(parse_date, window)
        if start > end:
            raise ValueError('counting window is reversed')
    grouped = defaultdict(list)
    for item in grounded_items(h, items):
        grouped[item['key']].append(item)
    counted, uncertain = [], []
    for key, mentions in grouped.items():
        inside, ambiguous = [], []
        for item in mentions:
            date = item['date']
            if window is None:
                inside.append(item)
            elif date is None or date['precision'] == 'inferred':
                ambiguous.append(item)
            else:
                a, b = parse_date(date['start']), parse_date(date['end'])
                if start <= a <= b <= end:
                    inside.append(item)
                elif not (b < start or a > end):
                    ambiguous.append(item)
        if inside:
            # Repeated chunks or citations preserve provenance without adding
            # another entity. A mention's identity includes the actual source span.
            unique = {}
            for item in inside:
                unique[(item['session_id'], item['turn'], tuple(item['span']))] = item
            counted.append({'key': key, 'label': inside[0]['label'], 'mentions': list(unique.values())})
        elif ambiguous:
            uncertain.append({'key': key, 'label': mentions[0]['label'], 'mentions': ambiguous})
    return {'count': len(counted) if not uncertain else None, 'lower_bound': len(counted),
            'upper_bound': len(counted) + len(uncertain), 'items': counted, 'uncertain_items': uncertain,
            'sources': list(dict.fromkeys(m['session_id'] for e in counted for m in e['mentions'])),
            'scope': 'supplied_grounded_items', 'history_coverage_verified': False,
            'item_semantics_verified': False}
