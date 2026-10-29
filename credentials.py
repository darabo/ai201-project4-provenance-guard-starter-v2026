"""
The verified-writer credential. (Stretch feature, declared in README.)

A writer can earn a "verified writer" badge by passing one extra step: write a
short piece on a prompt we choose, inside a time window, and have it come back
as something other than high-confidence AI. Once earned, every later
submission from that creator_id carries `verified_human: true` and a badge
line beside the label. The badge never changes a score.

How the step works, using two routes in app.py:

    1. POST /verify/challenge  {"creator_id": "..."}
       -> a random prompt and a challenge_id, valid for VERIFY_WINDOW_MINUTES
    2. POST /verify  {"creator_id": "...", "challenge_id": "...", "text": "..."}
       -> passes if: the challenge was issued to this creator, it hasn't
          expired or been used, at least VERIFY_MIN_SECONDS have passed since
          it was issued, the text has at least VERIFY_MIN_WORDS words, and
          the text is not labelled high-confidence AI.

Everything is stored in the audit log (no database): a challenge is an entry
with `"event": "verify_challenge"`, a credential is one with
`"event": "verified"`. That means a restart forgets nothing, and anyone reading
the log can see exactly when and how a writer was verified.

⚠️ What this proves, honestly: that someone holding this creator_id produced
non-AI-looking writing on a fresh prompt, at human typing speed, once. It does
NOT prove every later piece is theirs. A writer could verify honestly and paste
AI text tomorrow; the badge would still show. That's why it sits beside the
label instead of changing the score.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

import audit

# How long a challenge stays open. Ten minutes is enough to write 60 to 150
# words without rushing.
VERIFY_WINDOW_MINUTES = 10

# The response must arrive at least this long after the challenge was issued.
# 60 words at a fast 80 words per minute takes about 45 seconds, so anything
# quicker was almost certainly pasted, not typed.
VERIFY_MIN_SECONDS = 45

# Longer than /submit's 40-word floor: the signals are steadier on more text,
# and this is the one place we ask a writer to prove something.
VERIFY_MIN_WORDS = 60

# Prompts that ask for a specific personal detail. A generic essay question is
# easy to hand to a chat tool; "the last thing you fixed" invites concrete,
# unpredictable answers that read as human to signal one.
#
# Removed after testing: "Describe the route you take most often, as if giving
# directions to a friend." Directions are a formulaic genre ("go until you
# hit...", "take a left"), and my own honest answer to it scored perplexity
# 16.3 and was refused as AI (combined 0.78). A prompt that invites predictable
# phrasing sets real writers up to fail, so it's gone.
PROMPTS = [
    "Describe the last thing you fixed or repaired, and how it went.",
    "Write about a meal you remember clearly. Where were you and who was there?",
    "Write about something you changed your mind about in the last year.",
    "Describe the room you're sitting in right now, including one thing that annoys you about it.",
    "Write about a small mistake you made recently and what happened next.",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(timestamp: str) -> datetime:
    """Audit-log timestamps are ISO 8601 strings like 2026-10-29T01:47:28+00:00."""
    return datetime.fromisoformat(timestamp)


def issue_challenge(creator_id: str) -> dict:
    """Pick a prompt, log the challenge, and return what the writer needs."""
    issued = _now().replace(microsecond=0)
    challenge = {
        "challenge_id": f"v_{uuid.uuid4().hex[:12]}",
        "prompt": random.choice(PROMPTS),
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(minutes=VERIFY_WINDOW_MINUTES)).isoformat(),
        "min_words": VERIFY_MIN_WORDS,
    }
    audit.log_event("verify_challenge", creator_id=creator_id, status="pending", **challenge)
    return challenge


def find_challenge(challenge_id: str) -> dict | None:
    """The logged challenge entry with this id, or None."""
    for entry in audit.read_entries():
        if entry.get("event") == "verify_challenge" and entry.get("challenge_id") == challenge_id:
            return entry
    return None


def challenge_problem(challenge: dict | None, creator_id: str, word_count: int) -> str | None:
    """
    Every check /verify makes BEFORE scoring the text, in one place.

    Returns None if the attempt may go ahead, or a sentence explaining why not.
    Scoring is left to app.py so it uses exactly the same pipeline as /submit.
    """
    if challenge is None:
        return "That challenge_id doesn't exist. Ask for a new one at /verify/challenge."
    if challenge.get("creator_id") != creator_id:
        return "That challenge was issued to a different creator_id."
    if any(e.get("event") == "verified" and e.get("challenge_id") == challenge["challenge_id"]
           for e in audit.read_entries()):
        return "That challenge has already been used. Ask for a new one."

    elapsed = (_now() - _parse(challenge["issued_at"])).total_seconds()
    if _now() > _parse(challenge["expires_at"]):
        return f"That challenge expired after {VERIFY_WINDOW_MINUTES} minutes. Ask for a new one."
    if elapsed < VERIFY_MIN_SECONDS:
        return (f"That came back in under {VERIFY_MIN_SECONDS} seconds, faster than anyone "
                f"can type {VERIFY_MIN_WORDS} words. Take your time and write it yourself.")
    if word_count < VERIFY_MIN_WORDS:
        return f"The response has {word_count} words; at least {VERIFY_MIN_WORDS} are needed."
    return None


def grant(creator_id: str, challenge_id: str, scores: dict) -> dict:
    """Log the credential. `scores` is the scoring result for the response."""
    return audit.log_event(
        "verified",
        creator_id=creator_id,
        status="verified",
        challenge_id=challenge_id,
        guess=scores["guess"],
        combined_score=scores["confidence"],
        model_score=scores["model_score"],
        style_score=scores["style_score"],
        marker_score=scores["marker_score"],
    )


def credential_for(creator_id: str) -> dict | None:
    """The most recent "verified" entry for this creator, or None."""
    found = None
    for entry in audit.read_entries():
        if entry.get("event") == "verified" and entry.get("creator_id") == creator_id:
            found = entry
    return found


def badge_text(credential: dict | None) -> str | None:
    """The line shown beside the label on a verified writer's work."""
    if credential is None:
        return None
    day = _parse(credential["timestamp"]).strftime("%-d %B %Y")
    return f"Verified writer: completed a live writing check on {day}."
