"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics

# Window size for the moving-average type-token ratio (see type_token_ratio).
# 40 matches config.MIN_WORDS, so every accepted submission fills at least one
# full window.
TTR_WINDOW = 40

# The punctuation punctuation_density counts. Full stops and commas are left
# out on purpose. "—" is an em dash, "–" an en dash, "…" an
# ellipsis character, and the curly quotes are what word processors and phones
# type instead of straight ones. A three-dot "..." counts as three marks.
EXPRESSIVE_PUNCTUATION = [
    ";", ":", "—", "–", " - ", "(", ")", "!", "?",
    '"', "“", "”", "‘", "’", "…", "...",
]


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies. ← TODO

    Returns:
        A float. Decide yourself what scale it's on and which direction means
        "more human" — then write that down, because your combining rule
        depends on knowing it.

    A hint on what you're reaching for: the standard deviation of sentence
    lengths, probably divided by the mean so a long text and a short one are
    comparable. `statistics.stdev` is imported for you.

    Watch the edge case: a one-sentence submission has no spread at all, and
    `stdev` raises on fewer than two values. Decide what that should return
    before the attack set decides for you.

    My version: the coefficient of variation of sentence lengths, i.e. the
    standard deviation of words-per-sentence divided by the mean. Dividing by
    the mean makes it unitless, so a text of short sentences and a text of
    long ones are compared on how much they VARY, not how long they are.
    HIGHER means more varied, which is the more human direction.

    One sentence returns 0.0 ("no measurable spread"). That reads as AI-ish,
    which is why /submit refuses anything under config.MIN_WORDS: a 40-word
    floor usually means two or more sentences.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]  # a stray "..." has no words
    if len(lengths) < 2:
        return 0.0
    mean = statistics.mean(lengths)
    return statistics.stdev(lengths) / mean


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words. ← TODO

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    Worth knowing before you rely on it: this measure falls as text gets
    longer, because common words repeat. Two texts of different lengths aren't
    directly comparable on it, and if your test inputs vary a lot in length,
    that alone can look like a signal.

    My version fixes that length problem with a "moving-average" type-token
    ratio: slide a window of TTR_WINDOW words along the text one word at a
    time, take the plain ratio inside each window, and average them. Every
    window is the same size, so a 60-word post and a 1,500-word essay are
    measured on the same footing. A text shorter than the window falls back
    to the plain ratio.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    if len(tokens) <= TTR_WINDOW:
        return len(set(tokens)) / len(tokens)
    ratios = [
        len(set(tokens[i:i + TTR_WINDOW])) / TTR_WINDOW
        for i in range(len(tokens) - TTR_WINDOW + 1)
    ]
    return statistics.mean(ratios)


def punctuation_density(text: str) -> float:
    """
    How much punctuation, relative to length. ← TODO

    Returns:
        A float. Whether you count all punctuation or only some kinds — commas,
        semicolons, dashes — is a real choice. Semicolons and em dashes are
        more interesting than full stops, because they vary more between
        writers.

    My version counts only the EXPRESSIVE marks in EXPRESSIVE_PUNCTUATION
    (semicolons, colons, dashes, brackets, quotes, question and exclamation
    marks, ellipses) per 100 words. Full stops and commas are left out: every
    writer uses them, so they say little about who is writing. HIGHER means
    more expressive punctuation, which is the more human direction.
    """
    total_words = len(words(text))
    if total_words == 0:
        return 0.0
    marks = sum(text.count(mark) for mark in EXPRESSIVE_PUNCTUATION)
    return marks / total_words * 100


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.** ← TODO

    Combine your three measures into one number. Same direction as
    `detector.model_signal`, so that `scoring.combine_signals` can treat them
    the same way — if one of your signals runs backwards, everything above it
    is wrong in a way that's hard to see.

    Two things to decide and write down:

      1. Which direction each measure points. Low spread means more AI-ish, so
         it needs flipping. Work out which of your three need that.
      2. How to get each onto a comparable scale. A raw type-token ratio sits
         between 0 and 1; a raw punctuation count doesn't. Adding them
         unscaled means whichever has the bigger numbers wins by default.

    Test it on the four calibration inputs from Milestone 4 — clearly AI,
    clearly human, plain conventional human writing, lightly-edited AI — before
    you trust it. Plain and ordinary, not formal: formal prose reads as *human*
    to signal one, and it is plain writing that gets accused.

    How mine works: each raw measure goes through _ramp, which maps it onto
    0 (human-typical) to 1 (AI-typical) between two anchor values, then the
    three are blended with STYLE_WEIGHTS. The anchors and weights are at the
    bottom of this file's constants section, each with its reason.
    """
    spread = _ramp(sentence_length_spread(text), *SPREAD_ANCHORS)
    ttr = _ramp(type_token_ratio(text), *TTR_ANCHORS)
    punct = _ramp(punctuation_density(text), *PUNCT_ANCHORS)

    score = (
        STYLE_WEIGHTS["spread"] * spread
        + STYLE_WEIGHTS["ttr"] * ttr
        + STYLE_WEIGHTS["punct"] * punct
    )
    return round(score, 4)


def _ramp(value: float, ai_typical: float, human_typical: float) -> float:
    """
    Map a raw measure onto 0-1, where 1 means AI-typical.

    A straight line between two anchors, clamped at both ends:
    `value == ai_typical` gives 1.0, `value == human_typical` gives 0.0, and
    halfway between gives 0.5. Passing the anchors in either order handles the
    direction: for sentence spread the AI anchor is the LOW number, for
    type-token ratio it's the HIGH one, and the formula doesn't care.
    """
    if ai_typical == human_typical:
        return 0.5
    position = (value - human_typical) / (ai_typical - human_typical)
    return min(max(position, 0.0), 1.0)


# ── Calibration: anchors and weights ─────────────────────────────────────────
# Each pair is (AI-typical value, human-typical value). I set them from the
# raw numbers on samples/ (clearly_ai, borderline, clearly_human) plus
# what each measure means, so they're a starting point, not ground truth.
#
#   sample          spread   ttr    punct/100 words
#   clearly_ai      0.41     0.94   0.0
#   borderline      0.47     0.87   3.0
#   clearly_human   1.13     0.83   4.3

# Coefficient of variation of sentence length. 0.3 means sentences within
# about a third of the average length of each other, which is very even;
# 0.9 means some sentences are near double the average and others a fraction.
SPREAD_ANCHORS = (0.3, 0.9)

# Moving-average type-token ratio over 40-word windows. This runs the
# OPPOSITE way to the usual story: on my samples the AI text had the MORE
# varied vocabulary (formal words, little repetition) and the human text the
# less varied ("I", "the", "and" repeating in first-person narration). So high
# TTR counts as AI-typical here.
TTR_ANCHORS = (0.95, 0.80)

# Expressive punctuation per 100 words. Zero is AI-typical; 5 per 100 words
# (one dash, question or quote every 20 words) is comfortably human.
PUNCT_ANCHORS = (0.0, 5.0)

# TTR gets the smallest weight because its direction surprised me and rests on
# three samples, and because formal human writing also has high TTR, which is
# exactly the writer who shouldn't be pushed toward "AI". The weights add up
# to 1.0, so the blend stays on the 0-1 scale.
STYLE_WEIGHTS = {"spread": 0.4, "punct": 0.4, "ttr": 0.2}


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
    print("\nRaw measures: higher spread and punctuation lean human; higher TTR leans AI.")
