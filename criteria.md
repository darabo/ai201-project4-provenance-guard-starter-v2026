# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. My own writing is rarely called AI

Submit the 10 paragraphs I wrote myself (each at least 40 words, stored in
`scenarios.py` under the scenario "my own writing"). In each of three runs, at
most 2 of the 10 come back with the high-confidence AI label (`"guess": "ai"`).

**Why this target:** On a writing site, a wrong accusation damages a real
person's reputation, while a missed piece of AI text costs the site a little.
That cost is one-sided, so I set a limit on accusations against my own writing
instead of a target for how much AI text gets caught.

---

## 2. Clearly-AI and clearly-human text score far apart

In each of three runs, the `confidence` returned for
`samples/clearly_ai.json` is at least 0.30 higher than the `confidence`
returned for `samples/clearly_human.json`.

**Why this target:** 0.30 is the width of my unsure band (0.35 to 0.65 in
`config.py`). If the gap is smaller than that, both samples can sit inside the
unsure band together, which would mean my three signals combined can't tell an
obvious case from its opposite.

---

## 3. All three labels are reachable

In each of three runs, `samples/clearly_ai.json` returns `"guess": "ai"`,
`samples/borderline.json` returns `"guess": "unsure"`, and
`samples/clearly_human.json` returns `"guess": "human"`.

**Why this target:** A label no input can reach is a promise the system can't
keep. The unsure label is the one that protects writers whose work my signals
can't call, so if borderline text jumps straight to "ai", the middle band isn't
doing its job. I require all three runs because a sample that changes label
between runs means a writer could get a different verdict just by resubmitting.

---

## 4. Every appeal is recorded and changes status

Submit 5 texts, then send `POST /appeal` with each returned `content_id` and a
non-empty `reasoning`. All 5 appeals return 200 with `"status":
"under_review"`, and `GET /log` shows, for each of the 5 content_ids, an entry
with `"event": "appeal"`, `"status": "under_review"`, and the reasoning that
was sent. An appeal with the made-up content_id `c_doesnotexist` returns 404
and adds no appeal entry to the log.

**Why this target:** The appeal is the only thing a wrongly accused writer can
do, and my system has no automatic re-check. One lost appeal leaves a false
accusation standing with no record that it was ever challenged, so anything
less than 5 of 5 is a failure.

---

## 5. Bad input is refused cleanly, never crashes

Send these 7 bodies to `POST /submit`: `text` empty (`""`), `text` missing,
`text` as `null`, `text` of 39 words, `text` of 10,001 characters,
`creator_id` missing (with otherwise valid text), and a JSON list instead of an
object. Each one returns status 400 with a JSON body containing `"error"` and a
`"message"` explaining what was wrong, none returns a 500, and each leaves an
entry with `"status": "rejected"` in `GET /log`.

**Why this target:** Below about 40 words the signals don't mean much: gpt2
needs enough tokens for a perplexity reading, and a sentence-length spread
needs at least two sentences. Above 10,000 characters (about 1,700 words) the
text covers any essay or story, while gpt2 reads only the first 400 tokens
anyway, so a giant paste only slows the service. A 500 is what unit 8's attack
script counts as broken, and a refusal that leaves no log entry is an attack I
could never find later.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Capstone criteria (unit 9)

Five criteria for the unit 9 capstone, written before any trial was run. The
five above this heading are the unit 7 criteria and are left as they were.

## 1. Reproducible local run path

For each of 3 independent starts from a fresh checkout (three separate clones,
each into an empty folder with a new virtual environment; gpt2 may come from
the existing Hugging Face cache), a reader can follow only `RUNNING.md` to
create the documented Python environment, install the required dependencies
and model, and start Provenance Guard. Each start must return `200` with
`"ok": true` from `GET /health`, sent after gunicorn prints
`Booting worker with pid`, followed by a `200` response to one valid
`POST /submit` request (the `samples/clearly_ai.json` command in `RUNNING.md`).

**Why this target:** Provenance Guard runs a local GPT-2 detector, so a
documented local-with-logs path is more realistic than a free hosted
deployment. Three clean starts test that the service is reproducible rather
than merely working in my existing development environment.

---

## 2. Complete structured run logging

In each of 3 sessions of 10 requests, every response’s `X-Request-ID` appears
in exactly one record in `logs/runs.jsonl`. Each matching record includes
`timestamp`, `request_id`, `method`, `path`, `input`, `output`, `outcome`, and
`duration_ms`. For successful decisions (a `200` from `POST /submit`), `output`
includes the `content_id`, `guess`, and `confidence`; for rejected requests
(any 4xx response), it includes the HTTP status (`output.status_code`) and
error code (`output.error`).

The 10 requests in a session, sent in this order, with `creator_id`s that have
not been used earlier in that minute:

1. `GET /health`
2. `POST /submit` with paragraph 1 of `scenarios.MY_OWN_WRITING`
3. `POST /submit` with paragraph 2, from a second `creator_id`
4. `POST /submit` with paragraph 3, from a third `creator_id`
5. `POST /submit` with paragraph 4, from a fourth `creator_id`
6. `POST /submit` with `"text": ""`
7. `POST /submit` with the JSON array `[1, 2, 3]` as the body
8. `POST /appeal` with the `content_id` returned by request 2 and a non-empty
   `reasoning`
9. `POST /appeal` with the `content_id` `c_doesnotexist`
10. `GET /submitt` (a mistyped URL)

**Why this target:** Provenance Guard makes an attribution decision that a
writer may need to challenge. Complete records make it possible to investigate
both classifications and rejected requests afterward instead of treating
missing evidence as a quiet system.

---

## 3. Bad submission input is rejected and logged

In each of 3 trials, all 5 deliberately invalid `POST /submit` bodies—missing
`text`, empty `text` (`""`), whitespace-only `text` (three spaces), non-string
`text` (the number `12345`), and a JSON array instead of an object—return `400`
with a JSON `error` field and never return a `5xx`. Each rejection produces one
run-log record with `outcome: "rejected"`, `output.status_code: 400`, an error
code, and `duration_ms`. Every body except the array carries a `creator_id`
that has not been used before in that trial's minute (for example `c3_trial1`),
and the three trials run back to back with no pause between them.

**Why this target:** The project specifically accepts writer-submitted text,
and malformed input must not crash the service or disappear from the record.
These five cases cover absent, unusable, and incorrectly shaped request data.

---

## 4. Warm submissions remain responsive and measurable

After one valid warm-up submission has loaded the detector and `GET /health`
reports `"detector_loaded": true`, at least 9 of 10 valid `POST /submit`
requests (the ten paragraphs in `scenarios.MY_OWN_WRITING`, 42 to 86 words
each, each sent with a different `creator_id`) return `200` within 500 ms in
each of 3 trials. The time is the `duration_ms` in that request's record in
`logs/runs.jsonl`. Each successful response includes `content_id`,
`model_score`, `style_score`, `confidence`, and `label`.

**Why this target:** Initial model loading is expected to be slow, but a warmed
local detector should handle normal submissions promptly. 500 ms is about ten
times the 29 to 53 ms warm runs in my cost measurement and a quarter of the
2,031 ms cold start, so a request that reloads the model cannot pass. The
returned component scores are necessary to explain a questionable
classification rather than presenting an unexplained label.

---

## 5. Appeals preserve the original evidence

In each of 3 trials, after one valid submission, an appeal using its returned
`content_id` and non-empty reasoning returns `200` with
`"status": "under_review"`. The audit log (read from `GET /log`) contains both
the original decision and a later appeal record with the same `content_id`, and
`GET /content/<content_id>` retains the original scores and label while showing
`"status": "under_review"`.

**Why this target:** A false AI accusation is costly to a writer. An appeal
must be traceable without overwriting the initial decision, so a reviewer can
see both what the system concluded and why the writer challenged it.
