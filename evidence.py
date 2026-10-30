"""Evidence: pack the best chunks, grouped by session in date order, into the client's evidence format."""
from dates import _mark, annotate_dates, parse_date


def build_evidence(history, cands, budget=18000, max_chunk=1000, min_score=-6.0, dates=False):
    """Pick top chunks until the budget is used; one excerpt per session in date order, in the client's evidence
    format ({"id", "date", "text"}). An assistant chunk brings the start of the user turn before it as context, and
    every chunk brings the start of the next user turn, where the user often answers or corrects ("Yes, ...")."""
    sessions = history["sessions"]
    chosen, used = {}, 0

    def user_start(si, ti):
        turns = sessions[si]["turns"]
        if 0 <= ti < len(turns) and turns[ti]["role"] == "user" and (si, ti) not in chosen:
            t = turns[ti]["content"]
            return [((si, ti), t[:300] + (" …" if len(t) > 300 else ""))]
        return []

    for c in cands:
        if chosen and c["score"] < min_score:
            break
        text = c["text"] if len(c["text"]) <= max_chunk else c["text"][:max_chunk] + " …"
        key = (c["si"], c["turn"])
        extra = user_start(c["si"], c["turn"] - 1) if c["role"] == "assistant" else []
        extra += user_start(c["si"], c["turn"] + (1 if c["role"] == "assistant" else 2))
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
