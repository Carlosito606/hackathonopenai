"""Dates: session dates, explicit and relative dates in text tagged with a day number."""
import re
from datetime import datetime, timedelta


def parse_date(s):
    return datetime.strptime(s[:10], "%Y/%m/%d")


EPOCH = datetime(2022, 12, 31)
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
WEEKDAYS = "monday tuesday wednesday thursday friday saturday sunday".split()
_MONTH = (r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|"
          r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b\.?")
_ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
_MD = re.compile(rf"\b{_MONTH} (\d{{1,2}})(?:st|nd|rd|th)?(?:,? (20\d\d))?\b")
_DM = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)? (?:of )?{_MONTH}(?:,? (20\d\d))?\b")
_REL = re.compile(r"\b(yesterday|today|tonight|this morning|tomorrow|last (?:" + "|".join(WEEKDAYS) + r")|"
                  r"(\d+|a|one|two|three|four|five|six) (days?|weeks?) ago)\b", re.I)
_NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def day_no(d):
    return (d - EPOCH).days


def _mark(d):
    return f"{d:%Y-%m-%d}, day {day_no(d)}"


def annotate_dates(text, session_date):
    """Explicit and relative dates in ``text`` tagged with their calendar date and a day number, so that the
    difference of two day numbers is the number of days between them."""

    def explicit(y, mo, d, default_year):
        try:
            return datetime(int(y or default_year), mo, int(d))
        except ValueError:
            return None

    def sub(m, when):
        return f"{m.group(0)} [{_mark(when)}]" if when else m.group(0)

    year = session_date.year
    text = _ISO.sub(lambda m: sub(m, explicit(m.group(1), int(m.group(2)), m.group(3), year)), text)
    text = _MD.sub(lambda m: sub(m, explicit(m.group(3), MONTHS[m.group(1).lower()[:3]], m.group(2), year)), text)
    text = _DM.sub(lambda m: sub(m, explicit(m.group(3), MONTHS[m.group(2).lower()[:3]], m.group(1), year)), text)

    def rel(m):
        w = m.group(1).lower()
        if w in ("today", "tonight", "this morning"):
            off = 0
        elif w == "yesterday":
            off = -1
        elif w == "tomorrow":
            off = 1
        elif w.startswith("last "):
            off = -((session_date.weekday() - WEEKDAYS.index(w[5:])) % 7 or 7)
        else:
            n = int(m.group(2)) if m.group(2).isdigit() else _NUM[m.group(2).lower()]
            off = -n * (7 if m.group(3).lower().startswith("week") else 1)
        return f"{m.group(0)} [{_mark(session_date + timedelta(days=off))}]"

    return _REL.sub(rel, text)


TEMPORAL = re.compile(r"how many (days|weeks|months|years)|how long|when did|what date|which .*(first|earlier|later)|"
                      r"\bago\b|\border\b|before or after", re.I)
