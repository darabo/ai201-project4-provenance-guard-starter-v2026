# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## Stretch Features (declared before building)

I declared these on 2026-10-28, before writing any code for them. The commit
that adds this section comes before the commits that build each one.

1. **A third signal: stock-phrase markers.** `markers.py::marker_signal` will
   count how often the text uses phrases common in AI-generated prose ("it is
   important to note", "plays a significant role", "in today's fast-paced
   world") per 100 words, and turn that rate into a 0 to 1 score where higher
   means more likely AI. It measures word choice, which neither gpt2
   predictability nor the sentence-shape signal looks at. How the three
   signals are weighted against each other goes in Signals and Scoring.
2. **`GET /content/<id>`.** Returns one item's current status (`decided` or
   `under_review`), its scores, its label, and any appeals, rebuilt from the
   audit log.
3. **A verified-human path.** A writer asks for a writing prompt
   (`POST /verify/challenge`), writes a short response to it within a time
   limit, and sends it to `POST /verify`. If the response arrives in time, is
   long enough, and does not itself score as high-confidence AI, the writer's
   `creator_id` earns a "verified writer" credential, recorded in the audit
   log. Every later submission from that writer carries
   `"verified_human": true` and a line in the label saying so. The credential
   does not change the score.

---

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. A writing site sends `POST /submit` with JSON
   `{"text": "...", "creator_id": "..."}`.
2. `app.py::submit` checks the input. Missing, empty, too-short or oversized
   `text`, or a missing `creator_id`, gets a 400 with a plain explanation and a
   `rejected` line in the audit log, so bad input never reaches a signal.
3. Signal one, `detector.py::model_signal`, runs gpt2 on this machine and turns
   perplexity (how predictable the text is to a language model) into
   `model_score`.
4. Signal two, `stylometry.py::style_signal`, measures the text's shape
   (sentence-length spread, vocabulary variety, punctuation) and returns
   `style_score`.
5. Signal three, `markers.py::marker_signal`, counts stock AI phrases and
   returns `marker_score`.
6. `scoring.py::combine_signals` turns the three scores into one `confidence`
   between 0 (confidently human) and 1 (confidently AI), and
   `scoring.py::score_to_label` maps that number to a guess and the sentence a
   reader sees.
7. `audit.py::log_decision` writes everything to `logs/audit.jsonl` with status
   `decided`, and the route returns it as JSON. If the writer disagrees,
   `POST /appeal` with the `content_id` moves the item to `under_review` and
   logs their reasoning beside the original decision.

### The contract

**`POST /submit`**

| Direction | Field | Type | Notes |
|---|---|---|---|
| in | `text` | string | Required. Not empty, between the word and character limits in `config.py` |
| in | `creator_id` | string | Required. Who wrote it; appeals and the verified credential hang off it |
| out | `content_id` | string | `c_` plus 12 hex characters. The handle for `/appeal` and `/content/<id>` |
| out | `creator_id` | string | Echoed back |
| out | `guess` | string | `"ai"`, `"human"` or `"unsure"` |
| out | `confidence` | float | The combined score, 0.0 (confidently human) to 1.0 (confidently AI) |
| out | `label` | string | The full sentence a reader sees |
| out | `model_score`, `style_score`, `marker_score` | float | Each signal on its own, 0 to 1, higher means more AI-like |
| out | `verified_human` | bool | Whether this writer holds the verified credential |
| out | `status` | string | `"decided"` |

Bad input returns 400 with `{"error": "bad_request", "message": "..."}`.

**`POST /appeal`**

| Direction | Field | Type | Notes |
|---|---|---|---|
| in | `content_id` | string | Required. Must exist in the audit log |
| in | `reasoning` | string | Required, not empty. The writer's explanation |
| out | `content_id` | string | Echoed back |
| out | `status` | string | `"under_review"` |
| out | `message` | string | A confirmation sentence for the writer |
| out | `appealed_at` | string | UTC timestamp of the appeal |

Missing fields return 400. A `content_id` that was never issued returns 404
with `{"error": "not_found"}`.


---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** How predictable the text is to gpt2, running locally.
`detector.py::perplexity` computes perplexity over the first 400 tokens, and
`detector.py::model_signal` squashes it onto 0 to 1 with a logistic curve:
perplexity 45 scores 0.5, lower perplexity scores higher (more AI-like).

**Why that might differ between human and AI writing:** A language model
writes by picking a likely next word again and again, so its output is text a
model finds easy to predict. People make less likely choices: an odd word, a
specific name, a sentence that turns halfway through.

**What it can't see:** Who wrote the text. It rewards common words in plain
sentences, so a person writing in a second language, a younger writer, or
anyone writing plainly on purpose scores about as machine-like as a machine.
The reverse fails too: AI text pushed toward rare words or odd phrasing scores
as human. It also only reads the first 400 tokens (about 300 words), so
anything after that has no effect.

### Signal two — the style signal

**What it measures:** The shape of the text without reading it:
how much sentence lengths vary, how much of the vocabulary repeats
(type-token ratio), and how much varied punctuation it uses. All three are
combined into one 0 to 1 `style_score` in `stylometry.py::style_signal`.

**Why that might differ between human and AI writing:** Generated prose tends
toward even, mid-length sentences, a safe vocabulary, and little beyond commas
and full stops. Human writing is lumpier: a three-word sentence beside a
forty-word one, a dash, a question, a semicolon.

**What it can't see:** Meaning. Anything that changes the shape without
changing the substance moves it: adding typos, splitting long sentences,
pasting in a quotation, or adding a few dashes. Type-token ratio also falls as
text gets longer, so length alone can push the score.

### Signal three — the stock-phrase signal (stretch)

**What it measures:** How often the text uses phrases common in AI-generated
prose ("it is important to note", "plays a significant role", "in today's
fast-paced"), counted per 100 words in `markers.py::marker_signal` and turned
into a 0 to 1 `marker_score`.

**Why that might differ between human and AI writing:** Chat models reach for
the same transitions and hedges because they are safe, likely choices. Most
people writing about their own life or opinions don't say "it is important to
note".

**What it can't see:** Anything outside its fixed list. One paraphrase pass
removes every marker, and a human trained in corporate or academic writing
uses many of these phrases naturally. The list is English only.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:**

**The numbers:**

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "creator_id": "..."}'
```

```json

```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json

```

---

## How I Used AI

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
