# Running Provenance Guard

Everything about how the starter works.

This is a **web service**. It runs on your machine and you talk to it with
`curl` from another terminal. If you've not built a backend before, that's
assumed — the starter ships one that already answers.

---

## The capstone run path (unit 9)

This section is the run path for the capstone. Everything below it is the
starter's guide from units 7 and 8, kept as it was.

**Path B: local, with logs.** The service runs on one machine, started by one
command, and every request it answers leaves a record in `logs/runs.jsonl`.

### The start command

From the repository folder, with the virtual environment active:

```bash
gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120
```

What each part does:

| Part | Meaning |
|---|---|
| `gunicorn` | A production web server for Python. It replaces Flask's built-in development server, which is what `python app.py` uses |
| `app:app` | "In the file `app.py`, serve the object named `app`" |
| `--bind 127.0.0.1:5000` | Listen on this machine only (`127.0.0.1` is the loopback address), on port 5000 |
| `--workers 1` | One worker process. The rate-limit counts and the loaded model live in that process's memory, so a second worker would keep its own separate counts and load a second copy of gpt2 |
| `--timeout 120` | Give a request up to 120 seconds before the worker is restarted. The default is 30, and the first submission after a start has to load the model, which can take longer than that on a slow disk |

Stop it with Ctrl+C.

### What the environment needs

| Thing | What I ran it on | Notes |
|---|---|---|
| Operating system | macOS 27.2, Apple M5 Pro, 48 GB RAM | `gunicorn` does not run on Windows. There, `python app.py` starts the same service and writes the same run log |
| Python | 3.13.9 | `requirements.txt` supports 3.11, 3.12 and 3.13, and not 3.14 |
| Disk for packages | 947 MB | Size of `.venv` after `pip install`, almost all of it `torch` |
| Model file | `gpt2`, 525 MB | Downloaded once from Hugging Face by `python detector.py` into `~/.cache/huggingface/hub/models--gpt2` |
| Memory while running | about 1,000 MB | Measured with `ps`: the worker holds 39 MB before the first submission and 984 to 1,051 MB once gpt2 is loaded |
| API keys, accounts | none | After the model download, nothing here uses the network |

The dependencies, with the range `requirements.txt` allows and the exact
version installed when I ran it:

| Package | Allowed range | Version I ran |
|---|---|---|
| flask | `>=3.0,<4.0` | 3.1.3 |
| flask-limiter | `>=3.5,<4.0` | 3.12 |
| requests | `>=2.31,<3.0` | 2.34.2 |
| transformers | `>=4.44,<5.0` | 4.57.6 |
| torch | `>=2.2,<3.0` | 2.15.0 |
| gunicorn | `>=21.2,<24.0` | 23.0.0 |
| certifi | `>=2026.10.19` | 2026.10.23 |

### From a clean checkout

```bash
git clone https://github.com/darabo/ai201-project4-provenance-guard-starter-v2026.git
cd ai201-project4-provenance-guard-starter-v2026
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python detector.py
gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120
```

`python detector.py` is the step that downloads the 525 MB model. Skip it and
the service still starts, but the first submission has to do the download.

Then, in a second terminal (activate the virtual environment there too):

```bash
curl http://127.0.0.1:5000/health
```

A running service answers with JSON that starts `{"detector_loaded":false,`.
`detector_loaded` turns `true` after the first submission.

Send one submission and read back its run record:

```bash
curl -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d @samples/clearly_ai.json
```

```bash
python runlog.py --tail 1
```

The first submission after a start is the slow one (about 2 to 3 seconds here)
because it loads gpt2. Its record says `"cold_start": true`. Later ones take
about 40 milliseconds.

### The run record

| File | What it is |
|---|---|
| `logs/runs.jsonl` | One JSON object per line, one line per HTTP request. Written by `runlog.py`. **Committed**, like the audit log |
| `python runlog.py --tail 10` | Print the last ten records |
| `python runlog.py --count` | How many records, split into ok, rejected and error |
| `python measure_cost.py` | Send ten submissions and report the compute time per run |
| `python runlog.py --stages` | Where the time goes inside a scored request |
| `python run_capstone.py --label before` | The five capstone criteria, three trials each. Starts and stops the service itself, so stop your own copy first |
| `python load_test.py` | Send submissions at 2 a second, then 20 a second, and compare |

### What went wrong when I followed this in a fresh clone

I cloned the repository into an empty folder, made a new virtual environment
and followed the steps above. The install and the start worked. Two things
would have stopped a reader on a Mac:

- **Port 5000 answers even when the service is down.** macOS runs AirPlay
  Receiver on port 5000. My first health check went out before `gunicorn` had
  finished starting and came back `403 Forbidden` with the header
  `Server: AirTunes`. That is AirPlay, and it looks like the service refusing
  the request. Wait for the line `Booting worker with pid` before sending
  anything, and treat any reply that is not JSON as "not my service".
- **`localhost` is not the same as `127.0.0.1` here.** `curl
  http://localhost:5000/ping` got the AirPlay 403 while the service was up,
  because `localhost` tried the IPv6 address first and `gunicorn` is bound to
  the IPv4 one. Every command in this section uses `127.0.0.1` for that reason.

One thing this test could not cover: gpt2 was already in my Hugging Face cache
from unit 7, so the clone did not exercise the 525 MB download.

### Why this is not hosted

A free host gives 512 MB of memory. This service needs about 1,000 MB once the
model is loaded (the measurement in the table above), so it would be killed on
its first submission. The starter's own arithmetic for this is in "This
project will not fit a free host" further down.

---

## Before your first class

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python test.py
```

**You're ready when `python test.py` passes.**

You'll see `[WARN] Detector model — not downloaded yet`:

```bash
python detector.py
```

That downloads about 550 MB and scores a sample.

> **No API key for this pair.** Nothing here calls a hosted service. The model
> that reads your text runs on your own laptop.

---

## Your first five minutes

Two terminals. In the first:

```bash
python app.py
```

In the second:

```bash
curl -X POST http://127.0.0.1:5000/ping \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

You should get JSON back. That's the whole idea of a web service — something
sent it data, it sent something back.

> **On Windows, use `curl.exe` and keep it on one line.**
>
> In PowerShell, `curl` is an alias for a different tool and the command above
> fails with `Cannot bind parameter 'Headers'` before it ever reaches your
> service. The `\` line breaks don't work there either. This does:
>
> ```powershell
> curl.exe -X POST http://127.0.0.1:5000/ping -H "Content-Type: application/json" -d '{\"message\": \"hello\"}'
> ```
>
> Every `curl` command in this file and in the brief works the same way: swap
> `curl` for `curl.exe` and put it on one line. Git Bash needs no change.

**Leave `/ping` alone.** It's your control. When something breaks later, check
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself, and that's a help-channel question.

Then try the route you're going to build:

```bash
curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "some writing", "creator_id": "me"}'
```

It returns a `501` saying it isn't built yet. **That's the correct starting
position.**

---

## The routes

| Route | State | What it does |
|---|---|---|
| `POST /ping` | **works** | The example. Don't edit it |
| `GET /health` | **works** | Is the service up, is the model loaded |
| `GET /log` | **works** | The audit log, as JSON |
| `POST /submit` | **you build it** | Milestones 3, 4, 5 |
| `POST /appeal` | **you build it** | Milestone 5 |

---

## Every command

| Command | What it does |
|---|---|
| `python test.py` | Checks your environment |
| `python app.py` | Runs the service |
| `python detector.py` | Downloads the model and scores a sample — **run before class** |
| `python detector.py "some text"` | Score one piece of text from the terminal |
| `python stylometry.py "some text"` | Your style measures, on one piece of text |
| `python run_attacks.py --set <folder>` | The attack set — **unit 8** |
| `python run_attacks.py --flood 15` | Push past your rate limit and print the status codes — **unit 8** |
| `python run_eval.py --label before` | Your five criteria, three trials — **unit 8** |

---

## Which piece goes with which milestone

### Unit 7 — the build

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Trace a submission on paper | Nothing to run |
| 2 | Write your criteria | `criteria.md` — all five are yours |
| 3 | The route, one signal, the log | `app.py::submit`, `detector.py`, `audit.py` |
| 4 | Second signal, combine, score | `stylometry.py`, `scoring.py::combine_signals` |
| 5 | Labels and the appeal path | `scoring.py::score_to_label`, `app.py::appeal` |
| 6 | Write it up | `README.md` |

### Unit 8 — the test

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Rate limiting and the full log | `config.py`, the decorator in `app.py` |
| 2 | Run the attack set | `run_attacks.py` |
| 3 | Run your own criteria | `scenarios.py`, `run_eval.py` |
| 4 | Verdicts and diagnoses | `README.md` |
| 5 | Fix one thing, re-run | `run_attacks.py --label after` |
| 6 | What's still broken | `README.md` |

---

## Building `/submit` in three passes

The ordering is deliberate. It's how you tell a broken route from a broken
signal.

**Milestone 3.** Return a hardcoded response. Confirm `curl` gets it back
**before** you add any logic. Then pull `text` and `creator_id` out. Then call
one signal. Then log it.

**Milestone 4.** Add the second signal. Combine them. Log both scores.

**Milestone 5.** Turn the score into a label.

> Test each signal from a terminal on its own before wiring it in. If you skip
> that you'll spend an hour not knowing whether the route or the signal is
> lying to you.

---

## Turning on rate limiting (unit 8)

Three steps:

1. In `config.py`, set `RATE_LIMITING_ENABLED = True` — or run with
   `AI201_RATE_LIMITS=1`.
2. Choose your numbers there.
3. In `app.py`, uncomment the `@limiter.limit(...)` line above `submit`.

Then push past your limit and watch for `429`:

```bash
python run_attacks.py --flood 15
```

That sends 15 submissions from one `creator_id` and prints the run of status
codes — `200 200 200 ... 429 429` — which is exactly what your README's **Rate
Limiting** section asks you to paste. It also writes `results/flood_<date>.md`.

The attack set can't do this for you. Every attack row submits under its own
`creator_id`, so a full attack run looks like forty-odd different callers and
never trips a limit however long it is.

No `429` at all? Either your limit is above 15 a minute, or rate limiting is
still off. `GET /health` reports which.

Rejections are logged for you. **An attack that shows up only as an absence is
one you'll never find** — a thousand requests that got a `429` and left no
trace look exactly like a quiet afternoon.

---

## Running it somewhere else (unit 9)

Unit 9 asks you to deploy one of your systems. **Read this before you pick
which one** — for this project the answer is already decided, and it isn't the
hosted one.

Flask's built-in server says "development server" on startup because that's
what it is. A real one comes from `gunicorn`, which is in
`requirements.txt` and unused until now:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Two settings do the work, and both read the environment:

| Variable | Default | What it does |
|---|---|---|
| `HOST` | `127.0.0.1` | Loopback — your machine only. A host needs `0.0.0.0`, or nothing outside the box can reach the service and it looks like the app is down |
| `PORT` | `5000` | Most hosts hand you a port in `PORT` and expect you to bind exactly that one |
| `AI201_DEBUG` | `1` | Debug mode. Off automatically whenever `HOST` isn't loopback — an interactive debugger on a public address is a stranger's Python prompt inside your process |

Nothing about your local workflow changes. With no variables set you get
`http://127.0.0.1:5000` and every `curl` above still works.

### This project will not fit a free host

Say it plainly, because the arithmetic is the point:

| What has to be in memory | Roughly |
|---|---|
| `torch` | ~200–800 MB depending on the build |
| the `gpt2` weights | ~550 MB on disk, loaded into RAM to score |
| Flask, gunicorn, your code | the rest |
| **A free tier gives you** | **512 MB** |

That's over budget before a single request arrives — and a free host has no
persistent disk, so the 550 MB download starts again after every idle
spin-down. There is no configuration that fixes this. The model is the size it
is.

**So pair 4 extensions take Path B — local, with logs.** That is the expected
answer for this project, not a fallback and not a failure. Working out that a
system doesn't fit its host *before* you spend an evening watching it get
killed is the skill unit 9 is actually testing. Write the arithmetic above in
your write-up; that's the deliverable.

---

## Where everything lives

| File | What it does |
|---|---|
| `config.py` | Every setting: thresholds, weights, rate limits, the model |
| `app.py` | The service. `/ping` and `/log` work; `/submit` and `/appeal` are yours |
| `detector.py` | Signal one — the local model. Given to you |
| `stylometry.py` | Signal two. **Stubs — you build these** |
| `scoring.py` | Combining and labelling. **Stubs — you build these** |
| `audit.py` | The audit log writer. Given to you |
| `run_attacks.py` | Runs the attack set — **unit 8** |
| `run_eval.py` | Runs your criteria three times — **unit 8** |
| `scenarios.py` | What your test runs. **You fill this in** |
| `criteria.md` | Your five criteria. **You write all five** |
| `logs/audit.jsonl` | Your audit log. **Commit it** |
| `results/` | Attack runs and run logs. **Commit them** |

---

## The two blind spots, up front

Both signals have one, and unit 8's attack set is built out of them. You have
to name them yourself in Milestone 1 — but knowing they exist now saves you
from being surprised.

**Signal one** measures how *predictable* your text is. Predictability isn't
authorship. What it really rewards is common words in short, ordinary
sentences — someone writing in a second language and staying with vocabulary
they're sure of, a younger writer, anyone writing plainly on purpose. Writing
like that scores about as machine-like as machine writing does. (Dense, ornate
prose often goes the other way and reads as human, because rare words are what
a language model fails to predict.) So the writers this signal is most likely
to accuse are the ones with the least room to argue back. That is the false
positive the whole project is about, and it's structural rather than a bug.

**Signal two** cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — typos, broken-up
sentences, a pasted quotation. That is very cheap to do on purpose.

---

## When something goes wrong

| What you see | What it means |
|---|---|
| `501 not_implemented` | Correct at the start — that's the TODO in `app.py` |
| `404` from curl | Is the server running? Is the path exactly what you typed? |
| `Cannot bind parameter 'Headers'` | You're in PowerShell, where `curl` is a different tool. Use `curl.exe`, on one line |
| Request body arrives empty | curl needs `-H "Content-Type: application/json"` |
| `Address already in use` | A server left running from an earlier attempt. Kill it, don't debug it |
| The first submission takes 10+ seconds | Signal one is loading the model into memory. Later ones take a second or two |
| *Every* submission takes 10+ seconds | Something is reloading the model each call. `GET /health` shows `detector_loaded` — if it goes back to `false`, look for a reload in your handler |
| `DetectorUnavailable` | Run `python detector.py` once to download the model |
| `/appeal` seems to do nothing | Does the `content_id` you sent actually exist in the log? A typo there fails silently |
| Every request gets through, no `429` ever | The decorator is uncommented but limiting is still off. Set `RATE_LIMITING_ENABLED` in `config.py` |
| Flask-Limiter warns about storage | Shouldn't happen — `storage_uri` is preconfigured. If you changed it, put it back |
| All three of your labels never appear | Your ranges have a gap. `scoring.label_ranges()` prints them |

If the route won't respond, go back to `/ping`. If that answers, the problem is
in your handler.

---

## A note on committing

At least four new commits in unit 7, four more in unit 8.

`logs/` and `results/` are deliberately **not** in `.gitignore`. Your audit log
is evidence, and the entries you paste into your README are what unit 8 grades.

**Do not delete and recreate this repository.** You submit the same URL both
units.
