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

Two stretch routes build on this path: `GET /content/<id>` reports an item's
current status at any time, and a writer who passes the verified-writer step
gets `"verified_human": true` and a badge line beside the label on every later
submission (details under Stretch Features: What I Built).

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
| out | `verified_badge` | string or null | The badge line shown beside the label for a verified writer; `null` otherwise |
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

**The rule:** Average the two required signals equally to get a base score.
Then let the stock-phrase signal push that score up, never down, because
finding stock phrases is evidence of AI while finding none proves nothing (a
paraphrase removes them all). Finally, unless at least two of the three
signals lean AI on their own, cap the score just under the AI line, so no
single signal can produce a high-confidence AI label. That guard exists for
the false positive: signal one alone scores plain human writing as AI-like.

**The numbers:**

1. `base = 0.5 × model_score + 0.5 × style_score`
2. `final = base + 0.3 × marker_score × (1 − base)`, so a text at base 0.50
   full of stock phrases rises to at most 0.65, and the score can never pass
   1.0.
3. If fewer than 2 of the 3 signals are at or above 0.5, `final` is capped at
   0.64 (0.01 under the AI threshold of 0.65).

All of these live in `config.py` (`WEIGHT_MODEL_SIGNAL`, `WEIGHT_STYLE_SIGNAL`,
`MARKER_BOOST`, `AGREEMENT_LEVEL`, `MIN_AGREEING`).

**How the three signals are weighted against each other (stretch note):** The
two required signals carry equal weight because each has a blind spot I can
name and I have no evidence yet that one is more reliable. The stock-phrase
signal gets no weight in the base at all. It acts only as a one-way boost
worth at most 30% of the remaining distance to 1.0, because its absence is
weak evidence of anything. It does count as one of the three votes in the
agreement guard.

Inside signal two, the three measures are blended 0.4 sentence-length spread,
0.4 expressive punctuation, 0.2 type-token ratio, each first mapped onto 0 to 1
between an AI-typical and a human-typical anchor (`stylometry.py`, constants
`SPREAD_ANCHORS`, `PUNCT_ANCHORS`, `TTR_ANCHORS`, `STYLE_WEIGHTS`).
Type-token ratio gets the least weight because its direction surprised me: on
my samples the AI text had the more varied vocabulary (0.94 against 0.83 for
the human sample), so I flipped it to count high variety as AI-typical, and
three samples is thin evidence for that.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**All three signals on the calibration samples:**

| Sample | model | style | marker | combined |
|---|---|---|---|---|
| `samples/clearly_ai.json` | 0.754 | 0.914 | 0.994 | 0.884 |
| `samples/borderline.json` (lightly edited AI) | 0.349 | 0.539 | 0.000 | 0.444 |
| `samples/clearly_human.json` | 0.445 | 0.104 | 0.000 | 0.275 |

**A case where my two signals split, and what my rule does with it:**
`samples/borderline.json` is the AI paragraph rewritten by hand: stock
phrases removed, a dash and a semicolon added, British spellings. gpt2 reads
it as fairly human (0.349) while the style signal puts it in the middle
(0.539), and the marker signal finds nothing (0.0). A plain three-way average
that counted the marker zero as evidence would have dropped it to about 0.30,
a confident "human". My rule ignores the marker zero, averages the two
required signals to 0.444, and labels it unsure, which is what it is.

The second split is in the other direction: on `clearly_human.json` gpt2 gives
0.445, more AI-like than the edited AI text, because the paragraph's everyday
words are easy to predict. The style signal (0.104) reads the uneven sentences
and dashes correctly, and the average lands at 0.275, human.

**A false positive on my own writing (kept as-is for unit 8):** The fourth
calibration input was plain writing of my own. I wrote it as my answer to the
verified-writer prompt "Describe the route you take most often, as if giving
directions to a friend", and my system labeled it high-confidence AI:

> Go straight until you hit 50th St, turn right, go until you hit 8th Ave,
> then turn right. Go about three blocks until you reach the Apple Store, and
> take a left at the traffic light. You will walk by a New York Public Library
> branch, go past it until you hit the Burger King and take a right. Walk down
> until you hit the Starbucks and take a left. The building will be right in
> front of you. It's a white building with a black awning.

| | my directions | `clearly_ai.json` |
|---|---|---|
| perplexity | 16.3 | 22.3 |
| model | 0.835 | 0.754 |
| style | 0.723 | 0.914 |
| marker | 0.000 | 0.994 |
| combined | 0.779 (AI) | 0.884 (AI) |

gpt2 found my directions more predictable than the AI sample, because
directions are made of stock moves ("go until you hit", "take a left"). The
style signal agreed: no dashes, semicolons or quotes (punctuation density 0.0,
the most AI-typical value) and evenly sized steps (spread 0.42). Two of three
signals were over 0.5, so my agreement guard let the AI label through, and the
marker signal, which correctly found nothing, can only push scores up.

This one is personal. People often tell me my writing looks like AI, and my
own detector agreed with them on the first try. It is the false positive from
Milestone 1 in practice: a real writer, writing plainly, labeled AI by a
system that measures predictability rather than authorship.

I'm deliberately not retuning to fix it now. Widening the unsure band (an AI
threshold around 0.80 would move this text to unsure and still label
`clearly_ai.json` AI at 0.884) is the obvious improvement, and I'm saving it
for unit 8, where it can be measured before and after against my criteria. I
did remove the directions prompt from the verified-writer path
(`credentials.py::PROMPTS`), because a prompt that invites formulaic writing
sets honest writers up to fail.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 to 0.35 (0.35 itself is human) | We think this was written by a person. Our check looks at writing patterns, so it can be wrong, but nothing here suggested an AI tool. |
| unsure | above 0.35 and below 0.65 | We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it. |
| high-confidence AI | 0.65 to 1.00 (0.65 itself is AI) | This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it. |

The text lives in `scoring.py` (`LABEL_TEXT`), chosen by
`scoring.py::score_to_label`. Each label was reached with a real submission:
`samples/clearly_human.json` scored 0.2745 (human), `samples/borderline.json`
0.4441 (unsure), and `samples/clearly_ai.json` 0.8838 (AI).

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->

Most text that lands in the unsure band is plain or edited writing, and gpt2
is known to score plain human writing as AI-like, so the person reading this
label most likely wrote the piece. The label must not read as a soft
accusation, so it says the system made no call at all instead of hinting
which way it leans.


---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

`samples/clearly_ai.json` holds `{"text": "The importance of effective time
management cannot be overstated in today's fast-paced work environment. ...",
"creator_id": "demo_instructor"}`.

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d @samples/clearly_ai.json
```

```json
{
  "confidence": 0.8838,
  "content_id": "c_47219dc63d36",
  "creator_id": "demo_instructor",
  "guess": "ai",
  "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
  "marker_score": 0.9943,
  "model_score": 0.7544,
  "status": "decided",
  "style_score": 0.9145,
  "verified_badge": null,
  "verified_human": false
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "c_47219dc63d36", "reasoning": "I wrote this for my team'\''s newsletter. I always write in this formal style at work."}'
```

```json
{
  "appealed_at": "2026-10-29T02:15:12+00:00",
  "content_id": "c_47219dc63d36",
  "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
  "status": "under_review"
}
```

**What the log shows afterwards**

The original decision stays exactly as it was; the appeal is a new line after
it with status `under_review`.

```bash
$ curl "http://127.0.0.1:5000/log?limit=2"
```

```json
{
  "count": 2,
  "entries": [
    {
      "combined_score": 0.8838,
      "content_id": "c_47219dc63d36",
      "creator_id": "demo_instructor",
      "guess": "ai",
      "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
      "marker_score": 0.9943,
      "model_score": 0.7544,
      "status": "decided",
      "style_score": 0.9145,
      "timestamp": "2026-10-29T02:15:12+00:00",
      "verified_human": false
    },
    {
      "content_id": "c_47219dc63d36",
      "creator_id": "demo_instructor",
      "event": "appeal",
      "reasoning": "I wrote this for my team's newsletter. I always write in this formal style at work.",
      "status": "under_review",
      "timestamp": "2026-10-29T02:15:12+00:00"
    }
  ]
}
```

**Bad input is refused, not crashed on** (criterion 5). A 39-word text:

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "word word word ... (39 words)", "creator_id": "eval_bad_short"}'
```

```json
{
  "error": "bad_request",
  "message": "The text has 39 words; at least 40 are needed to judge it fairly."
}
```

The status is 400, and the log gains an entry with `"event": "rejected"`,
`"reason": "text_too_short"`.

---

## How I Used AI

**Moment 1: writing my acceptance criteria**

- *What I asked for:* I asked Claude (in Claude Code) to help me write my five
  criteria, because I didn't know where to start.
- *What came back:* It wouldn't write them outright, since the brief says a
  criterion I didn't write is one I can't defend. Instead it gave me a
  skeleton sentence for each area and then multiple-choice questions for every
  number and reason. It also flagged a tension in my false-positive criterion:
  my reason says a wrong accusation is the expensive mistake, but my target
  allows 2 of my 10 paragraphs to be called AI.
- *What I changed:* I chose every target myself (2 of 10, a 0.30 spread, 3 of 3
  runs, 5 of 5 appeals, 40 words to 10,000 characters). I kept 2 of 10 after
  the warning.

**Moment 2: the verified-writer prompts**

- *What I asked for:* I had Claude build the verified-writer path, including
  the list of writing prompts a writer answers to earn the badge.
- *What came back:* A prompt list with the claim that prompts asking for
  concrete personal details would read as human. When I answered two of them
  honestly in my own words, my system refused me both times as AI (combined
  0.779 and 0.787). The directions prompt in particular invites formulaic
  phrasing that gpt2 predicts easily.
- *What I changed:* I removed the directions prompt. I decided not to retune
  the thresholds to make my own writing pass, and to record both refusals and
  the flaw they expose (the badge's gate repeats the detector's false
  positive) for unit 8 instead. The verified-writer demo below uses the
  course's human sample, labeled as such.

---

## Stretch Features: What I Built

All three were declared at the top of this README before any of their code
existed (commit `9d55dc7`).

### Third signal: stock phrases

Built as declared in `markers.py::marker_signal`; the weighting note is in
Signals and Scoring under "How the three signals are weighted against each
other". What it changed: `/submit` now returns and logs `marker_score`, and
`scoring.py::combine_signals` takes it as a third argument (a one-way boost
plus a vote in the agreement guard).

### `GET /content/<id>`

Built in `app.py::get_content`. It reads every audit-log line for the id and
reports the newest status, so an appealed item shows `under_review`. What it
changed: nothing about existing routes; it only reads the log. Using the item
from the Sample Run above, after its appeal:

```bash
$ curl http://127.0.0.1:5000/content/c_47219dc63d36
```

```json
{
  "appeals": [
    {
      "appealed_at": "2026-10-29T02:15:12+00:00",
      "reasoning": "I wrote this for my team's newsletter. I always write in this formal style at work."
    }
  ],
  "confidence": 0.8838,
  "content_id": "c_47219dc63d36",
  "creator_id": "demo_instructor",
  "guess": "ai",
  "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
  "marker_score": 0.9943,
  "model_score": 0.7544,
  "status": "under_review",
  "style_score": 0.9145,
  "submitted_at": "2026-10-29T02:15:12+00:00",
  "verified_human": false
}
```

An id that was never issued returns 404 with `{"error": "not_found", ...}`.

### Verified-writer path

**The extra step:** a writer calls `POST /verify/challenge` and gets a personal
prompt and a `challenge_id`. They then have 10 minutes to send at least 60
words to `POST /verify`. It's refused if the reply comes back in under 45
seconds (faster than anyone types 60 words), comes from a different
`creator_id`, reuses a challenge, or scores as high-confidence AI through the
same three signals as `/submit`. Passing writes a `"verified"` entry to the
audit log. From then on, every submission by that `creator_id` carries
`"verified_human": true` and a `verified_badge` line beside its label. The
badge never changes the score. The logic lives in `credentials.py`; the routes
are `app.py::verify_challenge` and `app.py::verify`.

**What it changed:** the three-signal scoring moved out of `/submit` into
`app.py::_score_text` so `/verify` judges text exactly the same way;
`audit.py` gained `log_event` for the challenge and credential entries;
`/submit` responses gained `verified_human` and `verified_badge`, and decision
log entries gained `verified_human`.

**The credential appearing on an item.** This run uses the course's human
sample (`samples/clearly_human.json`) as the writer's answer, under the
`creator_id` `test_verify`. It drew the directions prompt, which I later
removed, and the sample doesn't answer it: the gate checks timing, length and
score, not whether the text is on topic.

```bash
$ curl -X POST http://127.0.0.1:5000/verify/challenge \
  -H "Content-Type: application/json" \
  -d '{"creator_id": "test_verify"}'
```

```json
{
  "challenge_id": "v_6248f720816d",
  "expires_at": "2026-10-29T02:04:45+00:00",
  "instructions": "Write at least 60 words responding to the prompt, in your own words, then send them to POST /verify with this challenge_id before it expires.",
  "issued_at": "2026-10-29T01:54:45+00:00",
  "min_words": 60,
  "prompt": "Describe the route you take most often, as if giving directions to a friend."
}
```

Sending the answer immediately is refused with a 400 for arriving faster than
anyone could type 60 words. Sending it again 46 seconds after the challenge:

```bash
$ curl -X POST http://127.0.0.1:5000/verify \
  -H "Content-Type: application/json" \
  -d '{"creator_id": "test_verify", "challenge_id": "v_6248f720816d", "text": "I didn'\''t sleep. Not properly, anyway ... (full text of samples/clearly_human.json)"}'
```

```json
{
  "badge": "Verified writer: completed a live writing check on 29 October 2026.",
  "creator_id": "test_verify",
  "message": "You're verified. Your future submissions will show this badge beside their label.",
  "verified": true,
  "verified_at": "2026-10-29T01:55:33+00:00"
}
```

The audit log entry for the credential:

```json
{"timestamp": "2026-10-29T01:55:33+00:00", "creator_id": "test_verify", "event": "verified", "status": "verified", "challenge_id": "v_6248f720816d", "guess": "human", "combined_score": 0.2745, "model_score": 0.4445, "style_score": 0.1044, "marker_score": 0.0}
```

Then a submission from the same writer (`samples/borderline.json`'s text with
`creator_id` `test_verify`) shows the badge on the item:

```json
{
  "confidence": 0.4441,
  "content_id": "c_d11b5333aa47",
  "creator_id": "test_verify",
  "guess": "unsure",
  "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
  "marker_score": 0.0,
  "model_score": 0.3489,
  "status": "decided",
  "style_score": 0.5393,
  "verified_badge": "Verified writer: completed a live writing check on 29 October 2026.",
  "verified_human": true
}
```

**What happened when I tried it with my own writing:** refused, twice. My
directions answer scored 0.779 and my answer to "Write about something you
changed your mind about in the last year" scored 0.787, both
high-confidence AI, both for the reasons in Signals and Scoring (predictable
phrasing to gpt2, even sentences and no expressive punctuation to the style
signal). Both refusals are in `logs/audit.jsonl` under `creator_id` `dara`
with `"reason": "verify_scored_ai"`.

That exposes a flaw in my own design: the gate that grants the "verified
human" badge uses the same detector, so the writers most likely to be
wrongly accused are the ones it locks out. A fairer version would send an
AI-scored answer to a person for review instead of refusing it. I'm leaving
it as built for unit 8, where I can measure the false positive and fix it.

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
