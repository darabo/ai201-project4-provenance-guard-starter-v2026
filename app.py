#!/usr/bin/env python3
"""
Provenance Guard — the web service.

    python app.py

Then, in another terminal:

    curl -X POST http://127.0.0.1:5000/ping \
      -H "Content-Type: application/json" \
      -d '{"message": "hello"}'

That's the example route. It works right now, before you've written anything.
**Leave it alone** — it's your control. When something breaks later, check that
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself.

Routes:

    POST /ping        the worked example. Already works. Don't edit it
    POST /submit      ← YOU BUILD THIS (Milestone 3, 4, 5)
    POST /appeal      ← YOU BUILD THIS (Milestone 5)
    GET  /content/<id>        one item's current status (stretch)
    POST /verify/challenge    get a writing prompt to earn the verified badge (stretch)
    POST /verify              answer it and earn the badge (stretch)
    GET  /log         the audit log. Already works
    GET  /health      is the service up, and is the model loaded

Unit 9 (capstone): every request to any route above also leaves one record in
the run log, logs/runs.jsonl. The hooks that do it are just below the line
`app = Flask(__name__)`; runlog.py explains the record.
"""

import sys
import time
import uuid

from flask import Flask, g, got_request_exception, has_request_context, jsonify, request

import audit
import config
import credentials
import detector
import markers
import runlog
import scoring
import stylometry

app = Flask(__name__)


# ── The run log — UNIT 9 (capstone) ──────────────────────────────────────────
# One record in logs/runs.jsonl for EVERY request, whatever happens to it.
#
# This is done with "hooks": functions Flask calls by itself around each
# request, so no route has to remember to log. Three of them are used:
#
#   before_request    runs before the route. Starts the clocks.
#   after_request     runs once a response exists. Writes the record.
#   teardown_request  runs last, even after a crash. Catches the one case
#                     after_request can miss (see below).
#
# They are registered HERE, above the rate limiter, on purpose. Flask runs
# before_request functions in the order they were registered, and the limiter
# can end a request early with a 429. Starting the clock first means a
# rate-limited request is timed and logged like any other.
#
# `g` is Flask's per-request scratch space: an object that exists for exactly
# one request and is thrown away afterwards. It's how the "before" hook hands
# the start time to the "after" hook without a global variable that two
# simultaneous requests would overwrite.

def _ms(seconds: float) -> float:
    """Seconds to milliseconds (x 1000), rounded to one decimal place."""
    return round(seconds * 1000, 1)


@app.before_request
def _start_run_record():
    """Note when this request arrived and start timing it."""
    g.run_id = runlog.new_request_id()
    g.run_timestamp = runlog.now()
    # True when gpt2 isn't in memory yet. The first scored request after a
    # start has to load it (seconds, not milliseconds), and without this flag
    # that one slow row would look like an unexplained spike.
    g.run_cold_start = detector._model is None
    g.run_stages = None          # filled in by _score_text if text gets scored
    g.run_error_type = None      # filled in by _note_exception if a route crashes
    g.run_logged = False         # set once the record is written
    # Two clocks, because they measure different things:
    #   process_time  processor time this whole process has used, summed over
    #                 every CPU core. This is the "compute" a request costs.
    #   perf_counter  ordinary elapsed ("wall-clock") time. This is the wait
    #                 the caller experiences.
    # gpt2 runs on several cores at once, so CPU time can be larger than the
    # elapsed time. CPU time is per PROCESS, so it's only attributable to one
    # request while requests are handled one at a time, which is how
    # RUNNING.md starts the service (a single gunicorn worker).
    g.run_cpu_started = time.process_time()
    g.run_started = time.perf_counter()


def _note_exception(sender, exception, **extra):
    """
    Remember what kind of exception crashed a route, for the run record.

    Flask sends the `got_request_exception` signal when a route raises
    something nobody handled. A "signal" is a notification you can subscribe
    to; subscribing changes nothing about how Flask then deals with the crash.
    """
    g.run_error_type = type(exception).__name__


got_request_exception.connect(_note_exception, app)


def _build_run_record(status_code: int, response_body) -> dict:
    """
    Assemble one run-log record from the request and what was sent back.

    Every read from `g` uses getattr with a fallback, so a request that
    somehow skipped _start_run_record still produces a record instead of an
    AttributeError inside the logging code.
    """
    finished = time.perf_counter()
    cpu_finished = time.process_time()
    started = getattr(g, "run_started", None)
    cpu_started = getattr(g, "run_cpu_started", None)

    # silent=True: a body that isn't JSON gives None instead of raising.
    # get_data(cache=True) returns the raw bytes; Flask keeps them after the
    # first read, so asking again here costs nothing.
    payload = request.get_json(silent=True)
    body_bytes = len(request.get_data(cache=True))

    record = {
        "timestamp": getattr(g, "run_timestamp", None) or runlog.now(),
        "request_id": getattr(g, "run_id", None) or runlog.new_request_id(),
        "method": request.method,
        "path": request.path,
        "input": runlog.summarize_input(payload, body_bytes),
        "output": runlog.summarize_output(status_code, response_body),
        "outcome": runlog.outcome_for(status_code),
        "duration_ms": _ms(finished - started) if started is not None else None,
        "cpu_ms": _ms(cpu_finished - cpu_started) if cpu_started is not None else None,
        "cold_start": getattr(g, "run_cold_start", None),
    }
    stages = getattr(g, "run_stages", None)
    if stages:
        record["stages_ms"] = stages
    error_type = getattr(g, "run_error_type", None)
    if error_type:
        record["output"]["error_type"] = error_type
    return record


@app.after_request
def _write_run_record(response):
    """
    Write the run record for this request, then let the response go.

    Flask calls this with the finished response for every request that
    produced one: a 200, a refused 400, a rate-limited 429, an unknown-URL
    404, and (under gunicorn) the 500 Flask builds when a route crashes.

    The whole body is inside try/except because logging must never be the
    reason a request fails. If the log can't be written (disk full, folder
    not writable) the caller still gets their answer and the problem is
    printed to the server's terminal instead.
    """
    try:
        record = _build_run_record(response.status_code, response.get_json(silent=True))
        # The id travels back in a response header, so whoever sent the
        # request can look up exactly its row in logs/runs.jsonl.
        response.headers["X-Request-ID"] = record["request_id"]
        runlog.write(record)
        g.run_logged = True
    except Exception as exc:  # noqa: BLE001 — see the docstring
        print(f"[runlog] could not write a run record: {exc!r}", file=sys.stderr)
    return response


@app.teardown_request
def _write_run_record_after_crash(exc):
    """
    The safety net for a crash that never became a response.

    With `python app.py` Flask runs in debug mode, and in debug mode an
    unhandled exception is passed straight up to the debugger. No response
    object is built, so after_request never runs and the crash would leave
    nothing in the log. teardown_request runs regardless, and `exc` is the
    exception (or None when the request ended normally).

    `g.run_logged` stops a double entry: under gunicorn the crash DOES become
    a 500 response, after_request logs it, and this hook has nothing to do.
    """
    if exc is None or getattr(g, "run_logged", True):
        return
    try:
        g.run_error_type = type(exc).__name__
        runlog.write(_build_run_record(500, None))
    except Exception as log_exc:  # noqa: BLE001 — never raise from teardown
        print(f"[runlog] could not write a crash record: {log_exc!r}", file=sys.stderr)


# ── Rate limiting — UNIT 8 ────────────────────────────────────────────────────
# Off until you turn it on. In unit 8, Milestone 1:
#
#   1. Set RATE_LIMITING_ENABLED = True in config.py (or AI201_RATE_LIMITS=1)
#   2. Choose your numbers there
#   3. Uncomment the @limiter.limit(...) line on /submit below
#
# The order doesn't matter. While limiting is off, that decorator is a no-op
# that quietly does nothing, so uncommenting it early costs you nothing — but
# it also means no 429 until you've done step 1.
#
# The storage backend is preconfigured, which stops Flask-Limiter printing a
# warning on every start. In-memory is right for one laptop and wrong for
# anything real — a restart forgets every count.

class _LimiterOff:
    """
    Stands in for the real limiter while rate limiting is off.

    It makes @limiter.limit(...) a decorator that returns the route
    untouched, so uncommenting the line before you flip the setting is
    harmless instead of a crash on startup.
    """

    def limit(self, *args, **kwargs):
        return lambda view: view


limiter = _LimiterOff()
if config.RATE_LIMITING_ENABLED:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def rate_limit_key():
        """
        Who a request counts against.

        Falling back to the caller's address is the easy version. Unit 8's
        stretch asks about per-creator limits instead — and the difference
        matters: one script can look like a thousand callers, and one household
        can look like one.
        """
        payload = request.get_json(silent=True)
        # A body that parses as JSON but isn't an object — a bare list or
        # string — has no .get. Without this guard the key function raises
        # BEFORE the route runs, and a malformed request becomes a 500 that
        # looks like your handler crashed when your handler never ran.
        if not isinstance(payload, dict):
            return get_remote_address()
        creator = payload.get("creator_id")
        return creator if isinstance(creator, str) and creator.strip() else get_remote_address()

    limiter = Limiter(
        key_func=rate_limit_key,
        app=app,
        storage_uri=config.RATE_LIMIT_STORAGE,
        default_limits=[],
    )

    @app.errorhandler(429)
    def rate_limited(exc):
        """
        A rejected request still leaves a trace.

        ⚠️ An attack that shows up only as an absence is one you'll never find.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="rate_limited",
            limit=str(exc.description),
        )
        return jsonify({
            "error": "rate_limited",
            "message": "Too many submissions. Try again shortly.",
            "limit": str(exc.description),
        }), 429


# ── The worked example. Already works. Don't edit. ────────────────────────────

@app.post("/ping")
def ping():
    """
    Everything a route needs, in six lines.

    JSON arrives as a dict. You pull things out of it. You return a dict and
    the framework turns it into a response. That's the whole idea.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "you_sent": payload.get("message"),
        "service": "provenance-guard",
    })


@app.get("/health")
def health():
    """Is the service up, and has the model been downloaded yet?"""
    import detector

    loaded = detector._model is not None
    return jsonify({
        "ok": True,
        "detector_model": config.DETECTOR_MODEL,
        "detector_loaded": loaded,
        "rate_limiting": config.RATE_LIMITING_ENABLED,
        "log_entries": len(audit.read_entries()),
    })


# ── YOU BUILD THIS ────────────────────────────────────────────────────────────

@app.post("/submit")
# Unit 8: the rate limit. Flask-Limiter checks this BEFORE submit() runs; a
# caller over the limit gets the 429 from rate_limited() above and never
# reaches the signals. "5/minute;50/day" means both limits apply at once.
@limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute;{config.RATE_LIMIT_PER_DAY}/day")
def submit():
    """
    Take a piece of text, decide about it, log the decision, answer.
    ← TODO — Milestones 3, 4 and 5

    Expects JSON:
        {"text": "...", "creator_id": "..."}

    Should return JSON with, at minimum:
        {"content_id": "...", "guess": "...", "confidence": 0.0, "label": "...",
         "model_score": 0.0, "style_score": 0.0}

    ⚠️ **Both signal scores go in the response, not just the log.** Unit 8's
    `run_attacks.py` and `run_eval.py` read `model_score` and `style_score`
    straight off this response and put them in your reports. Leave them out and
    every row of next unit's evidence says `null` — which is exactly the
    diagnostic you need to name a stage and a mechanism. You do not want to
    find that out after running the attack set.

    ─────────────────────────────────────────────────────────────────────────
    Build it in three passes. Do not skip ahead — the ordering is how you tell
    a broken route from a broken signal.

    **Milestone 3 — the route answers.**
      1. Return a hardcoded response. Confirm `curl` gets it back before you
         add any logic at all.
      2. Then pull `text` and `creator_id` out of the payload.
      3. Then call ONE signal — `detector.model_signal(text)` — and put the
         real number in. Leave confidence and label as placeholders.
      4. Log every submission with `audit.log_decision(...)`. The content_id
         matters: `/appeal` needs it, and a student who skips it rebuilds this
         whole flow later.

    **Milestone 4 — the second signal and the score.**
      5. Add `stylometry.style_signal(text)`.
      6. Combine them with `scoring.combine_signals(...)`.
      7. Log BOTH signal scores alongside the combined one, and put them in the
         response too. Next unit you can't diagnose anything without them.

    **Milestone 5 — the label.**
      8. `scoring.score_to_label(...)` and put the real label in the response.

    ─────────────────────────────────────────────────────────────────────────
    Worth deciding early, because unit 8's attack set will decide it for you:
    what should this do when `text` is missing, empty, or enormous? A crash on
    a malformed input is one of the most common real failures there is.
    """

    # get_json(silent=True) returns None instead of raising when the body
    # isn't valid JSON, so a garbage body falls into the checks below rather
    # than crashing the route.
    payload = request.get_json(silent=True)

    # Step 2: refuse bad input BEFORE any signal runs. Every check lives in
    # _check_submission so this route reads top to bottom.
    problem = _check_submission(payload)
    if problem:
        reason, message = problem
        # A refused request still leaves a trace in the log (criterion 5).
        # creator_id may be missing or the body may not even be an object, so
        # fall back to "unknown" rather than calling .get on a non-dict.
        creator = payload.get("creator_id") if isinstance(payload, dict) else None
        audit.log_rejection(
            creator_id=creator if isinstance(creator, str) and creator.strip() else "unknown",
            reason=reason,
            message=message,
        )
        return jsonify({"error": "bad_request", "message": message}), 400

    text = payload["text"]
    creator_id = payload["creator_id"].strip()

    # Steps 3 to 6: three signals, one combined score, one label. See
    # _score_text below; /verify uses the same helper so both routes judge
    # text identically.
    try:
        result = _score_text(text)
    except detector.DetectorUnavailable as exc:
        # The model isn't downloaded or can't load. That's the service's
        # fault, not the writer's, so it's a 503 ("service unavailable").
        audit.log_rejection(creator_id=creator_id, reason="detector_unavailable", message=str(exc))
        return jsonify({"error": "detector_unavailable", "message": str(exc)}), 503

    # Step 7 (stretch): does this writer hold the verified-writer credential?
    # It's shown beside the label and never changes the score.
    credential = credentials.credential_for(creator_id)

    # Step 8: log the decision. The content_id is the handle /appeal and
    # /content/<id> need later. uuid4().hex is 32 random hex characters; 12 of
    # them give about 2.8e14 possible ids, so a collision is not a real worry.
    content_id = f"c_{uuid.uuid4().hex[:12]}"
    audit.log_decision(
        content_id=content_id,
        creator_id=creator_id,
        guess=result["guess"],
        model_score=result["model_score"],
        style_score=result["style_score"],
        combined_score=result["confidence"],
        label=result["label"],
        status="decided",
        # Not among the nine standard fields, so these ride in **extra.
        marker_score=result["marker_score"],
        verified_human=credential is not None,
    )

    # All three signal scores go in the response, not just the log: unit 8's
    # run_attacks.py and run_eval.py read model_score and style_score from here.
    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        **result,
        "verified_human": credential is not None,
        "verified_badge": credentials.badge_text(credential),
        "status": "decided",
    }), 200


def _score_text(text: str) -> dict:
    """
    Run all three signals on `text`, combine them, and label the result.

    Returns a dict with guess, confidence, label, model_score, style_score and
    marker_score. Raises detector.DetectorUnavailable if gpt2 can't load.
    """
    # Unit 9: a stopwatch reading is taken between the stages (t0 to t4), so
    # the run log can say where a request's time went. perf_counter() returns
    # seconds from an arbitrary starting point; only the DIFFERENCE between
    # two readings means anything.
    t0 = time.perf_counter()

    # Signal one. The first call loads gpt2 into memory (10+ seconds); after
    # that it stays loaded and each call takes a second or two.
    model_score = detector.model_signal(text)
    t1 = time.perf_counter()

    # Signals two and three are plain Python string work: milliseconds.
    style_score = stylometry.style_signal(text)
    t2 = time.perf_counter()
    marker_score = markers.marker_signal(text)
    t3 = time.perf_counter()

    # One number from three. The rule and its numbers are explained in
    # scoring.combine_signals and above the weights in config.py.
    confidence = scoring.combine_signals(model_score, style_score, marker_score)

    # The number becomes words a writer can read.
    guess, label = scoring.score_to_label(confidence)
    t4 = time.perf_counter()

    # Hand the timings to the run-log hook through `g`. has_request_context()
    # is False if this function is ever called outside a web request (from a
    # test or a script), where `g` doesn't exist and touching it would raise.
    if has_request_context():
        g.run_stages = {
            "model": _ms(t1 - t0),      # gpt2 perplexity (detector.py)
            "style": _ms(t2 - t1),      # sentence measures (stylometry.py)
            "markers": _ms(t3 - t2),    # stock-phrase search (markers.py)
            "scoring": _ms(t4 - t3),    # combine + label (scoring.py)
        }

    return {
        "guess": guess,
        "confidence": confidence,
        "label": label,
        "model_score": model_score,
        "style_score": style_score,
        "marker_score": marker_score,
    }


def _check_submission(payload) -> tuple[str, str] | None:
    """
    Decide whether a /submit body is something we can score.

    Returns None when the body is fine, or a (reason, message) pair when it
    isn't: `reason` is a short code for the audit log, `message` is the
    sentence sent back to the caller. These are the seven cases criterion 5
    names, checked in the order a caller would most likely trip them.
    """
    # A JSON list or string parses fine but has no fields to read.
    if not isinstance(payload, dict):
        return "not_an_object", 'Send a JSON object like {"text": "...", "creator_id": "..."}.'

    text = payload.get("text")
    # Covers a missing field (None), an explicit null, and a non-string value.
    if not isinstance(text, str):
        return "text_missing", 'The "text" field is required and must be a string.'
    if not text.strip():
        return "text_empty", 'The "text" field is empty.'

    # Character limit first: counting words on a huge paste is wasted work.
    if len(text) > config.MAX_TEXT_CHARS:
        return "text_too_long", (
            f"The text is {len(text):,} characters; the limit is "
            f"{config.MAX_TEXT_CHARS:,}."
        )
    word_count = len(stylometry.words(text))
    if word_count < config.MIN_WORDS:
        return "text_too_short", (
            f"The text has {word_count} words; at least {config.MIN_WORDS} are "
            f"needed to judge it fairly."
        )

    creator_id = payload.get("creator_id")
    if not isinstance(creator_id, str) or not creator_id.strip():
        return "creator_missing", 'The "creator_id" field is required.'

    return None


@app.post("/appeal")
def appeal():
    """
    A writer says you got it wrong. ← TODO — Milestone 5

    Expects JSON:
        {"content_id": "...", "reasoning": "..."}

    Should:
      1. Check the content_id actually exists — `audit.entries_for(id)` tells
         you. A typo here fails silently and looks like a broken endpoint,
         which is the single most common way this milestone eats an hour.
      2. Record the appeal with `audit.log_appeal(...)`, which moves the item
         to `under_review`.
      3. Confirm to the writer. No automatic re-checking needed.

    This is the smallest endpoint in the project and the one that matters most
    to the person on the other end. It's the only thing standing between a
    wrong accusation and nothing at all.
    """
    payload = request.get_json(silent=True)

    # Step 1: both fields present and usable. Same idea as _check_submission:
    # a body that isn't a JSON object has no fields at all.
    if not isinstance(payload, dict):
        payload = {}
    content_id = payload.get("content_id")
    reasoning = payload.get("reasoning")
    if not isinstance(content_id, str) or not content_id.strip():
        return _refuse_appeal("appeal_missing_id", 'The "content_id" field is required.', 400)
    if not isinstance(reasoning, str) or not reasoning.strip():
        return _refuse_appeal("appeal_missing_reasoning",
                              'The "reasoning" field is required: tell us why you think the result is wrong.', 400)
    if len(reasoning) > config.APPEAL_MAX_CHARS:
        return _refuse_appeal("appeal_too_long",
                              f"Please keep the reasoning under {config.APPEAL_MAX_CHARS:,} characters.", 400)
    content_id = content_id.strip()

    # Step 2: the content_id must belong to a real decision. entries_for
    # returns every log line for this id; the original decision is the one
    # without an "event" field (appeals and rejections carry one).
    decisions = [e for e in audit.entries_for(content_id) if "event" not in e]
    if not decisions:
        # 404 = "no such thing". Criterion 4: an unknown id adds no appeal entry.
        return _refuse_appeal("appeal_unknown_id",
                              f"No submission with content_id {content_id!r} exists.", 404,
                              error="not_found", content_id=content_id)

    # Step 3: record it. log_appeal APPENDS a new line with status
    # under_review; the original decision line stays untouched, so the log
    # shows both what was decided and that it was challenged.
    entry = audit.log_appeal(
        content_id=content_id,
        creator_id=decisions[0]["creator_id"],
        reasoning=reasoning.strip(),
    )

    # Step 4: confirm to the writer. No automatic re-check happens here.
    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": ("Thank you. Your appeal has been recorded and this piece is now "
                    "marked as under review. A person will read your explanation "
                    "alongside our original result."),
        "appealed_at": entry["timestamp"],
    }), 200


def _refuse_appeal(reason: str, message: str, status: int, error: str = "bad_request", **extra):
    """
    Turn away a bad appeal, leaving a `rejected` trace in the audit log.

    The log entry says "rejected", never "appeal", so a refused appeal can't be
    mistaken for a recorded one when someone reads the log later.
    """
    audit.log_rejection(creator_id="unknown", reason=reason, message=message, **extra)
    return jsonify({"error": error, "message": message}), status


# ── Stretch features ──────────────────────────────────────────────────────────

@app.get("/content/<content_id>")
def get_content(content_id):
    """
    One item's current status, rebuilt from the audit log. (Stretch.)

        curl http://127.0.0.1:5000/content/c_3de98cf58d2c

    The log is append-only, so "current status" means: start from the
    original decision, then let each later appeal move the status on. The
    `<content_id>` in the route is a Flask URL variable: whatever sits in that
    part of the path arrives as the function's argument.
    """
    entries = audit.entries_for(content_id)
    # The decision is the entry with no "event" field; appeals and rejections
    # carry one. A rejected appeal against a made-up id also lands in
    # entries_for, which is why we can't just test "any entries at all".
    decisions = [e for e in entries if "event" not in e]
    if not decisions:
        return jsonify({"error": "not_found",
                        "message": f"No submission with content_id {content_id!r} exists."}), 404

    decision = decisions[0]
    appeals = [e for e in entries if e.get("event") == "appeal"]
    # The newest status wins: under_review once any appeal exists.
    status = appeals[-1]["status"] if appeals else decision["status"]

    return jsonify({
        "content_id": content_id,
        "creator_id": decision["creator_id"],
        "status": status,
        "guess": decision["guess"],
        "confidence": decision["combined_score"],
        "label": decision["label"],
        "model_score": decision["model_score"],
        "style_score": decision["style_score"],
        "marker_score": decision.get("marker_score"),
        "verified_human": decision.get("verified_human", False),
        "submitted_at": decision["timestamp"],
        "appeals": [{"reasoning": a["reasoning"], "appealed_at": a["timestamp"]} for a in appeals],
    })


@app.post("/verify/challenge")
def verify_challenge():
    """
    Step one of the verified-writer path: hand out a writing prompt. (Stretch.)

    Expects {"creator_id": "..."}; returns the prompt, a challenge_id, and
    when it expires. See credentials.py for how the whole path works.
    """
    payload = request.get_json(silent=True)
    creator_id = payload.get("creator_id") if isinstance(payload, dict) else None
    if not isinstance(creator_id, str) or not creator_id.strip():
        return jsonify({"error": "bad_request", "message": 'The "creator_id" field is required.'}), 400

    challenge = credentials.issue_challenge(creator_id.strip())
    return jsonify({
        **challenge,
        "instructions": (f"Write at least {challenge['min_words']} words responding to the "
                         f"prompt, in your own words, then send them to POST /verify with "
                         f"this challenge_id before it expires."),
    })


@app.post("/verify")
def verify():
    """
    Step two: check the writer's response and grant the credential. (Stretch.)

    Expects {"creator_id": "...", "challenge_id": "...", "text": "..."}.
    The text is scored by the same _score_text as /submit; a high-confidence
    AI result is refused. Anything else earns the credential, including
    "unsure", because the unsure band is where plain human writing lands and
    refusing it would lock out exactly the writers this path is meant to help.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    creator_id = payload.get("creator_id")
    challenge_id = payload.get("challenge_id")
    text = payload.get("text")
    if not all(isinstance(v, str) and v.strip() for v in (creator_id, challenge_id, text)):
        return jsonify({"error": "bad_request",
                        "message": 'Send "creator_id", "challenge_id" and "text".'}), 400
    creator_id = creator_id.strip()

    # Checks that don't need the model: right writer, in time, long enough.
    challenge = credentials.find_challenge(challenge_id.strip())
    problem = credentials.challenge_problem(challenge, creator_id, len(stylometry.words(text)))
    if problem:
        audit.log_rejection(creator_id=creator_id, reason="verify_refused",
                            message=problem, challenge_id=challenge_id)
        return jsonify({"verified": False, "message": problem}), 400

    try:
        result = _score_text(text)
    except detector.DetectorUnavailable as exc:
        return jsonify({"error": "detector_unavailable", "message": str(exc)}), 503

    if result["guess"] == "ai":
        message = ("This response read as AI-generated, so we can't verify you from it. "
                   "You can ask for a new prompt and try again in your own words.")
        audit.log_rejection(creator_id=creator_id, reason="verify_scored_ai", message=message,
                            challenge_id=challenge_id, combined_score=result["confidence"])
        return jsonify({"verified": False, "message": message, **result}), 400

    credential = credentials.grant(creator_id, challenge["challenge_id"], result)
    return jsonify({
        "verified": True,
        "creator_id": creator_id,
        "verified_at": credential["timestamp"],
        "badge": credentials.badge_text(credential),
        "message": "You're verified. Your future submissions will show this badge beside their label.",
    })


# ── Already works ─────────────────────────────────────────────────────────────

@app.get("/log")
def get_log():
    """
    The audit log, most recent last.

        curl "http://127.0.0.1:5000/log?limit=10"

    You need this in unit 8 to paste entries into your README, and you need it
    now to see whether your logging is actually working.
    """
    limit = request.args.get("limit", type=int)
    entries = audit.read_entries(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


def main():
    print(f"Provenance Guard on http://{config.HOST}:{config.PORT}")
    print(f"  detector model:  {config.DETECTOR_MODEL}")
    print(f"  rate limiting:   {'ON' if config.RATE_LIMITING_ENABLED else 'off (unit 8)'}")
    print(f"  audit log:       {config.AUDIT_LOG}")
    print(f"  run log:         {config.RUN_LOG}")
    print()
    print("Check it's alive:")
    print(f'  curl -X POST http://{config.HOST}:{config.PORT}/ping \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"message\": \"hello\"}'")
    print()
    # debug=True hands out an interactive debugger, so it's local-only — see config.py
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()