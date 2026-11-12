#!/usr/bin/env python3
"""
A load observation. (Unit 9 capstone, stretch item.)

    python load_test.py             2 requests a second, then 20 a second
    python load_test.py --save      also write results/load_<date>.md

What it is: a script that sends submissions to the RUNNING service at a
"normal" rate, then at ten times that rate, and reports what changed.

Where it's used: the "Stretch: Load Observation" part of the README is this
script's output.

Why it exists: every other measurement in the capstone sends one request,
waits for the answer, then sends the next. Real callers don't wait for each
other. This shows what happens when requests arrive faster than that.

What "normal" means here: 2 submissions a second. That is already far busier
than the hundred-a-day case in What It Costs (2 a second is 120 a minute). It
was picked so that ten times it, 20 a second, sits close to what one worker
can do: a warm request takes about 40 ms, so one worker handling them one at
a time finishes at most about 1000 / 40 = 25 a second.

How the requests are sent ("open loop"): the script works out when each
request is DUE (request i is due i / rate seconds after the start) and sends
it at that moment on its own thread, whether or not earlier ones have been
answered. A thread is a separate line of execution inside one program; using
one per request is what lets several be in flight at once. Sending the next
request only after the previous answer (a "closed loop") could never push the
service harder than it can already go, which would defeat the point.

Two different times are reported for each request, and the gap between them
is the finding:

    client latency   what the caller waited, from send to answer. Includes
                     any time the request spent queued behind others.
    service time     duration_ms from the run log: how long the service
                     worked on the request once it started on it.

Every request uses its own creator_id, so the per-creator rate limit (5 a
minute) stays out of the picture. This measures the service's capacity, not
its limiter.
"""

import argparse
import sys
import threading
import time
import uuid
from datetime import datetime

import config
import runlog
import scenarios

DEFAULT_URL = f"http://{config.HOST}:{config.PORT}"


def percentile(values: list[float], fraction: float) -> float:
    """
    The value below which `fraction` of the values fall.

    percentile(v, 0.5) is the median: half the requests were faster. 0.95
    means 95% were faster, so it describes the slow end without being decided
    by one freak request the way the maximum is. Method: sort, then take the
    item `fraction` of the way along (the "nearest rank" method).
    """
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(fraction * len(ordered)))
    return ordered[index]


def run_phase(url: str, rate: float, seconds: float, tag: str) -> dict:
    """
    Send `rate` submissions a second for `seconds` seconds and collect results.

    Returns a dict of the numbers the report needs.
    """
    import requests

    count = int(rate * seconds)
    texts = scenarios.MY_OWN_WRITING
    # One slot per request. Each thread writes only its own slot, so the
    # threads never touch the same item and no lock is needed.
    outcomes: list[dict | None] = [None] * count

    def send(i: int):
        started = time.perf_counter()
        try:
            response = requests.post(
                f"{url}/submit",
                # % wraps around the ten paragraphs however many requests there are.
                json={"text": texts[i % len(texts)], "creator_id": f"load_{tag}_{i:04d}"},
                timeout=60,
            )
            outcomes[i] = {
                "status": response.status_code,
                "request_id": response.headers.get("X-Request-ID"),
                "client_ms": (time.perf_counter() - started) * 1000,
            }
        except Exception as exc:  # noqa: BLE001 — a failed request is a result to report
            outcomes[i] = {"status": type(exc).__name__, "request_id": None,
                           "client_ms": (time.perf_counter() - started) * 1000}

    threads = []
    phase_started = time.perf_counter()
    for i in range(count):
        # When request i is due, measured from the start of the phase.
        due = phase_started + i / rate
        wait = due - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        thread = threading.Thread(target=send, args=(i,))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()          # wait until every answer is in
    elapsed = time.perf_counter() - phase_started

    # Read the run log once and index it by request id, instead of re-reading
    # the whole file for each of several hundred requests.
    by_id = {r.get("request_id"): r for r in runlog.read_runs()}
    ok = [o for o in outcomes if o and o["status"] == 200]
    records = [by_id[o["request_id"]] for o in ok if o["request_id"] in by_id]

    statuses: dict[str, int] = {}
    for o in outcomes:
        key = str(o["status"]) if o else "no result"
        statuses[key] = statuses.get(key, 0) + 1

    client = [o["client_ms"] for o in ok]
    service = [r["duration_ms"] for r in records]
    cpu = [r["cpu_ms"] for r in records]
    return {
        "rate": rate, "sent": count, "statuses": statuses, "elapsed": elapsed,
        "logged": len(records),
        "client": client, "service": service,
        "cpu_mean": sum(cpu) / len(cpu) if cpu else float("nan"),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare the service at a normal rate and at ten times it.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--normal-rate", type=float, default=2.0,
                        help="submissions a second in the normal phase (default 2)")
    parser.add_argument("--seconds", type=float, default=15.0,
                        help="how long each phase lasts (default 15)")
    parser.add_argument("--save", action="store_true",
                        help="also write the report to results/load_<date>.md")
    args = parser.parse_args()

    try:
        import requests
        requests.get(f"{args.url}/health", timeout=5).json()
        # One submission first, so gpt2 is in memory before anything is timed.
        requests.post(f"{args.url}/submit", timeout=120,
                      json={"text": scenarios.MY_OWN_WRITING[0],
                            "creator_id": f"load_warmup_{uuid.uuid4().hex[:6]}"})
    except Exception as exc:  # noqa: BLE001 — a reader gets this, not a traceback
        sys.exit(f"The service isn't answering at {args.url} ({exc}).\nStart it first: see RUNNING.md.")

    tag = uuid.uuid4().hex[:6]
    normal = run_phase(args.url, args.normal_rate, args.seconds, tag + "n")
    time.sleep(2)   # let the service go idle between the two phases
    heavy = run_phase(args.url, args.normal_rate * 10, args.seconds, tag + "h")

    def row(label: str, pick) -> str:
        return f"| {label} | {pick(normal)} | {pick(heavy)} |"

    def spread(values: list[float]) -> str:
        if not values:
            return "no data"
        return (f"{percentile(values, 0.5):.1f} / {percentile(values, 0.95):.1f} / "
                f"{max(values):.1f}")

    lines = [
        f"Load observation, {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Service: {args.url}   each phase: {args.seconds:.0f} s   run tag: {tag}",
        "",
        f"| Measure | Normal ({normal['rate']:g} a second) | Ten times ({heavy['rate']:g} a second) |",
        "|---|---|---|",
        row("Requests sent", lambda p: p["sent"]),
        row("Responses by status", lambda p: ", ".join(f"{k}: {v}" for k, v in sorted(p["statuses"].items()))),
        row("Found in the run log", lambda p: f"{p['logged']} of {p['statuses'].get('200', 0)}"),
        row("Client latency ms, median / 95th / max", lambda p: spread(p["client"])),
        row("Service time ms, median / 95th / max", lambda p: spread(p["service"])),
        row("CPU ms per request, mean", lambda p: f"{p['cpu_mean']:.1f}"),
        row("Seconds until every answer was in", lambda p: f"{p['elapsed']:.1f}"),
        row("Answers per second achieved", lambda p: f"{p['statuses'].get('200', 0) / p['elapsed']:.1f}"),
    ]
    print("\n".join(lines))

    if args.save:
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = config.RESULTS_DIR / f"load_{datetime.now().strftime('%Y-%m-%d_%H%M')}.md"
        path.write_text("# Load observation\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
