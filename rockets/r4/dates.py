"""R4 fork of the date block in R1 memsys.py (de158d5), extended with intervals.

No dates are cached by session id. Ambiguous expressions remain intervals;
only exact, explicitly grounded days may enter an exact duration calculation.
"""
import calendar
import re
from datetime import date, datetime, timedelta

EPOCH = date(2022, 12, 31)
MONTHS = {m: i for i, m in enumerate('jan feb mar apr may jun jul aug sep oct nov dec'.split(), 1)}
WEEKDAYS = 'monday tuesday wednesday thursday friday saturday sunday'.split()
NUMBERS = dict(zip('zero one two three four five six seven eight nine ten eleven twelve'.split(), range(13)))
NUMBERS.update({'a': 1, 'an': 1, 'a couple of': 2})
MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
NUMBER = r'(?:\d+|a couple of|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
PATTERNS = [
    ('iso', re.compile(r'\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b')),
    ('month_day', re.compile(rf'\b({MONTH})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b', re.I)),
    ('day_month', re.compile(rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH})\.?(?:,?\s+(20\d{{2}}))?\b', re.I)),
    ('offset', re.compile(rf'\b({NUMBER})\s+(days?|weeks?|months?|years?|weekends?)\s+(ago|earlier|later|from now)\b', re.I)),
    ('weekday', re.compile(r'\b(last|this|next|past)\s+(' + '|'.join(WEEKDAYS) + r')\b', re.I)),
    ('period', re.compile(r'\b(last|this|next|past)\s+(weekend|week|month|year)\b', re.I)),
    ('relative', re.compile(r'\b(day before yesterday|day after tomorrow|yesterday|today|tonight|this morning|tomorrow)\b', re.I)),
    ('ordinal', re.compile(r'\bthe\s+(\d{1,2})(?:st|nd|rd|th)\b', re.I)),
]


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10].replace('/', '-'))


def shift_months(day, amount):
    serial = day.year * 12 + day.month - 1 + amount
    year, month = divmod(serial, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def number(value):
    return int(value) if value.isdigit() else NUMBERS[value.lower()]


def _resolve(kind, match, base, text):
    groups = match.groups()
    inferred = False
    if kind == 'iso':
        start = end = date(*map(int, groups))
    elif kind in ('month_day', 'day_month'):
        mon, day, year = groups if kind == 'month_day' else (groups[1], groups[0], groups[2])
        start = end = date(int(year or base.year), MONTHS[mon.lower()[:3]], int(day))
        # An omitted year could refer to another year. Annotate, never assert exact arithmetic.
        inferred = year is None
    elif kind == 'relative':
        offset = {'day before yesterday': -2, 'yesterday': -1, 'today': 0, 'tonight': 0,
                  'this morning': 0, 'tomorrow': 1, 'day after tomorrow': 2}[groups[0].lower()]
        start = end = base + timedelta(days=offset)
    elif kind == 'weekday':
        modifier, weekday = (g.lower() for g in groups)
        target = WEEKDAYS.index(weekday)
        if modifier in ('last', 'past'):
            offset = -((base.weekday() - target) % 7 or 7)
        elif modifier == 'next':
            offset = (target - base.weekday()) % 7 or 7
        else:
            offset = target - base.weekday()
        start = end = base + timedelta(days=offset)
    elif kind == 'offset':
        quantity, unit, direction = groups
        n = number(quantity)
        unit = unit.lower().rstrip('s')
        sign = -1 if direction.lower() in ('ago', 'earlier') else 1
        if unit == 'weekend':
            # "two weekends ago": Saturday and Sunday of the second preceding weekend.
            saturday = base - timedelta(days=(base.weekday() - 5) % 7)
            if saturday + timedelta(days=1) >= base:
                saturday -= timedelta(days=7)
            start = saturday + timedelta(days=(n - 1) * 7 * sign) if sign < 0 else saturday + timedelta(days=n * 7)
            end = start + timedelta(days=1)
        elif unit in ('month', 'year'):
            start = end = shift_months(base, sign * n * (12 if unit == 'year' else 1))
            inferred = True  # conversational month/year offsets need not be anniversary dates
        else:
            start = end = base + timedelta(days=sign * n * (7 if unit == 'week' else 1))
        if direction.lower() in ('earlier', 'later'):
            inferred = True  # may refer to an event elsewhere in the text, not the session date
    elif kind == 'period':
        modifier, unit = (g.lower() for g in groups)
        offset = {'last': -1, 'past': -1, 'this': 0, 'next': 1}[modifier]
        if unit == 'weekend':
            saturday = base + timedelta(days=5 - base.weekday())
            start = saturday + timedelta(days=offset * 7)
            if modifier in ('last', 'past') and base.weekday() < 5:
                start = saturday - timedelta(days=7)
            end = start + timedelta(days=1)
        elif unit == 'week':
            start = base - timedelta(days=base.weekday()) + timedelta(days=offset * 7)
            end = start + timedelta(days=6)
        elif unit == 'month':
            start = shift_months(base.replace(day=1), offset)
            end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        else:
            start, end = date(base.year + offset, 1, 1), date(base.year + offset, 12, 31)
    else:  # bare ordinal: choose last/next occurrence, but mark the inferred month
        day = int(groups[0])
        future = bool(re.search(r'\b(will|going to|plan|next|upcoming)\b', text[:match.start()], re.I))
        month_base = base
        for _ in range(13):
            try:
                candidate = month_base.replace(day=day)
                if (future and candidate >= base) or (not future and candidate <= base):
                    start = end = candidate
                    break
            except ValueError:
                pass
            month_base = shift_months(month_base.replace(day=1), 1 if future else -1)
        else:
            raise ValueError('invalid ordinal')
        inferred = True
    return start, end, inferred


def resolve_dates(text, session_date):
    """Return spans with ISO bounds, provenance and precision; invalid dates are ignored."""
    base = parse_date(session_date)
    found = []
    occupied = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if any(match.start() < right and match.end() > left for left, right in occupied):
                continue
            try:
                start, end, inferred = _resolve(kind, match, base, text)
            except (ValueError, OverflowError):
                continue
            occupied.append(match.span())
            found.append({'span': list(match.span()), 'expression': match.group(), 'start': start.isoformat(),
                          'end': end.isoformat(), 'precision': 'inferred' if inferred else 'day' if start == end else 'range',
                          'rule': kind, 'session_date': str(session_date)})
    return sorted(found, key=lambda item: item['span'][0])


def annotate_dates(text, session_date):
    for item in reversed(resolve_dates(text, session_date)):
        left, right = item['span']
        start, end = item['start'], item['end']
        label = f'{start}, day {(parse_date(start) - EPOCH).days}' if item['precision'] == 'day' else f'{start}..{end}; {item["precision"]}'
        text = text[:right] + f' [{label}]' + text[right:]
    return text
