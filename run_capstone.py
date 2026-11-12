#!/usr/bin/env python3
"""
The capstone test: five criteria, three trials each. (Unit 9.)

    python run_capstone.py --label before          all five criteria
    python run_capstone.py --label after           the same set, after a fix
    python run_capstone.py --label before --only 2 4    just some of them

What it is: a script that runs every capstone criterion in criteria.md three
times against the real service and writes down what came back.

Where it's used: Milestone 5 (the "before" run) and Milestone 6 (the "after"
run). Its output files are what the README's Run Log tables are copied from:

    results/capstone_<date>_<label>.md      the table, then real output per trial
    results/capstone_<date>_<label>.json    the same results as data

Why it exists: unit 8's run_eval.py tests the unit 7 criteria. These five are
about the run path and the run log, which run_eval.py knows nothing about.

Three decisions about HOW the test runs, so a reader can judge the results:

  1. This script starts the service itself, with exactly the command in
     RUNNING.md, and stops it afterwards. Stop your own copy first: two
     services can't share port 5000.

  2. The service is restarted before each criterion. Rate-limit counts live
     in the service's memory, so a restart clears them, and one criterion's
     requests can't use up another criterion's allowance. Within a criterion
     the three trials run back to back against the same running service.

  3. Nothing here decides a verdict by judgment. Each trial counts how many
     checks passed, and a criterion is MET only when all three trials reach
     the target written in criteria.md.

Each criterion is one function below, named criterion_1 to criterion_5, so
the README can point at exactly the code that produced a result.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import config
import runlog
import scenarios

# 127.0.0.1, never "localhost": on a Mac "localhost" can reach AirPlay
# Receiver, which also listens on port 5000 (see RUNNING.md).
URL = "http://127.0.0.1:5000"

# The start command, word for word as RUNNING.md gives it.
START_COMMAND = "gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120"

# The line gunicorn prints once its worker process exists. Criterion 1 says
# the health check goes out after this line appears.
BOOT_LINE = "Booting worker with pid"

REPO = Path(__file__).parent
TRIALS = 3


# ── Starting and stopping the service ────────────────────────────────────────

class Service:
    """
    One running copy of the service, started from a shell script.

    `script` is the text of a small bash script whose last line starts
    gunicorn. Everything the script prints goes to `log_path`, and start()
    watches that file for BOOT_LINE to know the service is up.
    """

    def __init__(self, script: str, cwd: Path, log_path: Path, boot_timeout: float):
        self.script = script
        self.cwd = cwd
        self.log_path = log_path
        self.boot_timeout = boot_timeout   # seconds to wait for BOOT_LINE
        self.proc = None
        self._log_file = None

    def start(self):
        env = dict(os.environ)
        # Put this Python's own folder first on PATH. When the script is run
        # as `.venv/bin/python run_capstone.py` without activating the
        # virtual environment, this is what lets the bare word `gunicorn`
        # still find the copy installed in .venv.
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

        self._log_file = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            ["bash", "-c", self.script],
            cwd=self.cwd,
            env=env,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,     # errors go to the same log file
            # A new "session" puts bash and everything it starts into their
            # own process group, so stop() can signal the whole group at once
            # and no gunicorn worker is left running afterwards.
            start_new_session=True,
        )

        deadline = time.monotonic() + self.boot_timeout
        while time.monotonic() < deadline:
            if BOOT_LINE in self.log_text():
                return
            # poll() is None while the process is alive. Anything else means
            # the script ended before gunicorn came up (a failed install, a
            # port already in use), and waiting longer won't help.
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"the start script exited with code {self.proc.returncode} before "
                    f"gunicorn was up. Last output:\n{self.log_tail(15)}"
                )
            time.sleep(0.25)
        self.stop()
        raise RuntimeError(f"no '{BOOT_LINE}' line within {self.boot_timeout:.0f}s. "
                           f"Last output:\n{self.log_tail(15)}")

    def log_text(self) -> str:
        return self.log_path.read_text(encoding="utf-8", errors="replace")

    def log_tail(self, lines: int) -> str:
        return "\n".join(self.log_text().splitlines()[-lines:])

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            # SIGTERM is the polite "please shut down" signal; gunicorn
            # finishes any request in progress and exits.
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                # Still alive after 15 seconds: SIGKILL cannot be ignored.
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(timeout=5)
        if self._log_file is not None:
            self._log_file.close()
        # Give the operating system a moment to release port 5000 before the
        # next start asks for it.
        time.sleep(0.5)


def call(method: str, path: str, body=None) -> dict:
    """
    Send one request and return what came back as a plain dict.

    Keys: status (the HTTP status code, or None if nothing answered), json
    (the parsed body, or None if it wasn't JSON), request_id (the
    X-Request-ID header, or None), and error (why nothing answered).
    """
    import requests

    try:
        response = requests.request(method, URL + path, json=body, timeout=60)
    except Exception as exc:  # noqa: BLE001 — recorded as a failed check, not a crash
        return {"status": None, "json": None, "request_id": None, "error": repr(exc)}
    try:
        parsed = response.json()
    except ValueError:
        parsed = None          # Flask's own 404 page is HTML, not JSON
    return {
        "status": response.status_code,
        "json": parsed,
        "request_id": response.headers.get("X-Request-ID"),
        "error": None,
    }


def records_for(request_id: str | None) -> list[dict]:
    """Every run-log record carrying this request id. The criteria want exactly one."""
    if not request_id:
        return []
    return [r for r in runlog.read_runs() if r.get("request_id") == request_id]


def something_already_listening() -> bool:
    """True if a copy of the service already answers on port 5000."""
    answer = call("GET", "/health")
    return isinstance(answer["json"], dict) and answer["json"].get("ok") is True


def start_main_service(scratch: Path, name: str) -> Service:
    """Start the service from this repository with the RUNNING.md command."""
    service = Service(
        # `exec` replaces bash with gunicorn instead of running it as a child,
        # so the process this script holds IS gunicorn.
        script=f"exec {START_COMMAND}",
        cwd=REPO,
        log_path=scratch / f"server_{name}.log",
        boot_timeout=60,
    )
    service.start()
    return service


def trial(score: int, out_of: int, target: int, lines: list[str]) -> dict:
    """Package one trial's result. It passes when score reaches target."""
    return {"score": f"{score}/{out_of}", "passed": score >= target, "lines": lines}


# ── Criterion 1: reproducible local run path ─────────────────────────────────

# The "From a clean checkout" block in RUNNING.md, line for line. Two things
# differ, and both are stated in the report: the clone comes from $SOURCE
# (this folder by default, because capstone commits may not be pushed yet),
# and the folder is called `repo`.
CLEAN_START_SCRIPT = f"""
set -e
git clone -q "$SOURCE" repo
cd repo
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python detector.py
exec {START_COMMAND}
"""


def criterion_1(n: int, tag: str, scratch: Path, source: str) -> dict:
    """
    One clean start: fresh clone, new virtual environment, install, start,
    then GET /health and one POST /submit. Two checks, both must pass.
    """
    lines = [f"source cloned: {source}"]
    # mkdtemp makes a new, empty folder with a unique name.
    folder = Path(tempfile.mkdtemp(prefix=f"pg_clean_{tag}_{n}_"))
    os.environ["SOURCE"] = source
    service = Service(CLEAN_START_SCRIPT, cwd=folder,
                      log_path=scratch / f"clean_start_{n}.log",
                      boot_timeout=900)   # 15 minutes: pip may download torch
    score = 0
    started = time.monotonic()
    try:
        service.start()
        lines.append(f"'{BOOT_LINE}' seen after {time.monotonic() - started:.1f}s")
        lines.append("last lines of the start output:")
        lines += ["  " + line for line in service.log_tail(6).splitlines()]

        health = call("GET", "/health")
        lines.append(f"GET /health -> {health['status']} {json.dumps(health['json'])}")
        if health["status"] == 200 and isinstance(health["json"], dict) and health["json"].get("ok") is True:
            score += 1

        # The same body the RUNNING.md curl command sends, read from the clone.
        body = json.loads((folder / "repo" / "samples" / "clearly_ai.json").read_text(encoding="utf-8"))
        submit = call("POST", "/submit", body)
        lines.append(f"POST /submit -> {submit['status']} {json.dumps(submit['json'])[:200]}")
        if submit["status"] == 200:
            score += 1

        # The clone has its own logs/ folder. Quote its last run record before
        # the clone is deleted, as proof the fresh copy logged the request.
        clone_log = folder / "repo" / "logs" / "runs.jsonl"
        if clone_log.exists():
            lines.append("last record in the clone's logs/runs.jsonl:")
            lines.append("  " + clone_log.read_text(encoding="utf-8").splitlines()[-1])
    except Exception as exc:  # noqa: BLE001 — a failed start is a result, not a crash
        lines.append(f"FAILED: {exc}")
    finally:
        service.stop()
        # Each clone holds about 950 MB of installed packages. Delete it.
        shutil.rmtree(folder, ignore_errors=True)
    return trial(score, 2, 2, lines)


# ── Criterion 2: complete structured run logging ─────────────────────────────

REQUIRED_FIELDS = ("timestamp", "request_id", "method", "path",
                   "input", "output", "outcome", "duration_ms")


def criterion_2(n: int, tag: str) -> dict:
    """
    One session of the ten requests listed in criteria.md. A request passes
    when its X-Request-ID matches exactly one run record and that record has
    every required field.
    """
    own = scenarios.MY_OWN_WRITING
    who = f"c2_{tag}_s{n}"            # unique per session, so no rate limit carries over
    lines: list[str] = []
    score = 0
    first_content_id = "missing"

    # (method, path, body) for requests 1 to 10. Request 8 needs the
    # content_id that request 2 returns, so it's filled in during the loop.
    plan = [
        ("GET", "/health", None),
        ("POST", "/submit", {"text": own[0], "creator_id": f"{who}_a"}),
        ("POST", "/submit", {"text": own[1], "creator_id": f"{who}_b"}),
        ("POST", "/submit", {"text": own[2], "creator_id": f"{who}_c"}),
        ("POST", "/submit", {"text": own[3], "creator_id": f"{who}_d"}),
        ("POST", "/submit", {"text": "", "creator_id": f"{who}_e"}),
        ("POST", "/submit", [1, 2, 3]),
        ("POST", "/appeal", None),     # body built below
        ("POST", "/appeal", {"content_id": "c_doesnotexist", "reasoning": "This id was never issued."}),
        ("GET", "/submitt", None),
    ]

    for number, (method, path, body) in enumerate(plan, start=1):
        if number == 8:
            body = {"content_id": first_content_id, "reasoning": "I wrote this myself."}
        answer = call(method, path, body)
        if number == 2 and isinstance(answer["json"], dict):
            first_content_id = answer["json"].get("content_id", "missing")

        matches = records_for(answer["request_id"])
        problems: list[str] = []
        if not answer["request_id"]:
            problems.append("no X-Request-ID header")
        if len(matches) != 1:
            problems.append(f"{len(matches)} matching records (need exactly 1)")
        else:
            record = matches[0]
            output = record.get("output") or {}
            for field in REQUIRED_FIELDS:
                if record.get(field) is None:
                    problems.append(f"record has no {field}")
            status = answer["status"] or 0
            if method == "POST" and path == "/submit" and status == 200:
                for field in ("content_id", "guess", "confidence"):
                    if field not in output:
                        problems.append(f"output has no {field}")
            if 400 <= status < 500:
                for field in ("status_code", "error"):
                    if field not in output:
                        problems.append(f"output has no {field}")

        verdict = "ok" if not problems else "FAIL: " + "; ".join(problems)
        lines.append(f"{number:>2}. {method} {path} -> {answer['status']}  "
                     f"{answer['request_id']}  {verdict}")
        if problems and matches:
            # Show the actual record behind every failure.
            lines.append("    " + json.dumps(matches[0], ensure_ascii=False))
        if not problems:
            score += 1

    return trial(score, 10, 10, lines)


# ── Criterion 3: bad submission input is rejected and logged ─────────────────

def criterion_3(n: int, tag: str) -> dict:
    """
    The five invalid bodies. A body passes when the response is 400 with a
    JSON `error` field and its one run record says rejected / 400 / has an
    error code / has a duration.
    """
    who = f"c3_{tag}_trial{n}"        # a creator_id not used before this trial
    bodies = [
        ("missing text", {"creator_id": who}),
        ("empty text", {"text": "", "creator_id": who}),
        ("whitespace-only text", {"text": "   ", "creator_id": who}),
        ("non-string text", {"text": 12345, "creator_id": who}),
        ("JSON array", [1, 2, 3]),
    ]
    lines: list[str] = []
    score = 0
    for name, body in bodies:
        answer = call("POST", "/submit", body)
        matches = records_for(answer["request_id"])
        problems: list[str] = []
        if answer["status"] != 400:
            problems.append(f"status {answer['status']} (need 400)")
        if not (isinstance(answer["json"], dict) and "error" in answer["json"]):
            problems.append("response has no JSON error field")
        if len(matches) != 1:
            problems.append(f"{len(matches)} matching records (need exactly 1)")
        else:
            record = matches[0]
            output = record.get("output") or {}
            if record.get("outcome") != "rejected":
                problems.append(f"outcome is {record.get('outcome')!r}")
            if output.get("status_code") != 400:
                problems.append(f"output.status_code is {output.get('status_code')!r}")
            if "error" not in output:
                problems.append("output has no error code")
            if record.get("duration_ms") is None:
                problems.append("record has no duration_ms")

        verdict = "ok" if not problems else "FAIL: " + "; ".join(problems)
        lines.append(f"{name}: -> {answer['status']} {json.dumps(answer['json'])[:110]}  {verdict}")
        for record in matches[:1]:
            lines.append("    " + json.dumps(record, ensure_ascii=False))
        if not problems:
            score += 1
    return trial(score, 5, 5, lines)


# ── Criterion 4: warm submissions remain responsive ──────────────────────────

LATENCY_LIMIT_MS = 500      # from criterion 4
RESPONSE_FIELDS = ("content_id", "model_score", "style_score", "confidence", "label")


def criterion_4(n: int, tag: str) -> dict:
    """
    Warm up, confirm the detector is loaded, then send the ten paragraphs.
    A request passes when it returns 200 and the run log's duration_ms for it
    is at most 500. The target is 9 of 10. Separately, every 200 response
    must carry the five response fields, or the trial fails whatever the count.
    """
    who = f"c4_{tag}_t{n}"
    lines: list[str] = []

    warm = call("POST", "/submit", {"text": scenarios.MY_OWN_WRITING[0], "creator_id": f"{who}_warm"})
    warm_record = (records_for(warm["request_id"]) or [{}])[0]
    lines.append(f"warm-up -> {warm['status']}, duration_ms {warm_record.get('duration_ms')}, "
                 f"cold_start {warm_record.get('cold_start')}")
    health = call("GET", "/health")
    loaded = isinstance(health["json"], dict) and health["json"].get("detector_loaded") is True
    lines.append(f"GET /health -> detector_loaded: {loaded}")

    score = 0
    fields_ok = True
    for i, text in enumerate(scenarios.MY_OWN_WRITING):
        answer = call("POST", "/submit", {"text": text, "creator_id": f"{who}_{i:02d}"})
        record = (records_for(answer["request_id"]) or [{}])[0]
        duration = record.get("duration_ms")
        in_time = answer["status"] == 200 and duration is not None and duration <= LATENCY_LIMIT_MS
        missing = []
        if answer["status"] == 200:
            missing = [f for f in RESPONSE_FIELDS if f not in (answer["json"] or {})]
            if missing:
                fields_ok = False
        lines.append(f"{i + 1:>2}. {len(text.split())} words -> {answer['status']}, "
                     f"duration_ms {duration}, {'within' if in_time else 'OVER or failed'}"
                     + (f", response missing {missing}" if missing else ""))
        if i == 0 and record:
            lines.append("    " + json.dumps(record, ensure_ascii=False))
        if in_time:
            score += 1

    result = trial(score, 10, 9, lines)
    # The warm-up conditions and the response fields are part of the
    # criterion, so failing either fails the trial even at 10/10.
    if not (warm["status"] == 200 and loaded and fields_ok):
        result["passed"] = False
        lines.append("FAIL: warm-up, detector_loaded or response fields not as required")
    return result


# ── Criterion 5: appeals preserve the original evidence ──────────────────────

def criterion_5(n: int, tag: str) -> dict:
    """
    Submit, appeal, then look in two places. Four checks:
      1. the appeal returns 200 with status under_review
      2. GET /log holds the decision and, after it, an appeal for the same id
      3. GET /content/<id> still shows the original scores and label
      4. GET /content/<id> shows status under_review
    """
    who = f"c5_{tag}_t{n}"
    lines: list[str] = []
    score = 0

    submit = call("POST", "/submit", {"text": scenarios.MY_OWN_WRITING[n], "creator_id": who})
    decided = submit["json"] if isinstance(submit["json"], dict) else {}
    content_id = decided.get("content_id", "missing")
    lines.append(f"POST /submit -> {submit['status']} " + json.dumps(
        {k: decided.get(k) for k in ("content_id", "guess", "confidence", "model_score", "style_score")}))

    appeal = call("POST", "/appeal", {"content_id": content_id,
                                      "reasoning": "I wrote this myself for a history class."})
    lines.append(f"POST /appeal -> {appeal['status']} {json.dumps(appeal['json'])[:160]}")
    if appeal["status"] == 200 and (appeal["json"] or {}).get("status") == "under_review":
        score += 1

    log = call("GET", "/log")
    entries = [e for e in (log["json"] or {}).get("entries", []) if e.get("content_id") == content_id]
    # The decision is the entry with no "event" key; the appeal has event "appeal".
    decision_at = next((i for i, e in enumerate(entries) if "event" not in e), None)
    appeal_at = next((i for i, e in enumerate(entries) if e.get("event") == "appeal"), None)
    for entry in entries:
        lines.append("    audit: " + json.dumps(entry, ensure_ascii=False)[:230])
    if decision_at is not None and appeal_at is not None and appeal_at > decision_at:
        score += 1
    else:
        lines.append("FAIL: the audit log does not hold a decision followed by an appeal")

    content = call("GET", f"/content/{content_id}")
    now = content["json"] if isinstance(content["json"], dict) else {}
    lines.append(f"GET /content/{content_id} -> {content['status']} " + json.dumps(
        {k: now.get(k) for k in ("status", "confidence", "model_score", "style_score")}))
    same = all(now.get(k) == decided.get(k) for k in ("confidence", "model_score", "style_score", "label"))
    if content["status"] == 200 and same and decided:
        score += 1
    else:
        lines.append("FAIL: scores or label differ from the original decision")
    if now.get("status") == "under_review":
        score += 1

    return trial(score, 4, 4, lines)


# ── Running everything and writing it down ───────────────────────────────────

CRITERIA = {
    1: ("Reproducible local run path", "2 of 2 checks (health, submit) per clean start"),
    2: ("Complete structured run logging", "10 of 10 requests"),
    3: ("Bad submission input is rejected and logged", "5 of 5 bodies"),
    4: ("Warm submissions remain responsive", "9 of 10 within 500 ms"),
    5: ("Appeals preserve the original evidence", "4 of 4 checks"),
}


def main():
    parser = argparse.ArgumentParser(description="Run the five capstone criteria, three trials each.")
    parser.add_argument("--label", required=True,
                        help="a name for this run, e.g. before or after; it goes in the file name")
    parser.add_argument("--only", type=int, nargs="+", choices=sorted(CRITERIA),
                        help="run just these criteria, e.g. --only 2 4")
    parser.add_argument("--source", default=str(REPO),
                        help="what criterion 1 clones (default: this folder; use the "
                             "GitHub URL once the capstone commits are pushed)")
    args = parser.parse_args()

    if something_already_listening():
        sys.exit("A copy of the service is already answering on port 5000.\n"
                 "Stop it first: this script starts and stops its own.")

    which = args.only or sorted(CRITERIA)
    tag = uuid.uuid4().hex[:6]      # makes this run's creator_ids unique
    scratch = Path(tempfile.mkdtemp(prefix="pg_capstone_"))   # server output goes here
    results: dict[int, list[dict]] = {}

    for number in which:
        title, target = CRITERIA[number]
        print(f"\nCriterion {number}: {title}")
        results[number] = []

        if number == 1:
            # Each trial is its own clone and its own service.
            for n in range(1, TRIALS + 1):
                outcome = criterion_1(n, tag, scratch, args.source)
                results[number].append(outcome)
                print(f"  trial {n}: {outcome['score']}  {'pass' if outcome['passed'] else 'FAIL'}")
            continue

        # Criteria 2 to 5: one fresh service, three trials back to back.
        run = {2: criterion_2, 3: criterion_3, 4: criterion_4, 5: criterion_5}[number]
        try:
            service = start_main_service(scratch, f"c{number}")
        except Exception as exc:  # noqa: BLE001 — recorded as three failed trials
            results[number] = [{"score": "0/0", "passed": False,
                                "lines": [f"the service did not start: {exc}"]}] * TRIALS
            print(f"  the service did not start: {exc}")
            continue
        try:
            for n in range(1, TRIALS + 1):
                try:
                    outcome = run(n, tag)
                except Exception as exc:  # noqa: BLE001 — a crash in a check is a failed trial
                    outcome = {"score": "error", "passed": False, "lines": [f"the check crashed: {exc!r}"]}
                results[number].append(outcome)
                print(f"  trial {n}: {outcome['score']}  {'pass' if outcome['passed'] else 'FAIL'}")
        finally:
            service.stop()

    write_report(results, args, tag)


def write_report(results: dict[int, list[dict]], args, tag: str):
    """Write the markdown report and the JSON copy, and print the table."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    # Which version of the code was tested. `git rev-parse --short HEAD`
    # prints the short id of the current commit.
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip() or "unknown"
    # A commit id only describes the code if nothing has been edited since.
    # `git status --porcelain -- "*.py"` lists Python files that differ from
    # that commit, one per line, like " M runlog.py". If there are any, the
    # report names them, so it never claims to have tested code it didn't.
    changed = subprocess.run(["git", "status", "--porcelain", "--", "*.py"], cwd=REPO,
                             capture_output=True, text=True).stdout.splitlines()
    if changed:
        # Each line is a two-character status, a space, then the file name.
        commit += "` plus uncommitted changes to `" + ", ".join(line[3:] for line in changed)

    table = ["| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |", "|---|---|---|---|---|---|"]
    for number, trials in results.items():
        title, target = CRITERIA[number]
        verdict = "MET" if all(t["passed"] for t in trials) else "MISSED"
        cells = " | ".join(t["score"] for t in trials)
        table.append(f"| {number}. {title} | {target} | {cells} | {verdict} |")

    out = [
        f"# Capstone run: {args.label}",
        "",
        f"- When: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Code tested: commit `{commit}`",
        f"- Service started with: `{START_COMMAND}`",
        f"- Run tag (appears in every creator_id this run used): `{tag}`",
        f"- Produced by: `python run_capstone.py --label {args.label}`",
        "",
        *table,
        "",
    ]
    for number, trials in results.items():
        title, target = CRITERIA[number]
        out += [f"## Criterion {number}: {title}", "",
                f"Target: {target}, in each of three trials. "
                f"Produced by `run_capstone.py::criterion_{number}`.", ""]
        for n, t in enumerate(trials, start=1):
            out += [f"### Trial {n}: {t['score']} ({'pass' if t['passed'] else 'FAIL'})", "",
                    "```text", *t["lines"], "```", ""]

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base = config.RESULTS_DIR / f"capstone_{stamp}_{args.label}"
    base.with_suffix(".md").write_text("\n".join(out), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps({"label": args.label, "commit": commit, "tag": tag, "results": results},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("\n".join(table))
    print(f"\nSaved to {base.with_suffix('.md')}")


if __name__ == "__main__":
    main()
