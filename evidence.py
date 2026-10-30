"""Evidence: pack the best chunks, grouped by session in date order, into the client's evidence format."""
from dates import _mark, annotate_dates, parse_date


def build_evidence(history, cands, budget=18000, max_chunk=1000, min_score=-6.0, dates=False):
    """Pick top chunks until the budget is used; one excerpt per session in date order, in the client's evidence
    format ({"id", "date", "text"}). An assistant chunk brings the start of the user turn before it as context."""
    sessions = history["sessions"]
    chosen, used = {}, 0
    for c in cands:
        if chosen and c["score"] < min_score:
            break
        text = c["text"] if len(c["text"]) <= max_chunk else c["text"][:max_chunk] + " …"
        key = (c["si"], c["turn"])
        extra = []
        if c["role"] == "assistant" and c["turn"] > 0 and (c["si"], c["turn"] - 1) not in chosen:
            prev = sessions[c["si"]]["turns"][c["turn"] - 1]
            if prev["role"] == "user":
                extra = [((c["si"], c["turn"] - 1), prev["content"][:300] + (" …" if len(prev["content"]) > 300 else ""))]
        cost = len(text) + sum(len(t) for _, t in extra) + 60
        if used + cost > budget:
            continue
        if key in chosen:
            chosen[key] += " … " + text
        else:
            chosen[key] = text
        for k, t in extra:
            chosen[k] = t
        used += cost
    by_session = {}
    for (si, ti), text in chosen.items():
        by_session.setdefault(si, []).append((ti, text))
    evidence = []
    for si in sorted(by_session):
        s = sessions[si]
        sd = parse_date(s["date"])
        lines, last = [], None
        for ti, text in sorted(by_session[si]):
            if last is not None and ti > last + 1:
                lines.append("…")
            role = s["turns"][ti]["role"]
            lines.append(f"{role}: {annotate_dates(text, sd) if dates else text}")
            last = ti
        if dates:
            lines.insert(0, f"(this conversation: {_mark(sd)})")
        evidence.append({"id": s["session_id"], "date": s["date"], "text": "\n".join(lines)})
    return evidence
