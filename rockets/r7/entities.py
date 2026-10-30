"""Specific entities of a question and whole-phrase checks against evidence text.

An entity is what makes a question about THIS fact and not a near-miss: a proper name ("Dr. Johnson", "Shinjuku",
"Software Engineer Manager"), a quoted title ('Sapiens'), a camel-case product ("iPad case"), or a lowercase noun
phrase ("table tennis", "egg tarts", "my hamster"). Matching is on whole words with a light stem, so "Korea" does
not match "Korean" and "tarts" matches "tart".
"""
import re

STOP = set("""a an the and or but if of to in on at for with from by about as is are was were be been being am do does
did have has had i me my mine we our you your yours he she it its they them their this that these those what which who
whom whose when where why how there here than then so too very can could would should will shall may might must not no
just also any some all each other into over after before up down out off again once ever now much many more most
tell told remember recall name named called""".split())

# Words that frame a question but never identify its fact.
FRAME = set("""many much long often time times day days week weeks month months year years total first last ago past
recently recent current currently new old different initially usually typically ever previous next later earlier
number amount kind type sort lot get got go went going take took make made do doing done spend spent see saw use used
start started starting finish finished complete completed buy bought keep kept like liked want wanted think thought
said say know knew mention mentioned way thing things something one two three four five six seven eight nine ten
times per every each average left still own also both either back around away""".split())

MONTHS = set("""january february march april may june july august september october november december jan feb mar apr
jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday""".split())

DETERMINERS = set("my the a an our his her their this that these those some any".split())

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’.\-]*")


def stem(w):
    w = w.lower().replace("’", "'").strip(".'-")
    if w.endswith("'s"):
        w = w[:-2]
    for suf in ("ies", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf) and not w.endswith(("ss", "us", "is")):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


FRAME_STEMS = FRAME | {stem(w) for w in FRAME}


def words(text):
    """Stemmed whole words of a text, hyphens split ("30-gallon" -> "30", "gallon")."""
    out = []
    for tok in WORD.findall(text):
        out.extend(stem(p) for p in re.split(r"[-.]", tok) if p and p != "'s")
    return [w for w in out if w]


def _proper(tok):
    t = tok.strip("'’.")
    return bool(t) and (t[0].isupper() or bool(re.match(r"[a-z]+[A-Z]", t)))


def extract(question):
    """[{"text", "kind": "proper"|"quoted"|"np"|"run", "words": [stems]}] for one question."""
    q = question.strip()
    out, seen = [], set()

    def add(text, kind):
        ws = [w for w in words(text) if w not in STOP and w not in FRAME_STEMS and w not in MONTHS]
        key = " ".join(ws)
        if ws and key not in seen:
            seen.add(key)
            out.append({"text": text, "kind": kind, "words": ws, "head": ws[-1]})

    for m in re.finditer(r"""(?<![A-Za-z])['"‘“]([^'"’”]{2,60})['"’”](?![A-Za-z])""", q):
        add(m.group(1), "quoted")
    toks = WORD.findall(q)
    i = 0
    while i < len(toks):
        tok = toks[i]
        low = tok.lower().strip("'’.")
        if _proper(tok) and not (i == 0 and low in STOP) and low not in ("i", "i'm", "i've", "i'd") \
                and low not in MONTHS and not tok[0].isdigit():
            j = i + 1
            while j < len(toks) and toks[j].lower() not in MONTHS and (
                    _proper(toks[j]) or toks[j] in ("of", "de") or (toks[j][0].isdigit() and _proper(toks[j - 1]))):
                j += 1
            while j > i + 1 and toks[j - 1] in ("of", "de"):
                j -= 1
            add(" ".join(toks[i:j]), "proper")
            i = j
            continue
        if low in DETERMINERS:
            j = i + 1
            while j < len(toks) and j - i <= 3 and toks[j].lower() not in STOP and not _proper(toks[j]):
                j += 1
            span = toks[i + 1:j]
            if span:
                add(" ".join(span), "np")
            i = max(j, i + 1)
            continue
        i += 1
    # Content words outside the spans above ("practicing violin", "bake egg tarts"): runs of adjacent content
    # words, kept as "run" entities.
    run = []
    for tok in toks + ["."]:
        low = tok.lower().strip("'’.")
        if low and low not in STOP and low not in FRAME and low not in MONTHS and not _proper(tok) \
                and not low.endswith("ing"):
            run.append(tok)
            continue
        if run:
            add(" ".join(run), "run")
        run = []
    return out


def present(entity, text_words, text_set=None):
    """How an entity occurs in a text given as stemmed words: "phrase" (consecutive), "words" (all words, apart),
    or None (some word missing)."""
    ws = entity["words"]
    text_set = text_set if text_set is not None else set(text_words)
    if not all(w in text_set for w in ws):
        return None
    if len(ws) == 1:
        return "phrase"
    n = len(ws)
    for k in range(len(text_words) - n + 1):
        if text_words[k] == ws[0] and text_words[k:k + n] == ws:
            return "phrase"
    return "words"


def check(question, texts):
    """Each entity of the question with how it occurs in the whole of ``texts`` ({session_id: text}) and in each
    session ("in": {session_id: "phrase" | "words"}, sessions without it left out)."""
    # Entity words have function and frame words removed, so the text loses them too ("Husbands of Evelyn Hugo").
    per = {sid: [w for w in words(t) if w not in STOP and w not in FRAME_STEMS] for sid, t in texts.items()}
    sets = {sid: set(ws) for sid, ws in per.items()}
    out = []
    for e in extract(question):
        where = {sid: f for sid in per if (f := present(e, per[sid], sets[sid]))}
        allw = set().union(*sets.values()) if sets else set()
        found = "phrase" if "phrase" in where.values() else ("words" if all(w in allw for w in e["words"]) else None)
        out.append(dict(e, found=found, head_found=e["head"] in allw, **{"in": where}))
    return out
