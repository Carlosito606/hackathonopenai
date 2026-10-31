"""Dates: session dates, explicit and relative dates in text tagged with a day number."""
import calendar
import re
from datetime import datetime, timedelta


def parse_date(s):
    return datetime.strptime(s[:10], "%Y/%m/%d")


EPOCH = datetime(2022, 12, 31)
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
WEEKDAYS = "monday tuesday wednesday thursday friday saturday sunday".split()
_MONTH = (r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|"
          r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b\.?")
_WD = "(" + "|".join(WEEKDAYS) + ")"
_N = r"(\d{1,3}|an?|one|two|three|four|five|six|seven|eight|nine|ten|a couple of|a few)"
_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
        "nine": 9, "ten": 10, "a couple of": 2, "a few": 3}
_VAGUE = ("a couple of", "a few")
_ISO = re.compile(r"\b(20\d\d)[-/](\d\d)[-/](\d\d)\b")
# "June 3rd", "May 3-5", "Jan 15th, 2023"
_MD = re.compile(rf"\b{_MONTH} (\d{{1,2}})(?:st|nd|rd|th)?(?: ?(?:-|–|to|through) ?(\d{{1,2}})(?:st|nd|rd|th)?)?"
                 rf"(?:,? (20\d\d))?\b")
# "3 May", "the 10th of June", "the 20th to the 27th of April"
_DM = re.compile(rf"\b(?:the )?(\d{{1,2}})(?:st|nd|rd|th)?(?: ?(?:-|–|to|through|until) ?(?:the )?(\d{{1,2}})"
                 rf"(?:st|nd|rd|th)?)? (?:of )?{_MONTH}(?:,? (20\d\d))?\b")
_SLASH = re.compile(r"\b(?:on|since|from|until|by|before|after) (\d{1,2})/(\d{1,2})(?:/(20\d\d|\d\d))?\b(?![/\d])",
                    re.I)
_ORD_REL = re.compile(r"\bthe (\d{1,2})(?:st|nd|rd|th) of (last|this|next) month\b", re.I)
_ON_ORD = re.compile(r"\bon the (\d{1,2})(?:st|nd|rd|th)\b(?! of)")
_IN_MONTH = re.compile(rf"\b(?i:in|of|during|since|early|late|mid-?) {_MONTH}")
_REL = re.compile(
    r"\b(the day before yesterday|the day after tomorrow|yesterday|today|tonight|tomorrow|last night|"
    r"this (?:morning|afternoon|evening)|"
    rf"{_N} (days?|weeks?|weekends?|months?|years?) ago|(?<!the )(last|next) (week|month|year))\b", re.I)
_WEEKEND = re.compile(r"\b(last|this past|past|this coming|this|coming|next|over the|on the) weekend\b", re.I)
_WDAY = re.compile(rf"\b(last|this past|past|this coming|this|coming|next|on|by|until|before|since|due) {_WD}\b"
                   rf"(?! (?:morning|afternoon|evening|night)s\b)(?! ?(?:-|–|to|through|and|or|/|,) ?{_WD})", re.I)
_WDAY_LW = re.compile(rf"\b(?:on )?{_WD},? (?:of )?last week\b|\blast week,? on {_WD}\b", re.I)
_FUTURE = re.compile(r"\b(will|won['’]t|going to|gonna|plan(?:ning|ned)?|need to|want to|have to|hop(?:e|ing) to|"
                     r"scheduled|coming up|upcoming|next|tomorrow|should|is on|are on|due|can['’]t wait|can|could|"
                     r"maybe|might|would|(?:I|we)['’](?:m|re) (?:heading|going|leaving|flying|driving|meeting|visiting|"
                     r"hosting|taking|attending|starting|moving|travell?ing))\b|['’]ll\b|['’]d like\b", re.I)
_PAST = re.compile(r"\b(was|were|did|had|went|(?<!['’]ve )(?<!have )got|came|made|saw|took|bought|ran|ate|met|left|"
                   r"found|gave|told|said|felt|spent|ago|last|yesterday|(?!need\b)\w+ed)\b", re.I)
_PRESENT = re.compile(r"\b(has|have|is|are|am)\b|['’](?:s|re|m|ve got)\b", re.I)


def day_no(d):
    return (d - EPOCH).days


def _mark(d):
    return f"{d:%Y-%m-%d}, day {day_no(d)}"


def _add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    return d.replace(year=y, month=m + 1, day=min(d.day, calendar.monthrange(y, m + 1)[1]))


def _date(y, mo, d, sd, tense=0):
    """The calendar date. Without a year: for a past event (tense -1) the latest one up to 60 days after the session
    date, for a future one (+1) the earliest from 60 days before, else the nearest one."""
    years = [int(y) + (2000 if len(str(y)) == 2 else 0)] if y else [sd.year + k for k in (-1, 0, 1)]
    cands = []
    for year in years:
        try:
            cands.append(datetime(year, int(mo), int(d)))
        except ValueError:
            pass
    if y or not cands:
        return cands[0] if cands else None
    if tense > 0:
        return next((c for c in cands if c >= sd - timedelta(days=60)), None)
    if tense < 0:
        return ([None] + [c for c in cands if c <= sd + timedelta(days=60)])[-1]
    return min(cands, key=lambda c: abs((c - sd).days))


def _tense(text, i, present=False):
    """+1 if the sentence up to the end of the clause at position ``i`` talks about something still to come, -1 if
    it is in the past, 0 if it does not say; the cue nearest to ``i`` wins. ``present``: present tense counts as
    future ("the team has a game on Saturday")."""
    a = max(text.rfind(c, 0, i) for c in ".!?\n") + 1
    b = min((j for j in (text.find(c, i) for c in ".!?\n,;") if j >= 0), default=len(text))
    cues = [(min(abs(m.start() - i), abs(m.end() - i)), sign)
            for pat, sign in ((_FUTURE, 1), (_PAST, -1)) for m in pat.finditer(text, a, b)]
    if cues:
        return min(cues)[1]
    return 1 if present and _PRESENT.search(text, a, b) else 0


def annotate_dates(text, session_date):
    """Explicit and relative dates in ``text`` tagged with their calendar date and a day number, so that the
    difference of two day numbers is the number of days between them. Vague ones ("last month", "a few weeks ago")
    are tagged "about"; ranges get both ends."""
    sd = session_date.replace(hour=0, minute=0, second=0, microsecond=0)
    found = []  # (start, end, tag)

    def add(m, d, d2=None, about=False):
        if d and (d2 is None or d2 >= d):
            tag = _mark(d) + (f" to {_mark(d2)}" if d2 and d2 != d else "")
            found.append((m.start(), m.end(), ("about " if about else "") + tag))

    for m in _ISO.finditer(text):
        add(m, _date(m.group(1), m.group(2), m.group(3), sd))
    for m in _MD.finditer(text):
        mo = MONTHS[m.group(1).lower()[:3]]
        d = _date(m.group(4), mo, m.group(2), sd, _tense(text, m.start()))
        add(m, d, m.group(3) and d and _date(d.year, mo, m.group(3), sd))
    for m in _DM.finditer(text):
        mo = MONTHS[m.group(3).lower()[:3]]
        if m.group(2):
            d2 = _date(m.group(4), mo, m.group(2), sd, _tense(text, m.start()))
            add(m, d2 and _date(d2.year, mo, m.group(1), sd), d2)
        else:
            add(m, _date(m.group(4), mo, m.group(1), sd, _tense(text, m.start())))
    for m in _SLASH.finditer(text):
        if 1 <= int(m.group(1)) <= 12:
            add(m, _date(m.group(3), m.group(1), m.group(2), sd, _tense(text, m.start())))
    for m in _ORD_REL.finditer(text):
        base = _add_months(sd, {"last": -1, "this": 0, "next": 1}[m.group(2).lower()])
        add(m, _date(base.year, base.month, m.group(1), sd))
    for m in _ON_ORD.finditer(text):
        a = max(text.rfind(c, 0, m.start()) for c in ".!?\n") + 1
        months = list(_IN_MONTH.finditer(text, a, m.start()))
        if months:
            add(m, _date(None, MONTHS[months[-1].group(1).lower()[:3]], m.group(1), sd, _tense(text, m.start())))

    for m in _REL.finditer(text):
        w = m.group(0).lower()
        if m.group(2):
            n, unit = m.group(2).lower(), m.group(3).lower()
            k = int(n) if n.isdigit() else _NUM[n]
            about = n in _VAGUE or unit.startswith(("month", "year"))
            if unit.startswith("day"):
                d = sd - timedelta(days=k)
            elif unit.startswith("weekend"):
                back = (sd.weekday() - 5) % 7
                d = sd - timedelta(days=back + (7 if back <= 1 else 0) + 7 * (k - 1))
            elif unit.startswith("week"):
                d = sd - timedelta(days=7 * k)
            else:
                d = _add_months(sd, -k * (12 if unit.startswith("year") else 1))
            add(m, d, about=about)
        elif m.group(4):
            sign, unit = -1 if m.group(4).lower() == "last" else 1, m.group(5).lower()
            if unit == "week":
                add(m, sd + timedelta(days=7 * sign), about=True)
            else:
                add(m, _add_months(sd, sign * (12 if unit == "year" else 1)), about=True)
        else:
            off = {"the day before yesterday": -2, "the day after tomorrow": 2, "yesterday": -1, "last night": -1,
                   "tomorrow": 1}.get(w, 0)
            add(m, sd + timedelta(days=off))
    for m in _WEEKEND.finditer(text):
        how = m.group(1).lower()
        back = (sd.weekday() - 5) % 7  # days since the latest Saturday: Sat 0, Sun 1, Mon 2 ...
        this = sd - timedelta(days=back) if back <= 1 else sd + timedelta(days=7 - back)
        if back == 1 and _tense(text, m.start(), True) > 0:
            this = sd  # "this weekend" said on Sunday about later today
        if how == "last":
            d = sd - timedelta(days=back + (7 if back <= 1 else 0))
        elif how in ("this past", "past") or (how in ("over the", "on the") and _tense(text, m.start(), True) <= 0):
            d = sd - timedelta(days=back)
        else:
            d = this + timedelta(days=7 if how == "next" else 0)
        add(m, d, about=how == "next")
    for m in _WDAY.finditer(text):
        how, wd = m.group(1).lower(), WEEKDAYS.index(m.group(2).lower())
        if re.search(_WD, text[max(0, m.start() - 15):m.start()], re.I):
            continue  # "Monday and on Wednesday": a schedule, not one day
        back, ahead = (sd.weekday() - wd) % 7, (wd - sd.weekday()) % 7
        if how in ("last", "this past", "past", "since") or (how == "on" and _tense(text, m.start(), True) <= 0):
            d = sd - timedelta(days=back or 7)
        else:
            d = sd + timedelta(days=ahead or (7 if how in ("next", "coming", "this coming", "on") else 0))
        add(m, d)
    for m in _WDAY_LW.finditer(text):
        wd = WEEKDAYS.index((m.group(1) or m.group(2)).lower())
        add(m, sd - timedelta(days=sd.weekday() + 7 - wd))

    out, pos = [], 0
    for s, e, tag in sorted(found, key=lambda f: (f[0], f[0] - f[1])):
        if s < pos:
            continue
        out.append(f"{text[pos:e]} [{tag}]")
        pos = e
    return "".join(out) + text[pos:]


TEMPORAL = re.compile(r"how many (days|weeks|months|years)|how long|when did|what date|which .*(first|earlier|later)|"
                      r"\bago\b|\border\b|before or after|most recently|\bfirst\b.*\bor\b|\bfirst, second\b|"
                      rf"\b(?:last|past) (?:week|weekend|month|{_WD[1:-1]})\b", re.I)
