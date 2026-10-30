"""Question forms, grounded event matching and calendar arithmetic. No model or gold input."""
import re

from .dates import parse_date, resolve_dates

STOP = set('a an the and or to of on at for from in with my me i did do does was were is are have has had been be '
           'day days week weeks month months year years how many much long ago since before after between '
           'when which what event events first last earliest latest order happened participate participated '
           'attend attended started start decided mentioned bought buy got get take took going went visit visited'.split())


def words(text):
    out = []
    text = re.sub(r'\bcancelled\b', 'canceled', text, flags=re.I)
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in STOP or len(word) < 3:
            continue
        for suffix in ('ing', 'ied', 'ed', 'es', 's'):
            if len(word) > len(suffix) + 3 and word.endswith(suffix):
                word = word[:-len(suffix)] + ('y' if suffix == 'ied' else '')
                break
        out.append(word)
    return set(out)


def classify(question):
    q = question.strip().rstrip('?.')
    unit_match = re.search(r'\b(days?|weeks?|months?|years?)\b', q, re.I)
    unit = unit_match.group(1).lower().rstrip('s') if unit_match else 'day'
    result = {'form': 'lookup', 'unit': unit, 'anchors': []}
    # Strong separators avoid splitting an event title containing an ordinary "and".
    match = re.search(r'\bbetween (.+?) and (?:the day )?(.+)', q, re.I)
    if match:
        result.update(form='between', anchors=list(match.groups()))
        return result
    match = re.search(r'\bsince (.+?) when (.+)', q, re.I)
    if match:
        result.update(form='between', anchors=list(match.groups()))
        return result
    match = re.search(r'\bbefore (.+?) did (.+)', q, re.I)
    if match:
        result.update(form='between', anchors=[match.group(2), match.group(1)], require_forward=True)
        return result
    match = re.search(r'\b(?:ago did I|ago have I) (.+?) when (.+)', q, re.I)
    if match:
        result.update(form='between', anchors=list(match.groups()))
        return result
    match = re.search(r'\b(?:how long|how many weeks) (?:had|have) I been (.+?) when (.+)', q, re.I)
    if not match:
        match = re.search(r'\bhow long (?:did I|have I been|had I been) (.+?) before (.+)', q, re.I)
    if match:
        result.update(form='between', anchors=list(match.groups()))
        return result
    if re.search(r'\b(first|earlier|most recently|earliest|latest|order)\b', q, re.I):
        tail = re.split(r':\s*|\bamong\s+', q, maxsplit=1, flags=re.I)
        among = bool(re.search(r'\bamong\s+', q, re.I))
        if len(tail) == 1:
            tail = re.split(r'\bfirst\s*,', q, maxsplit=1, flags=re.I)
        delimiter = r',\s*(?:and )?|\s+(?:or|and)\s+' if among else r',\s*(?:and )?|\s+or\s+'
        anchors = re.split(delimiter, tail[-1]) if len(tail) > 1 else []
        if len(anchors) < 2:
            anchors = re.findall(r"['\"]([^'\"]+)['\"]", q)
        result.update(form='order', anchors=[a.strip() for a in anchors if words(a)],
                      direction='latest' if re.search('recent|latest', q, re.I) else 'earliest',
                      order_output='list' if re.search(r'\border\b|first to last|earliest to latest|second and third', q, re.I) else 'winner')
        return result
    match = re.search(r'\b(?:ago did I|ago have I|passed since I|since I last)\s+(.+)', q, re.I)
    if match:
        result.update(form='elapsed', anchors=[match.group(1)])
    elif re.search(r'\bhow many\b|\btotal\b', q, re.I) and not unit_match:
        result.update(form='count', anchors=[q])
    elif re.search(r'\bhow long\b|how many (?:days|weeks|months|years)', q, re.I):
        result.update(form='duration')
    return result


def events(text, session_date, session_id, turn, role):
    """Keep the sentence and the exact date span together, with source identifiers."""
    out = []
    for item in resolve_dates(text, session_date):
        left, right = item['span']
        boundaries = [0] + [m.end() for m in re.finditer(r'[.!?]\s+|\n', text)] + [len(text)]
        start = max(b for b in boundaries if b <= left)
        end = min(b for b in boundaries if b >= right)
        clause = text[start:end].strip()
        # Planned and hypothetical events must not become statements that an event happened.
        planned = bool(re.search(r"\b(will|going to|planning to|plan to|hope to|hoping to|would|might|if)\b", clause, re.I))
        negated = bool(re.search(r"\b(didn't|did not|never|haven't|have not)\b", clause, re.I))
        cancelled = bool(re.search(r'\bcancell?ed\b', clause, re.I))
        relevant = [d for d in resolve_dates(clause, session_date) if d['precision'] == 'day']
        # Several different dates in one sentence cannot be assigned to individual events by proximity alone.
        ambiguous = len({d['start'] for d in relevant}) > 1
        subjects = re.findall(r'\b([Mm]y (?:friend|cousin|sister|brother|aunt|uncle|mother|father)|'
                              r'he|she|they|[A-Z][a-z]+)\s+(?:has |had |just )?'
                              r'(?:visited|attended|bought|finished|started|joined|graduated|became)\b', clause)
        subjects = [s for s in subjects if s.lower() not in ('i', 'we')]
        future = parse_date(item['start']) > parse_date(session_date)
        out.append({**item, 'session_id': session_id, 'turn': turn, 'role': role, 'text': clause,
                    'asserted': not planned and not negated and not future and role == 'user', 'ambiguous_clause': ambiguous,
                    'cancelled': cancelled, 'third_party_subjects': subjects})
    return out


def match_event(anchor, pool):
    tokens = words(anchor)
    if not tokens:
        return None
    choices = []
    for event in pool:
        if not event['asserted'] or event['precision'] != 'day' or event['ambiguous_clause']:
            continue
        if event.get('cancelled') and not re.search(r'\bcancel', anchor, re.I):
            continue
        if any(not words(subject) or not (words(subject) <= tokens) for subject in event.get('third_party_subjects', [])):
            continue
        matched = tokens & words(event['text'])
        coverage = len(matched) / len(tokens)
        if coverage < 0.75 or len(matched) < min(2, len(tokens)):
            continue
        # Names, quoted titles and numbers in the anchor must all be present, not merely similar.
        names = re.findall(r'\b[A-Z][a-z]+\b|\b\d+\b', anchor)
        if any(not (words(name) <= words(event['text'])) for name in names if words(name)):
            continue
        choices.append((coverage, len(matched), event))
    if not choices:
        return None
    choices.sort(key=lambda item: (-item[0], -item[1]))
    best = choices[0]
    tied = [e for coverage, count, e in choices if coverage == best[0] and count == best[1]]
    if len({e['start'] for e in tied}) > 1:
        return None  # repeated activities and conflicting dates need semantic disambiguation
    return best[2]


def calendar_difference(start, end, unit):
    a, b = parse_date(start), parse_date(end)
    days = abs((b - a).days)
    if unit == 'day':
        return f'{days} days'
    if unit == 'week':
        value = days / 7
        return f'{value:g} weeks ({days} days)'
    if b < a:
        a, b = b, a
    months = (b.year - a.year) * 12 + b.month - a.month
    if b.day < a.day:
        months -= 1
    if unit == 'month':
        return f'{months} complete calendar months ({days} days)'
    years = months // 12
    return f'{years} complete calendar years ({days} days)'


def compute(question, question_date, pool):
    form = classify(question)
    anchors = form['anchors']
    result = {'form': form['form'], 'unit': form['unit'], 'computed': False, 'sources': [], 'facts': '',
              'reason': 'unsupported_or_ambiguous_question_form'}
    if form['form'] not in ('between', 'elapsed', 'order') or not anchors:
        return result
    selected = [match_event(anchor, pool) for anchor in anchors]
    if any(event is None for event in selected):
        result['reason'] = 'missing_or_ambiguous_event_date'
        return result
    if form['form'] == 'between' and len({(e['session_id'], e['turn'], tuple(e['span'])) for e in selected}) < 2:
        result['reason'] = 'same_event_matched_twice'
        return result
    sources = list(dict.fromkeys(e['session_id'] for e in selected))
    facts = [f'{anchor}: {event["start"]} (source {event["session_id"]}, turn {event["turn"]}; '
             f'expression {event["expression"]!r})' for anchor, event in zip(anchors, selected)]
    answer = ''
    if form['form'] in ('between', 'elapsed'):
        end = selected[1]['start'] if len(selected) > 1 else parse_date(question_date).isoformat()
        if form.get('require_forward') and parse_date(selected[0]['start']) > parse_date(end):
            result['reason'] = 'before_premise_not_supported'
            return result
        if form['form'] == 'elapsed' and parse_date(selected[0]['start']) > parse_date(end):
            result['reason'] = 'event_after_question'
            return result
        answer = calendar_difference(selected[0]['start'], end, form['unit'])
        facts.append(f'Computed: {answer} between {selected[0]["start"]} and {end}.')
    else:
        if len(selected) < 2 or len({e['start'] for e in selected}) != len(selected):
            result['reason'] = 'order_not_strict'
            return result
        ordered = sorted(zip(anchors, selected), key=lambda item: item[1]['start'])
        chronology = ' -> '.join(anchor for anchor, _event in ordered)
        answer = chronology if form['order_output'] == 'list' else ordered[-1 if form['direction'] == 'latest' else 0][0]
        facts.append('Computed chronological order (earliest to latest): ' + chronology + '.')
        facts.append('Computed answer to the ordering question: ' + answer + '.')
    result.update(computed=True, sources=sources, facts='\n'.join(facts), answer=answer, reason='grounded_exact_dates')
    return result
