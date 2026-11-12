#!/usr/bin/env python3
"""
The run log. (Unit 9, the capstone.)

What it is: a writer for `logs/runs.jsonl`, a file with one JSON object per
line, one line for every HTTP request the service answers. "JSONL" just means
"JSON Lines": each line is a complete JSON object on its own, so the file can
be appended to forever and read back one line at a time.

Where it's used: `app.py` calls `write()` from a hook that Flask runs after
every request. `measure_cost.py` calls `read_runs()` to pull timings back out.

Why it exists when `audit.py` already writes a log: the audit log records
DECISIONS (a label was given, an appeal was filed, a request was refused). It
has no idea how long anything took, and a request that never reaches a
decision (a wrong URL, a crash, a GET /health) leaves nothing in it. The run
log records REQUESTS: every one, with what came in, what went out, and how
long it took. The two answer different questions, so they stay separate files.

One record looks like this:

    {
      "timestamp":   "2026-11-11T21:40:03.512+00:00",   when the request arrived (UTC)
      "request_id":  "r_3f9a1c2b7d4e",                  also sent back as the X-Request-ID header
      "method":      "POST",
      "path":        "/submit",
      "input":       {...},      what came in   (see summarize_input)
      "output":      {...},      what went out  (see summarize_output)
      "outcome":     "ok",       ok = 2xx/3xx, rejected = 4xx, error = 5xx
      "duration_ms": 412.7,      wall-clock time for the whole request
      "cpu_ms":      1630.2,     processor time the service burned meanwhile
      "stages_ms":   {...},      time per signal, only when text was scored
      "cold_start":  false       true when gpt2 was not yet in memory
    }

From a terminal:

    python runlog.py --tail 10      the last ten records, one per line
    python runlog.py --count        how many records, split by outcome
    python runlog.py --stages       where the time goes inside a scored request
"""

import json
import threading
import uuid
from datetime import datetime, timezone

import config

# A lock is a "one at a time" token. The service can answer several requests
# at once on different threads; without the lock two of them could write to
# the file at the same moment and interleave half a line each, leaving a row
# that isn't valid JSON.
_lock = threading.Lock()

# How much of a submitted text the log keeps. The log is for diagnosing the
# service, not for storing people's writing, so it keeps the length and the
# first 60 characters (about ten words: enough to recognise which test input
# a row was) and nothing more.
PREVIEW_CHARS = 60

# The response fields worth keeping in "what went out". Anything not named
# here is dropped, which keeps a `GET /log` response (hundreds of entries)
# from being copied into the run log.
_OUTPUT_FIELDS = (
    "content_id", "guess", "confidence", "model_score", "style_score",
    "marker_score", "status", "error", "verified", "ok", "count",
)


def now() -> str:
    """
    The current time in UTC, ISO 8601, to the millisecond.

    The audit log rounds to whole seconds. Here requests can be a few hundred
    milliseconds apart, and whole seconds would make several of them look
    simultaneous, so this keeps three decimal places.
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_request_id() -> str:
    """
    A short random id for one request, like `r_3f9a1c2b7d4e`.

    uuid4().hex is 32 random hexadecimal characters. Twelve of them allow
    16^12 (about 2.8e14) different ids, far more than this log will ever hold.
    The id goes back to the caller in a response header, so someone who sent a
    request can find exactly its row in the log afterwards.
    """
    return f"r_{uuid.uuid4().hex[:12]}"


def summarize_input(payload, body_bytes: int) -> dict:
    """
    Describe what came in, without storing all of it.

    `payload` is the request body after Flask tried to parse it as JSON: a
    dict for a normal request, a list or string for an odd one, and None when
    there was no body or it wasn't valid JSON. `body_bytes` is the raw size.
    """
    summary: dict = {"body_bytes": body_bytes}

    if payload is None:
        # No body at all (every GET), or bytes that don't parse as JSON. The
        # size tells the two apart. A body that is literally the JSON word
        # `null` also lands here, because it parses to Python's None.
        summary["body_type"] = "empty" if body_bytes == 0 else "unparseable"
        return summary

    if not isinstance(payload, dict):
        # Valid JSON but not an object, e.g. a bare list. There are no fields
        # to read, so the type name is all there is to record.
        summary["body_type"] = type(payload).__name__
        return summary

    summary["body_type"] = "object"
    # Field NAMES are always safe to keep and show at a glance what was
    # missing. Capped at ten so a body with thousands of keys can't bloat a row.
    summary["fields"] = sorted(str(key) for key in payload)[:10]

    creator_id = payload.get("creator_id")
    if isinstance(creator_id, str):
        summary["creator_id"] = creator_id.strip()[:80]

    content_id = payload.get("content_id")
    if isinstance(content_id, str):
        summary["content_id"] = content_id.strip()[:80]

    text = payload.get("text")
    if isinstance(text, str):
        summary["text_chars"] = len(text)
        # split() with no argument breaks on any run of whitespace, which is
        # a good-enough word count for a log line.
        summary["text_words"] = len(text.split())
        summary["text_preview"] = text[:PREVIEW_CHARS]

    return summary


def summarize_output(status_code: int, body) -> dict:
    """
    Describe what went out: the HTTP status and the few fields that matter.

    `body` is the response parsed as JSON, or None if it wasn't JSON (Flask's
    own 404 and 500 pages are HTML).
    """
    summary: dict = {"status_code": status_code}
    if isinstance(body, dict):
        for field in _OUTPUT_FIELDS:
            if field in body:
                summary[field] = body[field]

    # Unit 9 improvement (capstone criterion 2). Every refusal or failure
    # must carry an error code. The routes in app.py put one in their JSON
    # body, and the loop above copies it. But some responses are written by
    # Flask itself and are HTML pages with no JSON at all: an unknown URL
    # (404), the wrong method for a route (405), an unhandled crash (500).
    # Before this change those were logged with a status code and nothing
    # else. Now a code is derived from the status whenever the body didn't
    # supply one. "error_source" marks it as derived, so the log still shows
    # whether the service named the error or the status code did.
    if status_code >= 400 and "error" not in summary:
        summary["error"] = error_code_for(status_code)
        summary["error_source"] = "http_status"
    return summary


def error_code_for(status_code: int) -> str:
    """
    A short error code made from an HTTP status number.

    Python's standard library knows the official name of every status code:
    HTTPStatus(404).phrase is "Not Found". Lower-casing it and swapping
    spaces and hyphens for underscores gives `not_found`, the same style as
    the codes the routes write by hand (`bad_request`, `rate_limited`).
    A number the library doesn't recognise becomes e.g. `http_499`.
    """
    from http import HTTPStatus

    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        return f"http_{status_code}"
    return phrase.lower().replace(" ", "_").replace("-", "_")


def outcome_for(status_code: int) -> str:
    """
    One word for how the request ended, from its HTTP status code.

    HTTP groups status codes by their first digit: 2xx means it worked, 4xx
    means the caller sent something the service refused (400 bad input, 404
    no such thing, 429 too many requests), and 5xx means the service itself
    failed (500 crashed, 503 model unavailable).
    """
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "rejected"
    return "ok"


def write(record: dict) -> dict:
    """
    Append one record to the run log and return it.

    The file is opened in "a" (append) mode, so existing lines are never
    rewritten; a new line goes on the end.
    """
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False keeps curly quotes and accents readable in the file
    # instead of turning them into ’-style escapes.
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        with config.RUN_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return record


def read_runs(limit: int | None = None) -> list[dict]:
    """
    Read the run log back, oldest first. `limit` keeps the most recent N.

    A line that isn't valid JSON is skipped instead of raising: a log that
    can't be read at all because of one bad row is worse than one with a gap.
    """
    if not config.RUN_LOG.exists():
        return []

    records = []
    for line in config.RUN_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return records[-limit:] if limit else records


def find(request_id: str) -> dict | None:
    """The record for one request id, or None if it isn't in the log."""
    for record in read_runs():
        if record.get("request_id") == request_id:
            return record
    return None


def stage_breakdown(records: list[dict]) -> list[str]:
    """
    Where the time goes inside one scored request. (Capstone stretch item.)

    Uses every record that scored a text successfully with gpt2 already in
    memory ("warm"). For each stage it reports the mean time and what share
    of the whole request that is. Returns the report as a list of lines.

    The four timed stages come from the stopwatch readings in
    app.py::_score_text. "everything else" is the request's total time minus
    those four: reading and checking the body, the rate-limit check, the
    credential lookup, writing the audit entry and building the response.
    Nothing times those individually; they are what's left over.

    Cold starts (the first scored request after a start, which also loads the
    model) are reported on their own line, because averaging one 2-second
    request in with forty-millisecond ones would describe neither.
    """
    scored = [r for r in records
              if r.get("stages_ms") and r.get("outcome") == "ok" and r.get("duration_ms") is not None]
    warm = [r for r in scored if not r.get("cold_start")]
    cold = [r for r in scored if r.get("cold_start")]
    if not warm:
        return ["No warm scored requests in the log yet."]

    def mean(values):
        return sum(values) / len(values)

    total = mean([r["duration_ms"] for r in warm])
    stages = ["model", "style", "markers", "scoring"]
    means = {name: mean([r["stages_ms"].get(name, 0.0) for r in warm]) for name in stages}
    # Whatever the four stages don't account for.
    means["everything else"] = total - sum(means.values())

    labels = {
        "model": "gpt2 perplexity (detector.py)",
        "style": "style measures (stylometry.py)",
        "markers": "stock-phrase search (markers.py)",
        "scoring": "combine and label (scoring.py)",
        "everything else": "everything else (checks, audit write, response)",
    }
    lines = [
        f"Warm scored requests: {len(warm)}   mean total: {total:.2f} ms",
        "",
        "| Stage | Mean ms | Share of the request |",
        "|---|---|---|",
    ]
    for name, value in means.items():
        # Share = this stage's mean divided by the mean total, as a percentage.
        lines.append(f"| {labels[name]} | {value:.2f} | {100 * value / total:.1f}% |")
    lines.append(f"| **whole request** | {total:.2f} | 100.0% |")

    if cold:
        cold_total = mean([r["duration_ms"] for r in cold])
        cold_model = mean([r["stages_ms"].get("model", 0.0) for r in cold])
        lines += ["", f"Cold starts: {len(cold)}   mean total: {cold_total:.1f} ms, "
                      f"of which the model stage (load + first pass): {cold_model:.1f} ms "
                      f"({100 * cold_model / cold_total:.1f}%)"]
    return lines


def main():
    """The small command-line reader described at the top of this file."""
    import argparse

    parser = argparse.ArgumentParser(description="Read logs/runs.jsonl.")
    parser.add_argument("--tail", type=int, metavar="N",
                        help="print the last N records, one JSON object per line")
    parser.add_argument("--count", action="store_true",
                        help="print how many records there are, by outcome")
    parser.add_argument("--stages", action="store_true",
                        help="print where the time goes inside a scored request")
    args = parser.parse_args()

    records = read_runs()

    if args.stages:
        print("\n".join(stage_breakdown(records)))
        return

    if args.count:
        by_outcome: dict[str, int] = {}
        for record in records:
            outcome = record.get("outcome", "unknown")
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        print(f"{len(records)} records in {config.RUN_LOG}")
        for outcome, count in sorted(by_outcome.items()):
            print(f"  {outcome:<10} {count}")
        return

    # Default to the last ten, the number the README asks to have pasted.
    for record in records[-(args.tail or 10):]:
        print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
