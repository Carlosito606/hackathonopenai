"""Checks for entities.py: python rockets/r7/test_entities.py (standard library only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from entities import check, extract  # noqa: E402


def names(question):
    return [e["text"] for e in extract(question) if e["kind"] in ("proper", "quoted")]


def found(question, text, entity):
    return {e["text"]: e["found"] for e in check(question, {"s1": text})}[entity]


def main():
    assert names("Who graduated first among Emma, Rachel and Alex?") == ["Emma", "Rachel", "Alex"]
    assert names("How often do I see Dr. Johnson?") == ["Dr. Johnson"]
    assert names("Which project did I start first, the Ferrari model or the Porsche 991 Turbo S model?") == \
        ["Ferrari", "Porsche 991 Turbo S"]
    assert names("What was the airline that I flied with on Valentine's day?") == []
    assert names("Where did I complete my Bachelor's degree in Computer Science?") == ["Computer Science"]
    assert names("How many pages of 'The Seven Husbands of Evelyn Hugo' did I read?")[0] == \
        "The Seven Husbands of Evelyn Hugo"
    assert found("How long was I in Korea for?", "I loved Korean food in Japan.", "Korea") is None
    assert found("How long was I in Korea for?", "I stayed in Korea for two weeks.", "Korea") == "phrase"
    q = "How many pages of 'The Seven Husbands of Evelyn Hugo' did I read?"
    assert found(q, "I finished The Seven Husbands of Evelyn Hugo last week.", "The Seven Husbands of Evelyn Hugo") \
        == "phrase"
    q = "How often do I play table tennis with my friends?"
    tennis = [e["text"] for e in extract(q) if "tennis" in e["text"]][0]
    assert found(q, "I play tennis at the table near the park.", tennis) == "words"
    print("entities: all checks pass")


if __name__ == "__main__":
    main()
