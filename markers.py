"""
Signal three: the stock-phrase signal. (Stretch feature, declared in README.)

Signal one asks "how predictable is this text?" and signal two asks "what
shape is it?". This one asks a third, different question: **does it use the
stock phrases chat models reach for?** Things like "it is important to note",
"plays a significant role", "in today's fast-paced world".

It's used by app.py's /submit route, and its score is one of the three inputs
to scoring.combine_signals.

Why it might work: a chat model is trained to sound safe, helpful, and
organised, so it leans on the same transitions and hedges over and over.
Most people writing about their own life or opinions don't say "it is
important to note".

⚠️ The blind spot: it only knows the phrases on its list. One paraphrase pass
("note that" instead of "it is important to note") removes every marker, and
a person trained in corporate or academic writing uses many of these phrases
naturally. The list is English only.

Try it from a terminal:

    python markers.py "some text to look at"
"""

import math
import re

import stylometry

# Each entry is (phrase, weight). Matching is case-insensitive and on whole
# words, so "firstly" doesn't match inside "firstlyish".
#
# Weight 1.0: multi-word clichés that rarely appear in casual human writing.
# Weight 0.5: single connective words humans also use, just less often than
#             chat models do. Counting them at full weight would accuse anyone
#             who writes "Additionally" in a cover letter.
MARKERS = [
    # Openers and framing
    ("in today's fast-paced", 1.0),
    ("in today's world", 1.0),
    ("in today's digital age", 1.0),
    ("in the modern era", 1.0),
    ("cannot be overstated", 1.0),
    ("it is important to note", 1.0),
    ("it's important to note", 1.0),
    ("it is worth noting", 1.0),
    ("it's worth noting", 1.0),
    ("it is essential to", 1.0),
    ("plays a significant role", 1.0),
    ("plays a crucial role", 1.0),
    ("plays a vital role", 1.0),
    ("plays a key role", 1.0),
    ("a wide variety of", 1.0),
    ("a wide range of", 1.0),
    ("several key", 1.0),
    ("is widely considered", 1.0),
    ("are better positioned to", 1.0),
    ("navigate the complexities", 1.0),
    ("delve into", 1.0),
    ("a testament to", 1.0),
    ("in conclusion", 1.0),
    ("overall, ", 1.0),
    ("ultimately, ", 1.0),
    ("by doing so", 1.0),
    ("foster a", 1.0),
    ("seamless", 1.0),
    ("leverage", 1.0),
    # Half weight: single connectives, and phrases ordinary human writing
    # also uses fairly often
    ("the importance of", 0.5),
    ("ensure that", 0.5),
    ("additionally", 0.5),
    ("furthermore", 0.5),
    ("moreover", 0.5),
    ("first, ", 0.5),
    ("second, ", 0.5),
    ("finally, ", 0.5),
    ("essential", 0.5),
    ("crucial", 0.5),
]

# How fast the score rises with the marker rate. With SCALE = 2.0:
#   0 weighted markers per 100 words -> 0.00
#   1 per 100 words                  -> 0.39
#   2 per 100 words                  -> 0.63
#   4 per 100 words                  -> 0.86
# One stray "Additionally" in a 100-word paragraph is 0.5 per 100 words, which
# scores only 0.22, so a single connective can't push a writer toward "AI".
SCALE = 2.0


def _pattern(phrase: str) -> re.Pattern:
    """
    Turn a phrase into a case-insensitive whole-word regex.

    \\b is a regex "word boundary": the edge between a letter and a space or
    punctuation. Phrases ending in ", " already end on a boundary, so they
    don't get a trailing \\b (it would never match after a space).
    """
    escaped = re.escape(phrase.strip())
    tail = "" if phrase.endswith(" ") else r"\b"
    # Curly apostrophes (’) are what phones type; treat them like straight ones.
    escaped = escaped.replace("'", "['’]")
    return re.compile(r"\b" + escaped + tail, re.IGNORECASE)


_COMPILED = [(phrase, weight, _pattern(phrase)) for phrase, weight in MARKERS]


def find_markers(text: str) -> list[tuple[str, int, float]]:
    """Every marker present, as (phrase, how many times, weight)."""
    found = []
    for phrase, weight, pattern in _COMPILED:
        count = len(pattern.findall(text))
        if count:
            found.append((phrase.strip(), count, weight))
    return found


def marker_rate(text: str) -> float:
    """Weighted markers per 100 words, so long and short texts compare fairly."""
    total_words = len(stylometry.words(text))
    if total_words == 0:
        return 0.0
    weighted = sum(count * weight for _, count, weight in find_markers(text))
    return weighted / total_words * 100


def marker_signal(text: str) -> float:
    """
    The stock-phrase signal as a 0-1 score. **Higher means more likely AI.**

    1 - e^(-rate / SCALE) starts at 0 when there are no markers, rises quickly
    for the first few, and flattens toward 1 instead of shooting past it, so a
    text stuffed with clichés can't score above 1.0.
    """
    return round(1.0 - math.exp(-marker_rate(text) / SCALE), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "In today's fast-paced world, it is important to note that time "
        "management plays a crucial role in success. Additionally, it is "
        "essential to prioritize tasks."
    )
    for phrase, count, weight in find_markers(text):
        print(f"  {count} x {phrase!r} (weight {weight})")
    print(f"marker_rate     {marker_rate(text):.2f} per 100 words")
    print(f"marker_signal   {marker_signal(text)}   (higher = more likely AI)")
