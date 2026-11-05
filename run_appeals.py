#!/usr/bin/env python3
"""
Criterion 4, three trials: does every appeal get recorded and change status?

    python app.py                              # in one terminal
    python run_appeals.py --label before       # in another

Why this exists: run_eval.py only sends bodies to /submit, and an appeal
needs a real content_id from a submission first. scenarios.py says so, and
says to test it by hand or extend the tooling. This script is that extension.
It's a test tool, not part of the service, so it doesn't count as a change to
the system being measured.

Each trial does exactly what criterion 4 in criteria.md says:
  1. Submit 5 texts (the first five of my own paragraphs in scenarios.py),
     each under its own creator_id so the 5-per-minute limit isn't the thing
     being tested.
  2. Appeal each returned content_id with a non-empty reasoning.
  3. Read GET /log and check, for each content_id, that an entry exists with
     "event": "appeal", "status": "under_review" and the reasoning sent.
  4. Appeal the made-up id c_doesnotexist and check it returns 404 and that
     no appeal entry for it appears in the log.

The full JSON of every response goes to results/appeals_<date>_<label>.md.
"""

import argparse
import datetime as dt
import json

import requests

import config
import scenarios

FAKE_ID = "c_doesnotexist"


def appeal_entries(url: str, content_id: str) -> list[dict]:
    """Every appeal line in the audit log for one content_id."""
    entries = requests.get(f"{url}/log", timeout=30).json()["entries"]
    return [e for e in entries
            if e.get("content_id") == content_id and e.get("event") == "appeal"]


def run_trial(url: str, trial: int) -> dict:
    """One full pass of criterion 4. Returns everything needed for the report."""
    appeals = []
    for i, text in enumerate(scenarios.MY_OWN_WRITING[:5], 1):
        submit = requests.post(f"{url}/submit", timeout=90,
                               json={"text": text, "creator_id": f"appeal_check_{i}"})
        content_id = submit.json().get("content_id")
        reasoning = f"Trial {trial}, appeal {i}: I wrote this paragraph myself."
        appeal = requests.post(f"{url}/appeal", timeout=30,
                               json={"content_id": content_id, "reasoning": reasoning})
        logged = appeal_entries(url, content_id)
        appeals.append({
            "submit_status": submit.status_code,
            "content_id": content_id,
            "appeal_status": appeal.status_code,
            "appeal_response": appeal.json(),
            # Passes only if the log line carries the right status AND the
            # exact reasoning this trial sent.
            "log_has_appeal": any(e.get("status") == "under_review"
                                  and e.get("reasoning") == reasoning for e in logged),
        })

    before = len(appeal_entries(url, FAKE_ID))
    fake = requests.post(f"{url}/appeal", timeout=30,
                         json={"content_id": FAKE_ID, "reasoning": "This id was never issued."})
    after = len(appeal_entries(url, FAKE_ID))

    passed = sum(1 for a in appeals
                 if a["appeal_status"] == 200
                 and a["appeal_response"].get("status") == "under_review"
                 and a["log_has_appeal"])
    return {
        "appeals": appeals,
        "passed": passed,
        "fake_id": {"status": fake.status_code, "response": fake.json(),
                    "appeal_entries_added": after - before},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--url", default=f"http://{config.HOST}:{config.PORT}")
    args = parser.parse_args()

    trials = []
    for trial in range(1, args.trials + 1):
        result = run_trial(args.url, trial)
        trials.append(result)
        fake = result["fake_id"]
        print(f"trial {trial}: {result['passed']}/5 appeals recorded; "
              f"fake id -> {fake['status']}, appeal entries added: {fake['appeal_entries_added']}")

    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"appeals_{stamp}{label}.md"
    lines = [f"# Criterion 4: appeals{f' ({args.label})' if args.label else ''}", "",
             "- Produced by: `run_appeals.py::main`",
             f"- {args.trials} trials · {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    for n, result in enumerate(trials, 1):
        lines += [f"## Trial {n}: {result['passed']}/5 recorded, fake id "
                  f"{result['fake_id']['status']}", "", "```json",
                  json.dumps(result, indent=2, ensure_ascii=False), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
