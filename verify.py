"""Answerability check for near-miss questions: names in the question that never occur in the history."""
import re

from dates import WEEKDAYS
from retrieval import tokens

NAME = re.compile(r"(?<![.?!]\s)(?<!^)\b[A-Z][\w'-]*")
ABOUT_ME = re.compile(r"\b(I|my|me|mine)\b")
TO_ASSISTANT = re.compile(r"\byou\b|\byour\b|\bour (previous |last )?(chat|conversation)", re.I)
DATE_WORDS = set(tokens(" ".join(WEEKDAYS) + " january february march april may june july august september october "
                        "november december christmas valentine easter thanksgiving halloween"))


def _words(text):
    return tokens(text.replace("-", " "))


def missing_names(question, history):
    """Capitalized words inside the question (not the first word, not "I", months or weekdays) that occur in none of
    my turns, or of any turn when the question asks what the assistant said or is not about me. Whole tokens: "Korea"
    does not match "Korean". Common nouns ("violin") are not checked: too many paraphrases."""
    q = question.strip()
    names = [n for n in NAME.findall(q) if n != "I" and not set(_words(n)) <= DATE_WORDS]
    if not names:
        return []
    everyone = bool(TO_ASSISTANT.search(q)) or not ABOUT_ME.search(q)
    said = {w for s in history["sessions"] for t in s["turns"] if everyone or t["role"] == "user"
            for w in _words(t["content"])}
    return list(dict.fromkeys(n.removesuffix("'s") for n in names if not set(_words(n)) <= said))


if __name__ == "__main__":
    h = {"sessions": [{"turns": [{"role": "user", "content": "I lived in Harajuku and loved Korean food, Dr. Smith said"},
                                 {"role": "assistant", "content": "Shinjuku is close to Seattle-style cafes."}]}]}
    assert missing_names("How long have I lived in Shinjuku?", h) == ["Shinjuku"]
    assert missing_names("How long was I in Korea for?", h) == ["Korea"]
    assert missing_names("How often do I see Dr. Smith in June?", h) == []
    assert missing_names("What did you say about Shinjuku?", h) == []
    print("ok")
