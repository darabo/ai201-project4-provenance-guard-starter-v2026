#!/usr/bin/env python3
"""
What one run costs. (Unit 9, the capstone.)

What it is: a script that sends real submissions to the RUNNING service and
reports how much compute each one used, read back out of the run log.

    python measure_cost.py              ten submissions, the unit's requirement
    python measure_cost.py --runs 20    more of them
    python measure_cost.py --save       also write results/cost_<date>.md

Where it's used: the "What It Costs" section of the README is this script's
output.

Why it exists: Provenance Guard calls no paid API, so a run costs no money
directly. What it costs is processor time on the machine running gpt2. That
has to be MEASURED, because it depends on this laptop, this build of torch
and the length of the text, none of which a pricing page knows.

How the measurement works:

  1. Send one warm-up submission. The first scored request after a start has
     to load gpt2 into memory, which takes seconds and happens once per start,
     not once per run. It's reported on its own line and left out of the
     average.
  2. Send N submissions, one at a time. The texts are the ten paragraphs of my
     own writing from scenarios.py: real inputs of realistic length (about 50
     to 90 words each).
  3. Each response carries an X-Request-ID header. Look that id up in
     logs/runs.jsonl and read the service's OWN timing for the request.

Step 3 matters. Timing from this script's side would include the time to send
the request and receive the answer. The run log's numbers were taken inside
the service, around the work itself.

Every submission uses a different creator_id. The rate limit is 5 a minute
per creator, so ten from one creator would get five 429s. Ten different
writers each submitting once is also the situation the "a hundred people a
day" arithmetic describes.
"""

import argparse
import sys
import time
import uuid
from datetime import datetime

import config
import runlog
import scenarios

DEFAULT_URL = f"http://{config.HOST}:{config.PORT}"


def submit(url: str, text: str, creator_id: str):
    """
    Send one submission. Returns (status_code, request_id, client_ms).

    `client_ms` is the elapsed time seen from this side of the connection, in
    milliseconds. It's kept only to compare against the service's own figure.
    """
    import requests  # imported here so --help works without it installed

    started = time.perf_counter()
    response = requests.post(
        f"{url}/submit",
        json={"text": text, "creator_id": creator_id},
        # Seconds to wait before giving up. Generous because the warm-up
        # request may be loading a 550 MB model on a slow disk.
        timeout=120,
    )
    client_ms = round((time.perf_counter() - started) * 1000, 1)
    return response.status_code, response.headers.get("X-Request-ID"), client_ms


def average(values: list[float]) -> float:
    """The mean: add them up, divide by how many there are."""
    return sum(values) / len(values)


def main():
    parser = argparse.ArgumentParser(description="Measure the compute cost of one run.")
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"where the service is listening (default {DEFAULT_URL})")
    parser.add_argument("--runs", type=int, default=10,
                        help="how many submissions to measure (default 10)")
    parser.add_argument("--save", action="store_true",
                        help="also write the report to results/cost_<date>.md")
    args = parser.parse_args()

    try:
        import requests
        requests.get(f"{args.url}/health", timeout=5)
    except Exception as exc:  # noqa: BLE001 — a reader gets this, not a traceback
        sys.exit(f"The service isn't answering at {args.url} ({exc}).\n"
                 f"Start it first: see RUNNING.md.")

    # A random tag for this measurement, so its creator_ids can't collide with
    # an earlier run's and trip the per-creator rate limit.
    tag = uuid.uuid4().hex[:6]
    texts = scenarios.MY_OWN_WRITING
    lines: list[str] = []

    def say(line: str = ""):
        """Print a line and keep it, so --save writes exactly what was shown."""
        print(line)
        lines.append(line)

    say(f"Cost measurement, {datetime.now().astimezone().isoformat(timespec='seconds')}")
    say(f"Service: {args.url}   model: {config.DETECTOR_MODEL}   runs: {args.runs}")
    say()

    # Step 1: the warm-up, reported but not averaged.
    status, request_id, client_ms = submit(args.url, texts[0], f"cost_{tag}_warmup")
    record = runlog.find(request_id) if request_id else None
    if status != 200 or record is None:
        sys.exit(f"Warm-up failed: status {status}, run record found: {record is not None}.")
    say(f"Warm-up (not in the average): {record['duration_ms']} ms elapsed, "
        f"{record['cpu_ms']} ms CPU, cold_start={record['cold_start']}")
    say()

    # Step 2 and 3: the measured runs.
    say("| Run | Words | Status | Elapsed ms | CPU ms | Model ms | Client ms |")
    say("|---|---|---|---|---|---|---|")
    elapsed, cpu, model = [], [], []
    for i in range(args.runs):
        # The % (remainder) wraps around the text list, so --runs 20 reuses
        # the ten paragraphs twice instead of running off the end.
        text = texts[i % len(texts)]
        status, request_id, client_ms = submit(args.url, text, f"cost_{tag}_{i:02d}")
        record = runlog.find(request_id) if request_id else None
        if status != 200 or record is None:
            # A failed run is shown, not hidden, and stays out of the average:
            # a rejection costs almost nothing and would drag the mean down.
            say(f"| {i + 1} | {len(text.split())} | {status} | (no usable record) | | | {client_ms} |")
            continue
        elapsed.append(record["duration_ms"])
        cpu.append(record["cpu_ms"])
        model.append(record.get("stages_ms", {}).get("model", 0.0))
        say(f"| {i + 1} | {record['input'].get('text_words')} | {status} | "
            f"{record['duration_ms']} | {record['cpu_ms']} | {model[-1]} | {client_ms} |")

    if not elapsed:
        sys.exit("No run succeeded, so there is nothing to average.")

    say()
    say(f"Successful runs averaged: {len(elapsed)} of {args.runs}")
    say(f"Elapsed per run:  mean {average(elapsed):.1f} ms   "
        f"(min {min(elapsed):.1f}, max {max(elapsed):.1f})")
    say(f"CPU per run:      mean {average(cpu):.1f} ms   "
        f"(min {min(cpu):.1f}, max {max(cpu):.1f})")
    say(f"gpt2 share:       mean {average(model):.1f} ms of the elapsed time "
        f"({100 * average(model) / average(elapsed):.0f}%)")

    if args.save:
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        path = config.RESULTS_DIR / f"cost_{stamp}.md"
        path.write_text("# Cost measurement\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
