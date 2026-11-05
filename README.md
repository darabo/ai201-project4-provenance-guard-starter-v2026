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

| Direction | Field                                        | Type           | Notes                                                                         |
| --------- | -------------------------------------------- | -------------- | ----------------------------------------------------------------------------- |
| in        | `text`                                       | string         | Required. Not empty, between the word and character limits in `config.py`     |
| in        | `creator_id`                                 | string         | Required. Who wrote it; appeals and the verified credential hang off it       |
| out       | `content_id`                                 | string         | `c_` plus 12 hex characters. The handle for `/appeal` and `/content/<id>`     |
| out       | `creator_id`                                 | string         | Echoed back                                                                   |
| out       | `guess`                                      | string         | `"ai"`, `"human"` or `"unsure"`                                               |
| out       | `confidence`                                 | float          | The combined score, 0.0 (confidently human) to 1.0 (confidently AI)           |
| out       | `label`                                      | string         | The full sentence a reader sees                                               |
| out       | `model_score`, `style_score`, `marker_score` | float          | Each signal on its own, 0 to 1, higher means more AI-like                     |
| out       | `verified_human`                             | bool           | Whether this writer holds the verified credential                             |
| out       | `verified_badge`                             | string or null | The badge line shown beside the label for a verified writer; `null` otherwise |
| out       | `status`                                     | string         | `"decided"`                                                                   |

Bad input returns 400 with `{"error": "bad_request", "message": "..."}`.

**`POST /appeal`**

| Direction | Field         | Type   | Notes                                         |
| --------- | ------------- | ------ | --------------------------------------------- |
| in        | `content_id`  | string | Required. Must exist in the audit log         |
| in        | `reasoning`   | string | Required, not empty. The writer's explanation |
| out       | `content_id`  | string | Echoed back                                   |
| out       | `status`      | string | `"under_review"`                              |
| out       | `message`     | string | A confirmation sentence for the writer        |
| out       | `appealed_at` | string | UTC timestamp of the appeal                   |

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

| Sample                                        | model | style | marker | combined |
| --------------------------------------------- | ----- | ----- | ------ | -------- |
| `samples/clearly_ai.json`                     | 0.754 | 0.914 | 0.994  | 0.884    |
| `samples/borderline.json` (lightly edited AI) | 0.349 | 0.539 | 0.000  | 0.444    |
| `samples/clearly_human.json`                  | 0.445 | 0.104 | 0.000  | 0.275    |

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

|            | my directions | `clearly_ai.json` |
| ---------- | ------------- | ----------------- |
| perplexity | 16.3          | 22.3              |
| model      | 0.835         | 0.754             |
| style      | 0.723         | 0.914             |
| marker     | 0.000         | 0.994             |
| combined   | 0.779 (AI)    | 0.884 (AI)        |

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

| Label                 | Score range                         | The exact text a reader sees                                                                                                                     |
| --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| high-confidence human | 0.00 to 0.35 (0.35 itself is human) | We think this was written by a person. Our check looks at writing patterns, so it can be wrong, but nothing here suggested an AI tool.           |
| unsure                | above 0.35 and below 0.65           | We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.                                |
| high-confidence AI    | 0.65 to 1.00 (0.65 itself is AI)    | This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it. |

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

- _What I asked for:_ I asked Claude (in Claude Code) to help me write my five
  criteria, because I didn't know where to start.
- _What came back:_ It wouldn't write them outright, since the brief says a
  criterion I didn't write is one I can't defend. Instead it gave me a
  skeleton sentence for each area and then multiple-choice questions for every
  number and reason. It also flagged a tension in my false-positive criterion:
  my reason says a wrong accusation is the expensive mistake, but my target
  allows 2 of my 10 paragraphs to be called AI.
- _What I changed:_ I chose every target myself (2 of 10, a 0.30 spread, 3 of 3
  runs, 5 of 5 appeals, 40 words to 10,000 characters). I kept 2 of 10 after
  the warning. I kept it because I expect gpt2 to misjudge some plain writing no matter what.

**Moment 2: the verified-writer prompts**

- _What I asked for:_ I had Claude build the verified-writer path, including
  the list of writing prompts a writer answers to earn the badge.
- _What came back:_ A prompt list with the claim that prompts asking for
  concrete personal details would read as human. When I answered two of them
  honestly in my own words, my system refused me both times as AI (combined
  0.779 and 0.787). The directions prompt in particular invites formulaic
  phrasing that gpt2 predicts easily.
- _What I changed:_ I removed the directions prompt. I decided not to retune
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
{
  "timestamp": "2026-10-29T01:55:33+00:00",
  "creator_id": "test_verify",
  "event": "verified",
  "status": "verified",
  "challenge_id": "v_6248f720816d",
  "guess": "human",
  "combined_score": 0.2745,
  "model_score": 0.4445,
  "style_score": 0.1044,
  "marker_score": 0.0
}
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

## Unit 8 Stretch Features (declared before building)

I declared these on 2026-11-04, before turning on the rate limiter, running
the attack set, or writing any of the code or attacks below.

1. **Per-creator limits.** `/submit` is limited per `creator_id`
   (5 per minute, 50 per day), falling back to the caller's address only when
   a request has no usable `creator_id`. I'll show two creators sending from
   the same address getting separate limits, and write what this catches that
   per-address limiting misses and what it costs.
2. **A second measured improvement.** After the first improvement and its
   "after" run, I'll make a second change named by my diagnosis, and measure
   it the same way: a third attack run and a third run log in the same
   format, with a statement of whether it helped.
3. **Three attacks on another team's system.** I'll write three attacks
   against a classmate's Provenance Guard service and report what each one
   did, naming the system attacked.

---

## Rate Limiting

**My limits:** 5 per minute, 50 per day, on `POST /submit` only
(`config.py`: `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_PER_DAY`; the decorator
above `app.py::submit`).

**Why those numbers and not others:**

<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

A real writer submits their own work a few times an hour, so 5 a minute never
gets in their way, while a script probing where my thresholds sit gets only 5
tries a minute. 50 a day is far more than anyone posting their own writing
needs, and too few probes for one `creator_id` to map where the 0.35 and 0.65
lines are. Ten a minute (the starter's number) would double a script's probing
speed without helping any real writer.

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

A `creator_id`. A request with no usable `creator_id` (missing, empty, or a
body that isn't a JSON object) counts against the caller's address instead
(`app.py::rate_limit_key`). Requests my route refuses with a 400 still count:
the limiter runs before the route.

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

The course's flood test, `python run_attacks.py --flood 15`
(`results/flood_2026-11-04_2021.md`):

```
400 400 400 400 400 429 429 429 429 429 429 429 429 429 429
```

The first five are 400s, not 200s, because the flood script's text is 27
words long and my route refuses anything under 40 words (criterion 5). The
limiter still counted them, so requests 6 to 15 got 429. To show the limit
with accepted requests, I sent the same 15-request burst with a valid 94-word
text (`samples/clearly_human.json`) as `creator_id` `flood_valid_text`:

```
200 200 200 200 200 429 429 429 429 429 429 429 429 429 429
```

Each 429 left a rejection in the audit log:

```json
{
  "timestamp": "2026-11-05T01:21:36+00:00",
  "creator_id": "flood_valid_text",
  "event": "rejected",
  "status": "rejected",
  "reason": "rate_limited",
  "limit": "5 per 1 minute"
}
```

### Per-creator limits (stretch)

The limit is keyed to the `creator_id` rather than the address. The key
function, `app.py::rate_limit_key`, came with the starter; my part was choosing
it on purpose, setting the numbers, and testing what it does.

**What it catches that per-address limiting misses:** one creator flooding from
many addresses (different networks, a phone and a laptop) still hits the same
5-a-minute bucket. And it doesn't punish people who share an address. Right
after `flood_valid_text` was cut off, a second writer on the same machine got
through:

```
flood_valid_text             -> 429 rate_limited
second_writer_same_address   -> 200 human
```

Per address, a whole household, office, or school network behind one address
would share 5 submissions a minute.

**What it costs:** `creator_id` is whatever the caller types, so a script
can invent a new one for every request. Eight requests from one address in
the same minute, each with a new `creator_id`:

```
200 200 200 200 200 200 200 200
```

None were limited. Per-creator limiting only stops honest callers and lazy
scripts. A real deployment would tie `creator_id` to a logged-in account, or
keep a looser per-address limit as a backstop.

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->

`python run_attacks.py --set attack_set --label before`, all 56 attacks, run
once with nothing changed beforehand. Raw output:
`results/attack_run_2026-11-04_2042_before.md`; the audit log for the run:
`results/audit_extract_before.json`.

How I marked them: an **evasion** attack (AI text) is BROKE if it escaped the
AI label. A **false_positive** attack (real human writing) is BROKE if it got
the AI label. A **prompt_injection** attack is BROKE if the result moved the
way the attack wanted. A **malformed** or **flood** attack is BROKE if it
crashed the service (any 5xx) or got through unlimited. Nothing returned a
5xx.

| ID | Family | Targeting | Status | Guess | Score | Verdict | Note |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | ai | 0.686 | HELD | typos raised perplexity (model 0.16) but style 1.00 and markers 0.83 kept it AI, barely |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.578 | **BROKE** | AI text; one-word "Really." sentences and spaced dashes dropped style to 0.32, landing unsure |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | ai | 0.727 | HELD |  |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | ai | 0.858 | HELD |  |
| EV05 | evasion | both signals: heavy human editing pass | 200 | unsure | 0.435 | **BROKE** | AI text after a heavy human edit: no markers, model 0.32, landing unsure |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | ai | 0.672 | HELD | 0.672, just over the 0.65 line |
| EV07 | evasion | signal two: padding with punctuation | 200 | ai | 0.670 | HELD | 0.670, just over the 0.65 line |
| EV08 | evasion | signal one: text below the token window | 400 | — | — | HELD | refused at 10 words (under the 40-word minimum); never scored |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | ai | 0.847 | HELD |  |
| EV10 | evasion | signal two: repeated stanza structure | 200 | ai | 0.900 | HELD |  |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | ai | 0.676 | **BROKE** | real human writing labeled AI |
| FP02 | false_positive | human writing in a formal register | 200 | ai | 0.769 | **BROKE** | real human writing labeled AI |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | ai | 0.826 | **BROKE** | real human writing labeled AI |
| FP04 | false_positive | a student essay written to a rubric | 200 | ai | 0.855 | **BROKE** | real human writing labeled AI (worst outcome) |
| FP05 | false_positive | technical documentation written by a person | 200 | ai | 0.800 | **BROKE** | real human writing labeled AI |
| FP06 | false_positive | a person imitating a formal template | 200 | ai | 0.768 | **BROKE** | real human writing labeled AI |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | ai | 0.697 | **BROKE** | real human writing labeled AI |
| FP08 | false_positive | very short genuine human submission | 400 | — | — | HELD | 8 words, refused with a 400: not accused, but turned away |
| PI01 | prompt_injection | instruction to ignore the check | 200 | ai | 0.708 | HELD | instruction did nothing; labeled AI |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | unsure | 0.566 | **BROKE** | instruction did nothing, but its odd tokens fooled gpt2 (model 0.20); AI text landed unsure |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | ai | 0.694 | HELD | instruction did nothing; labeled AI |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | unsure | 0.500 | HELD | label text is fixed in scoring.py; nothing from the input is echoed back |
| PI05 | prompt_injection | attempt to inject into the audit log | 400 | — | — | HELD | refused at 28 words; the log is written with json.dumps, so no fields were injected |
| PI06 | prompt_injection | instruction plus real human text | 200 | ai | 0.651 | HELD | instruction did nothing; the human text it carries was labeled AI (0.651), same mechanism as FP01 |
| MF01 | malformed | text is only whitespace | 400 | — | — | HELD | refused with a 400 |
| MF02 | malformed | text is a single character | 400 | — | — | HELD | refused with a 400 |
| MF03 | malformed | text is control characters | 400 | — | — | HELD | refused with a 400 |
| MF04 | malformed | text is only punctuation | 400 | — | — | HELD | refused with a 400 |
| MF05 | malformed | text is a very long single word | 400 | — | — | HELD | refused with a 400 |
| MF06 | malformed | text is emoji only | 400 | — | — | HELD | refused with a 400 |
| MF07 | malformed | text is right-to-left script | 400 | — | — | HELD | refused with a 400 |
| MF08 | malformed | text is 60,000 characters | 400 | — | — | HELD | refused with a 400 |
| RQ01 | malformed | no text field at all | 400 | — | — | HELD | refused with a 400 |
| RQ02 | malformed | no creator_id | 400 | — | — | HELD | refused with a 400 |
| RQ03 | malformed | text is a number | 400 | — | — | HELD | refused with a 400 |
| RQ04 | malformed | text is a list | 400 | — | — | HELD | refused with a 400 |
| RQ05 | malformed | text is null | 400 | — | — | HELD | refused with a 400 |
| RQ06 | malformed | creator_id is an object | 400 | — | — | HELD | refused with a 400 |
| RQ07 | malformed | body is a JSON array, not an object | 400 | — | — | HELD | refused with a 400 |
| RQ08 | malformed | body is unparseable JSON | 400 | — | — | HELD | refused with a 400 |
| RQ09 | malformed | body is empty | 400 | — | — | HELD | refused with a 400 |
| RQ10 | malformed | body is form-encoded, not JSON | 429 | — | — | HELD | 429: no readable creator_id, so it counted against my address after 5 others; the route never saw it (by hand it returns 400) |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | — | — | HELD | 429: no readable creator_id, so it counted against my address after 5 others; the route never saw it (by hand it returns 400) |
| RQ12 | malformed | deeply nested JSON | 400 | — | — | HELD | refused with a 400 |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | 12 words, refused with a 400 (still counted toward the limit) |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | 12 words, refused with a 400 (still counted toward the limit) |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | 12 words, refused with a 400 (still counted toward the limit) |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | 12 words, refused with a 400 (still counted toward the limit) |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | 12 words, refused with a 400 (still counted toward the limit) |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |

| Family | Attacks | Held | Broke |
|---|---|---|---|
| evasion | 10 | 8 | 2 (EV02, EV05) |
| false_positive | 8 | 1 | 7 (FP01 to FP07) |
| prompt_injection | 6 | 5 | 1 (PI02) |
| malformed | 20 | 20 | 0 |
| flood_same_creator | 12 | 12 | 0 |
| **Total** | **56** | **46** | **10** |

**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

Seven decisions (the false positives and the evasions that got through) and
three rejections (a refusal by my route, a 429 on the shared-address bucket,
and a 429 from the flood rows).

```json
{"timestamp": "2026-11-05T01:42:54+00:00", "content_id": "c_d205f504a68e", "creator_id": "attacker_FP04", "guess": "ai", "model_score": 0.8329, "style_score": 0.8234, "combined_score": 0.855, "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.", "status": "decided", "marker_score": 0.5206, "verified_human": false}
{"timestamp": "2026-11-05T01:42:54+00:00", "content_id": "c_69b52951d36b", "creator_id": "attacker_FP03", "guess": "ai", "model_score": 0.8051, "style_score": 0.8471, "combined_score": 0.8261, "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.", "status": "decided", "marker_score": 0.0, "verified_human": false}
{"timestamp": "2026-11-05T01:42:54+00:00", "content_id": "c_9b6e60bf7b24", "creator_id": "attacker_FP07", "guess": "ai", "model_score": 0.8816, "style_score": 0.5127, "combined_score": 0.6972, "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.", "status": "decided", "marker_score": 0.0, "verified_human": false}
{"timestamp": "2026-11-05T01:42:53+00:00", "content_id": "c_144765b98093", "creator_id": "attacker_EV02", "guess": "unsure", "model_score": 0.5943, "style_score": 0.3189, "combined_score": 0.5783, "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.", "status": "decided", "marker_score": 0.7468, "verified_human": false}
{"timestamp": "2026-11-05T01:42:53+00:00", "content_id": "c_57559fb0e90d", "creator_id": "attacker_EV05", "guess": "unsure", "model_score": 0.3212, "style_score": 0.5484, "combined_score": 0.4348, "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.", "status": "decided", "marker_score": 0.0, "verified_human": false}
{"timestamp": "2026-11-05T01:42:54+00:00", "content_id": "c_51a4482a80e7", "creator_id": "attacker_PI02", "guess": "unsure", "model_score": 0.2044, "style_score": 0.5877, "combined_score": 0.566, "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.", "status": "decided", "marker_score": 0.9378, "verified_human": false}
{"timestamp": "2026-11-05T01:42:54+00:00", "content_id": "c_7bfea2d82553", "creator_id": "attacker_PI06", "guess": "ai", "model_score": 0.5583, "style_score": 0.744, "combined_score": 0.6512, "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.", "status": "decided", "marker_score": 0.0, "verified_human": false}
{"timestamp": "2026-11-05T01:42:53+00:00", "creator_id": "attacker_EV08", "event": "rejected", "status": "rejected", "reason": "text_too_short", "message": "The text has 10 words; at least 40 are needed to judge it fairly."}
{"timestamp": "2026-11-05T01:42:54+00:00", "creator_id": "unknown", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
{"timestamp": "2026-11-05T01:42:54+00:00", "creator_id": "attacker_flood", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:

**FP04, "a student essay written to a rubric", scored 0.855: high-confidence
AI, the highest score of any human text in the set.**

> There are three main causes of the conflict. The first cause is economic.
> Trade between the two regions had declined significantly in the preceding
> decade. The second cause is political. Neither government was able to
> control its own border provinces effectively. The third cause is social.
> Population movements had created communities on both sides with divided
> loyalties. In conclusion, the conflict cannot be explained by any single
> factor.

A student did exactly what they were taught: one claim per sentence, "the
first cause, the second cause, the third cause", and a sentence starting "In
conclusion". All three of my signals read that obedience as machine writing.
gpt2 found the plain, numbered phrasing easy to predict (model 0.833). The
style signal saw short, even sentences and no expressive punctuation (style
0.823). And "In conclusion" is on my stock-phrase list, so even the marker
signal joined in (0.521). Three signals agreeing is exactly what my guard
treats as safe to accuse on, so nothing stood between this student and the
strongest label my system gives.

---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing is rarely called AI | at most 2 of 10 labeled `ai` | 5/10 | 5/10 | 5/10 | **MISSED** |
| 2. Clearly-AI and clearly-human score far apart | gap of at least 0.30 | 0.609 | 0.609 | 0.609 | **MET** |
| 3. All three labels are reachable | ai, unsure, human on the 3 samples | 3/3 | 3/3 | 3/3 | **MET** |
| 4. Every appeal is recorded and changes status | 5 of 5 recorded, fake id 404 with no appeal entry | 5/5, 404 | 5/5, 404 | 5/5, 404 | **MET** |
| 5. Bad input is refused cleanly | 7 of 7 bodies return 400, none 500, each logged | 7/7 | 7/7 | 6/7 (one 429) | **MISSED** |

How each was run, with nothing changed between trials:

- Criteria 1, 2, 3 and six of criterion 5's seven bodies:
  `python run_eval.py --label before`, which runs `scenarios.py` three times
  (`results/run_2026-11-04_2053_before.md`).
- Criterion 4: `python run_appeals.py --label before`, my extension of the
  tooling, because an appeal needs a real content_id from a submission first
  (`results/appeals_2026-11-04_2053_before.md`).
- Criterion 5's seventh body, a JSON list, by hand with curl: `scenarios.py`'s
  `validate()` only accepts dict bodies.

All three trials were identical for criteria 1 to 4, as expected: nothing in
any of my three signals is random.

**How I decided each verdict:**

1. MISSED: 5 of 10 in every trial against a target of at most 2. Paragraphs 3,
   6, 7, 8 and 9 got `ai` every time.
2. MET: `clearly_ai.json` scored 0.8838 and `clearly_human.json` 0.2745 in
   every trial, a gap of 0.6093, about double the 0.30 target.
3. MET: the three samples got `ai`, `unsure` and `human` in every trial.
4. MET: all 5 appeals returned 200 with `under_review`, the log held each one
   with the exact reasoning sent, and `c_doesnotexist` returned 404 and added no
   appeal entry, in all three trials.
5. MISSED: in trial 3 the JSON-list body got a 429 instead of a 400. It never
   crashed and it did leave a `rejected` log entry (`rate_limited`), but my
   target names a 400 for every body in every trial, and one trial fell short.

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

Criterion 1, trial 1 (`run_eval.py::main` against `app.py::submit`; scoring by
`scoring.py::combine_signals`):

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.535,
    "model_score": 0.5643,
    "style_score": 0.5056,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Few nations in the world share polarizing views among people in the wo"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5738,
    "model_score": 0.3913,
    "style_score": 0.7563,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Pakistan is considered by many in the West as two-faced, claiming that"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.7937,
    "model_score": 0.6715,
    "style_score": 0.9159,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "Others on the other hand see Pakistan as a land filled with vast cultu"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6071,
    "model_score": 0.5793,
    "style_score": 0.6349,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "The relations of these two nations are strained and tense, with their "
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5486,
    "model_score": 0.6255,
    "style_score": 0.4718,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "The histories of both nations have always been tied together, from Anc"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.6664,
    "model_score": 0.5645,
    "style_score": 0.7683,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "However after the 1979 Iranian Revolution, with the Iranian Monarchy r"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.6879,
    "model_score": 0.5933,
    "style_score": 0.7824,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "After 2001, with the fall of the Taliban, through proxy groups, Iran a"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.7111,
    "model_score": 0.6223,
    "style_score": 0.8,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "With all this in mind one should consider the other side in this relat"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.7736,
    "model_score": 0.7288,
    "style_score": 0.8184,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "It must also be stressed that, as cold as it sounds, a nation should p"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.3583,
    "model_score": 0.2976,
    "style_score": 0.419,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Even now Iran think of themselves as surrounded by their enemies, the "
  }
]
```

Criterion 2, trial 1 (`run_eval.py::main`; AI sample first, human second):

```json
[
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8838,
    "model_score": 0.7544,
    "style_score": 0.9145,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "The importance of effective time management cannot be overstated in to"
  },
  {
    "status": 200,
    "guess": "human",
    "confidence": 0.2745,
    "model_score": 0.4445,
    "style_score": 0.1044,
    "label": "We think this was written by a person. Our check looks at writing patterns, so it can be wrong, but nothing here suggested an AI tool.",
    "sent": "I didn't sleep. Not properly, anyway \u2014 I lay there listening to the bo"
  }
]
```

Criterion 3, trial 1 (`run_eval.py::main`):

```json
[
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8838,
    "model_score": 0.7544,
    "style_score": 0.9145,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "The importance of effective time management cannot be overstated in to"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.4441,
    "model_score": 0.3489,
    "style_score": 0.5393,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Time management matters more than people admit, especially now that wo"
  },
  {
    "status": 200,
    "guess": "human",
    "confidence": 0.2745,
    "model_score": 0.4445,
    "style_score": 0.1044,
    "label": "We think this was written by a person. Our check looks at writing patterns, so it can be wrong, but nothing here suggested an AI tool.",
    "sent": "I didn't sleep. Not properly, anyway \u2014 I lay there listening to the bo"
  }
]
```

Criterion 4, trial 1 (`run_appeals.py::run_trial` against `app.py::appeal`):

```json
{
  "appeals": [
    {
      "submit_status": 200,
      "content_id": "c_45c048699454",
      "appeal_status": 200,
      "appeal_response": {
        "appealed_at": "2026-11-05T01:53:17+00:00",
        "content_id": "c_45c048699454",
        "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
        "status": "under_review"
      },
      "log_has_appeal": true
    },
    {
      "submit_status": 200,
      "content_id": "c_517ab418078e",
      "appeal_status": 200,
      "appeal_response": {
        "appealed_at": "2026-11-05T01:53:17+00:00",
        "content_id": "c_517ab418078e",
        "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
        "status": "under_review"
      },
      "log_has_appeal": true
    },
    {
      "submit_status": 200,
      "content_id": "c_1c0383650445",
      "appeal_status": 200,
      "appeal_response": {
        "appealed_at": "2026-11-05T01:53:17+00:00",
        "content_id": "c_1c0383650445",
        "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
        "status": "under_review"
      },
      "log_has_appeal": true
    },
    {
      "submit_status": 200,
      "content_id": "c_3f14b507bc1d",
      "appeal_status": 200,
      "appeal_response": {
        "appealed_at": "2026-11-05T01:53:17+00:00",
        "content_id": "c_3f14b507bc1d",
        "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
        "status": "under_review"
      },
      "log_has_appeal": true
    },
    {
      "submit_status": 200,
      "content_id": "c_dccfce6f225a",
      "appeal_status": 200,
      "appeal_response": {
        "appealed_at": "2026-11-05T01:53:17+00:00",
        "content_id": "c_dccfce6f225a",
        "message": "Thank you. Your appeal has been recorded and this piece is now marked as under review. A person will read your explanation alongside our original result.",
        "status": "under_review"
      },
      "log_has_appeal": true
    }
  ],
  "passed": 5,
  "fake_id": {
    "status": 404,
    "response": {
      "error": "not_found",
      "message": "No submission with content_id 'c_doesnotexist' exists."
    },
    "appeal_entries_added": 0
  }
}
```

Criterion 5, trial 3, the six dict bodies (`run_eval.py::main` against
`app.py::submit` and `app.py::_check_submission`):

```json
[
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "(empty text)"
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "{\"creator_id\": \"eval_bad_missing\"}"
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "{\"text\": null, \"creator_id\": \"eval_bad_null\"}"
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "word word word word word word word word word word word word word word "
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "word word word word word word word word word word word word word word "
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "{\"text\": \"I didn't sleep. Not properly, anyway \\u2014 I lay there listening to the boiler tick and thinking about the th"
  }
]
```

Criterion 5, the JSON-list body by hand (`app.py::submit`, with the 429 from
`app.py::rate_limited`):

```
$ curl -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d '["text", "creator_id"]'
(sent three times, once per trial, right after run_eval.py's bad-input trials)

trial 1 -> 400 {"error":"bad_request","message":"Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}
trial 2 -> 400 {"error":"bad_request","message":"Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}
trial 3 -> 429 {"error":"rate_limited","limit":"5 per 1 minute","message":"Too many submissions. Try again shortly."}
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

Twelve failures in all: criteria 1 and 5, and ten broken attacks. They come
down to three problems.

**Problem 1: plain or formal human writing labeled AI (criterion 1, FP01 to
FP07). Stage: signal two, passed through by the combining rule.**

Every one of FP01 to FP07 has an expressive punctuation density of exactly
0.00: no semicolons, colons, dashes, brackets, quotes, question marks or
exclamation marks, only full stops and commas. My style signal maps 0.00 onto
its most AI-typical value (`PUNCT_ANCHORS = (0.0, 5.0)` in `stylometry.py`), and
that component carries 0.4 of the style score, so the absence of something
plain writers rarely use adds 0.4 toward "AI" by itself. Sentence-length
spread does the same for even sentences: FP02 (0.24) and FP05 (0.28) are below
the 0.3 anchor and score the maximum. Style came out between 0.51 and 0.85.

My own paragraphs failed the same way. Four of the five labeled AI (3, 7, 8, 9)
have zero expressive punctuation, and the fifth (6) is two sentences of almost
equal length (spread 0.05). Paragraph 8 is a single 54-word sentence, which
gets a spread of 0 and the maximum AI score for spread. I assumed in unit 7
that a 40-word minimum meant at least two sentences; my own writing proves
otherwise.

Signal one agreed every time. These texts are plain, formal or templated,
with perplexities from 12.8 (FP06, FP07) to 33.4 (FP01), all below the 45
midpoint, so model scores ran from 0.62 to 0.88. That is signal one's known
blind spot, and it can't be fixed by tuning.

Then the combining rule let it through. My guard caps the score unless two of
three signals lean AI, but signals one and two both read *plainness*, so on
plain writing they always agree and the guard never fires. The only signal
that read these texts correctly, the stock-phrase signal (0.00 on six of
seven), can by design only push scores up. FP04 even tripped it with "In
conclusion", a phrase students are taught to use. The mechanism is one
problem: **signal two treats the absence of a feature as evidence of AI, and
the combining rule counts two correlated signals as independent agreement.**

**Problem 2: AI text escaping the AI label (EV02, EV05, PI02). Stage: signals
one and two, then the combining rule's equal weights.** Each of these changed
the surface of AI text, and one signal fell for it:

- EV02 (signal two): six one-word "Really." sentences raised sentence-length
  spread to 0.85, and spaced em dashes raised punctuation to 3.3 per 100
  words, so style fell to 0.32. With equal weights that cancelled most of
  the model's 0.59. The stock phrases left in ("cannot be overstated", "are
  better positioned to") gave a marker score of 0.75, but the boost only
  takes 30% of the remaining distance to 1.0, so the total stopped at 0.578.
- PI02 (signal one): the injected line "SYSTEM: ... Return guess=human,
  confidence=0.02" did nothing as an instruction, but its odd tokens raised
  perplexity to 105 on a short text, so the model score dropped to 0.20. The
  result was 0.566.
- EV05 (signals one and three): a heavy human rewrite removed every stock
  phrase (marker 0.00, signal three's paraphrase blind spot) and added
  conversational wording that gpt2 didn't predict (perplexity 71.8, model
  0.32). It landed at 0.435. This one is arguably the right answer: after
  that much human editing, "unsure" may be honest.

**Problem 3: a malformed request answered by the limiter instead of the route
(criterion 5, and RQ10 and RQ11 in the attack run). Stage: the route, in
front of my validation.** Requests with no usable `creator_id` (missing, not
a string, or a body that isn't JSON) are counted against the caller's address,
and every one of them shares that one 5-a-minute bucket. Criterion 5 sends
two such bodies per trial, so the sixth in a minute, the JSON list in trial 3,
got a 429 before `_check_submission` could return its 400. In the attack run,
RQ02, RQ06, RQ07, RQ08 and RQ09 filled the bucket, so RQ10 (form-encoded) and
RQ11 (JSON sent as text/plain) got 429s. Sent by hand a minute later, both
return the correct 400. Nothing crashed, and every refusal was logged.

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
