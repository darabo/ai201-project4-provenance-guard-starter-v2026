"""
Settings for Provenance Guard.

Everything you're likely to change lives here, at the top, on purpose.

You'll edit the thresholds in Milestone 5 and the rate limits in unit 8.
"""

import os
from pathlib import Path

ROOT = Path(__file__).parent


# ─── The service ─────────────────────────────────────────────────────────────

# `127.0.0.1` is loopback — only your own machine can reach it, which is what
# you want all through units 7 and 8. A host somewhere else has to accept
# traffic from outside the box, and that means `0.0.0.0`. Setting the env var
# is how you get it; the default keeps your local `curl` commands unchanged.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))

# Flask's debug mode gives anyone who can reach the service an interactive
# Python prompt inside your process. Fine on loopback, a gift to strangers
# anywhere else — so it turns itself off the moment HOST isn't loopback.
DEBUG = os.getenv("AI201_DEBUG", "1") == "1" and HOST in ("127.0.0.1", "localhost")


# ─── The local model ─────────────────────────────────────────────────────────
# Your first signal runs a language model ON YOUR OWN MACHINE. No account, no
# key, no card. It downloads about 550 MB the first time — do that before
# class, not during it.
#
# What it measures: how *predictable* your text is to a language model. Text a
# model finds easy to predict tends to be text a model wrote.
#
# The first call is the slow one — ten to twenty seconds while the model loads,
# longer on an older laptop. After that it stays in memory and a submission
# takes a second or two. That cost is part of what you're learning: this is
# what running a model inline in a request actually looks like.

DETECTOR_MODEL = os.getenv("AI201_DETECTOR_MODEL", "gpt2")

# Longer text gives a steadier reading but takes longer. 400 tokens is roughly
# 300 words, which is enough for the signal to mean something.
DETECTOR_MAX_TOKENS = 400


# ─── Input limits (criterion 5) ──────────────────────────────────────────────
# What /submit refuses with a 400 before any signal runs. Both numbers come
# from criterion 5 in criteria.md.
#
# MIN_WORDS: under about 40 words (two or three sentences) the signals have
# too little to measure. gpt2 needs enough tokens for perplexity to settle,
# and a sentence-length spread needs at least two sentences.
#
# MAX_TEXT_CHARS: 10,000 characters is roughly 1,700 words, enough for any
# essay or story. gpt2 only reads the first DETECTOR_MAX_TOKENS anyway, so a
# bigger paste would only slow the service down.

MIN_WORDS = 40
MAX_TEXT_CHARS = 10_000

# The longest appeal reasoning /appeal accepts. 5,000 characters is around 850
# words: room for a real explanation, but not a second essay.
APPEAL_MAX_CHARS = 5_000


# ─── Scoring (Milestone 4) ───────────────────────────────────────────────────
# How much each signal counts toward the combined score.
#
# ⚠️ These are placeholders. Milestone 4 asks you to write your combining rule
# down BEFORE you code it, and to put the numbers in your README. Whatever you
# decide, it goes here.

#
# My rule (scoring.py::combine_signals), in three steps:
#
#   1. base = 0.5 * model_score + 0.5 * style_score
#      Equal weights: each of the two required signals has a known blind spot
#      (gpt2 accuses plain writers; style can't read), and I have no evidence
#      yet that one is more trustworthy than the other.
#
#   2. final = base + MARKER_BOOST * marker_score * (1 - base)
#      Stock phrases can only push the score UP. Finding "it is important to
#      note" is evidence of AI; finding none is not evidence of a human,
#      because one paraphrase pass removes them all. Multiplying by (1 - base)
#      means the boost shrinks as the score nears 1, so it never passes 1.0.
#      With MARKER_BOOST = 0.3, a text at base 0.50 full of markers rises to
#      at most 0.65.
#
#   3. If fewer than MIN_AGREEING of the three signals are at or above
#      AGREEMENT_LEVEL, the score is capped just under AI_THRESHOLD, so the
#      result can be "unsure" but never high-confidence AI. No single signal
#      can accuse a writer on its own.

WEIGHT_MODEL_SIGNAL = 0.5
WEIGHT_STYLE_SIGNAL = 0.5
MARKER_BOOST = 0.3
AGREEMENT_LEVEL = 0.5
MIN_AGREEING = 2


# ─── Thresholds (Milestone 5) ────────────────────────────────────────────────
# Where one label becomes another. Scores run 0.0 (confidently human) to 1.0
# (confidently AI).
#
#   score < HUMAN_THRESHOLD          -> high-confidence human
#   between the two                  -> unsure
#   score > AI_THRESHOLD             -> high-confidence AI
#
# ⚠️ This is where your false-positive decision from Milestone 1 actually gets
# made. Widening the unsure band means fewer wrong accusations and more AI text
# getting through. There is no setting that avoids the trade — only settings
# that decide who pays for it.

HUMAN_THRESHOLD = 0.35

# Unit 8, improvement 2 (stretch): raised from 0.65 to 0.80, widening the
# unsure band to 0.35-0.80. After improvement 1, four human texts in the
# attack set (FP02 to FP05: formal, non-native, a rubric essay, technical
# docs) and two of my own paragraphs still scored 0.67 to 0.77, because gpt2
# alone rates plain, formal writing 0.74 to 0.83. A higher line means the AI
# label needs stronger evidence. The agreement guard in combine_signals caps
# at AI_THRESHOLD - 0.01, so it moves with this automatically (to 0.79).
AI_THRESHOLD = 0.80

# ⚠️ One thing that catches people out in Milestone 5. A weighted average can
# only land between its two inputs — so while `style_signal` is still the stub
# returning 0.5, the combined score can never leave 0.25–0.75 no matter what
# the model signal says, and the human label needs a model score below 0.20 to
# be reachable at all.
#
# If a label you can't reach is the problem, the fix is upstream of the
# thresholds: a style signal that actually varies. `scoring.label_ranges()`
# prints the bands; the reachable range is a different question.


# ─── Rate limiting (UNIT 8) ──────────────────────────────────────────────────
# Off in unit 7. You turn it on and choose the numbers in unit 8, Milestone 1.
#
# Think about two people: a real writer submitting their own work a few times
# an hour, and a script sending a thousand variations to map your thresholds.
# Your README has to say why your numbers and not others.

# On by default from unit 8. Running with AI201_RATE_LIMITS=0 still turns it
# off, which is handy for debugging but never for a graded run.
RATE_LIMITING_ENABLED = os.getenv("AI201_RATE_LIMITS", "1") == "1"

# Counted per creator_id (see rate_limit_key in app.py).
#
# 5 per minute: a real writer submits their own work a few times an hour, so
# they never come near it, while a script probing where my thresholds sit gets
# only 5 tries a minute. The flood test of 15 shows 5 x 200 then 10 x 429.
#
# 50 per day: far more than anyone posting their own writing needs, and too
# few probes for a script to map the 0.35 and 0.65 lines from one creator_id.
# Counts live in memory (RATE_LIMIT_STORAGE), so a restart resets them.
RATE_LIMIT_PER_MINUTE = 5
RATE_LIMIT_PER_DAY = 50

# Flask-Limiter warns loudly without this. In-memory is right for one laptop
# and wrong for anything real — a restart forgets every count, and two copies
# of the service wouldn't share limits.
RATE_LIMIT_STORAGE = "memory://"


# ─── Paths ───────────────────────────────────────────────────────────────────

LOG_DIR = ROOT / "logs"
AUDIT_LOG = LOG_DIR / "audit.jsonl"
RESULTS_DIR = ROOT / "results"

# Unit 9 (capstone): the run log, one line per HTTP request. See runlog.py for
# why this is a different file from the audit log above. The environment
# variable lets a test point the log somewhere else without touching the
# committed file; with nothing set it is logs/runs.jsonl.
RUN_LOG = Path(os.getenv("AI201_RUN_LOG", str(LOG_DIR / "runs.jsonl")))
