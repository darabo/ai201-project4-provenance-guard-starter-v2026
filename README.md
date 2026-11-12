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

> **Unit 8 update:** these were the ranges in unit 7. Unit 8's second
> improvement raised the AI threshold to 0.80, so unsure now covers above 0.35
> and below 0.80, and high-confidence AI covers 0.80 to 1.00. The label text
> didn't change. See The Improvement.

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

**Moment 3 (unit 8): picking the worst outcome**

- _What I asked for:_ After the first attack run, I asked Claude to help me
  read the results and mark each attack held or broke.
- _What came back:_ The marks, a diagnosis of each failure, and four
  candidates for the single worst outcome, with FP03 (a non-native English
  speaker, 0.826) listed first.
- _What I changed:_ I picked FP04, the student essay written to a rubric,
  instead. It scored highest of all the human texts (0.855), and it was
  accused for doing exactly what the student was taught.

**Moment 4 (unit 8): the second improvement and the trade**

- _What I asked for:_ Before re-running anything, I asked Claude to estimate
  what each candidate improvement would do, then had it make and measure
  both.
- _What came back:_ An offline estimate that matched the real runs: the
  0.80 threshold would clear every false positive and let almost all the
  dressed-up AI text through. The measured run confirmed it (11 of 12 escaped).
- _What I changed:_ I didn't adopt the setting that made my own numbers look
  best. Improvement 2 gave me 0 of 10 of my paragraphs labeled AI, but for my
  production trade I chose a 0.70 line with human review instead. I also
  dropped my third stretch item rather than claim it, because I never got
  access to another team's service.

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

   > **Dropped (2026-11-04):** I didn't get access to another team's running
   > service, so I didn't build this one and I'm not claiming it. Items 1 and 2
   > are built: see Rate Limiting and The Improvement.

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

**What I changed:** One line of scoring, in `stylometry.py::style_signal`.
The punctuation component is now capped at 0.5 (`PUNCT_ABSENCE_CAP`), so a
text with no expressive punctuation scores neutral on that component instead of
fully AI-typical. Real dashes, quotes, questions and semicolons still pull the
score toward human exactly as before. Because that component carries 0.4 of
the style score, the most this can move style is 0.2, and only for texts with
little or no expressive punctuation. Nothing else changed: same signals, same
weights, same thresholds, same labels.

**Which diagnosis pointed at it:** Problem 1. All seven human texts wrongly
labeled AI (FP01 to FP07), and four of the five of my own paragraphs labeled
AI, had an expressive punctuation density of exactly 0.00, which the old
anchor scored as the most AI-typical value possible. `clearly_ai.json` also has
none, so the absence of punctuation was never telling people and models
apart; it was only adding 0.4 toward "AI" for everyone who writes plainly.

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->

`python run_attacks.py --set attack_set --label after`, all 56 attacks, same
service, same order, with improvement 1 as the only change
(`results/attack_run_2026-11-04_2100_after.md`). The Note column gives the
before result wherever it changed.

| ID | Family | Targeting | Status | Guess | Score | Verdict | Note |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | unsure | 0.611 | **BROKE** | before: ai 0.686 |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.578 | **BROKE** |  |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | ai | 0.727 | HELD |  |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | ai | 0.785 | HELD | before: ai 0.858 |
| EV05 | evasion | both signals: heavy human editing pass | 200 | unsure | 0.384 | **BROKE** | before: unsure 0.435 |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | unsure | 0.599 | **BROKE** | before: ai 0.672 |
| EV07 | evasion | signal two: padding with punctuation | 200 | ai | 0.670 | HELD |  |
| EV08 | evasion | signal one: text below the token window | 400 | — | — | HELD | refused at 10 words; never scored |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | ai | 0.772 | HELD | before: ai 0.847 |
| EV10 | evasion | signal two: repeated stanza structure | 200 | ai | 0.830 | HELD | before: ai 0.900 |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | unsure | 0.576 | HELD | before: ai 0.676 |
| FP02 | false_positive | human writing in a formal register | 200 | ai | 0.669 | **BROKE** | before: ai 0.769 |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | ai | 0.726 | **BROKE** | before: ai 0.826 |
| FP04 | false_positive | a student essay written to a rubric | 200 | ai | 0.771 | **BROKE** | before: ai 0.855 |
| FP05 | false_positive | technical documentation written by a person | 200 | ai | 0.700 | **BROKE** | before: ai 0.800 |
| FP06 | false_positive | a person imitating a formal template | 200 | unsure | 0.640 | HELD | before: ai 0.768 |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | unsure | 0.597 | HELD | before: ai 0.697 |
| FP08 | false_positive | very short genuine human submission | 400 | — | — | HELD | 8 words, refused with a 400: not accused, but turned away |
| PI01 | prompt_injection | instruction to ignore the check | 200 | unsure | 0.636 | **BROKE** | instruction did nothing; the punctuation change lowered style to 0.53, so this AI text fell into unsure; before: ai 0.708 |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | unsure | 0.558 | **BROKE** | before: unsure 0.566 |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | ai | 0.694 | HELD |  |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | unsure | 0.500 | HELD | label text is fixed; nothing echoed back |
| PI05 | prompt_injection | attempt to inject into the audit log | 400 | — | — | HELD | refused at 28 words; nothing injected into the log |
| PI06 | prompt_injection | instruction plus real human text | 200 | unsure | 0.551 | HELD | instruction did nothing; its human text is no longer labeled AI; before: ai 0.651 |
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
| RQ10 | malformed | body is form-encoded, not JSON | 429 | — | — | HELD | 429 on the shared-address bucket, as before |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | — | — | HELD | 429 on the shared-address bucket, as before |
| RQ12 | malformed | deeply nested JSON | 400 | — | — | HELD | refused with a 400 |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |

| Family | Attacks | Broke before | Broke after |
|---|---|---|---|
| evasion | 10 | 2 (EV02, EV05) | 4 (EV01, EV02, EV05, EV06) |
| false_positive | 8 | 7 (FP01 to FP07) | 4 (FP02, FP03, FP04, FP05) |
| prompt_injection | 6 | 1 (PI02) | 2 (PI01, PI02) |
| malformed | 20 | 0 | 0 |
| flood_same_creator | 12 | 0 | 0 |
| **Total** | **56** | **10** | **10** |

### Run Log — After

`python run_eval.py --label after` (`results/run_2026-11-04_2101_after.md`),
`python run_appeals.py --label after` (`results/appeals_2026-11-04_2101_after.md`),
and the JSON-list body by hand, in the same order and timing as before.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict | Before |
|---|---|---|---|---|---|---|
| 1. My own writing is rarely called AI | at most 2 of 10 labeled `ai` | 2/10 | 2/10 | 2/10 | **MET** | 5/10, MISSED |
| 2. Clearly-AI and clearly-human score far apart | gap of at least 0.30 | 0.539 | 0.539 | 0.539 | **MET** | 0.609, MET |
| 3. All three labels are reachable | ai, unsure, human on the 3 samples | 3/3 | 3/3 | 3/3 | **MET** | MET |
| 4. Every appeal is recorded and changes status | 5 of 5 recorded, fake id 404 with no appeal entry | 5/5, 404 | 5/5, 404 | 5/5, 404 | **MET** | MET |
| 5. Bad input is refused cleanly | 7 of 7 bodies return 400, none 500, each logged | 7/7 | 7/7 | 6/7 (one 429) | **MISSED** | MISSED |

Criterion 1 is MET at exactly the limit: paragraphs 3 (0.694) and 9 (0.674)
are still labeled AI in every trial, so 2 of 10, and any third one would have
missed. Criterion 5 didn't move because the change doesn't touch the route.

Criterion 1, trial 1, after (`run_eval.py::main` against `app.py::submit`):

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5259,
    "model_score": 0.5643,
    "style_score": 0.4874,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Few nations in the world share polarizing views among people in the wo"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5478,
    "model_score": 0.3913,
    "style_score": 0.7044,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Pakistan is considered by many in the West as two-faced, claiming that"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.6937,
    "model_score": 0.6715,
    "style_score": 0.7159,
    "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wrote this yourself, you can ask for a person to review it.",
    "sent": "Others on the other hand see Pakistan as a land filled with vast cultu"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5871,
    "model_score": 0.5793,
    "style_score": 0.5949,
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
    "guess": "unsure",
    "confidence": 0.6331,
    "model_score": 0.5645,
    "style_score": 0.7016,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "However after the 1979 Iranian Revolution, with the Iranian Monarchy r"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5878,
    "model_score": 0.5933,
    "style_score": 0.5824,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "After 2001, with the fall of the Taliban, through proxy groups, Iran a"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6111,
    "model_score": 0.6223,
    "style_score": 0.6,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "With all this in mind one should consider the other side in this relat"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.6736,
    "model_score": 0.7288,
    "style_score": 0.6184,
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

**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->

It helped the problem it was aimed at, and it cost exactly what the other side
of the trade predicts. I know because the same 56 attacks and the same five
criteria ran before and after with nothing else changed, and every score
difference is the punctuation component: style fell by the full 0.2 on every
text with no expressive punctuation, by less on texts with a little (EV05 by
0.10, PI02 by 0.02), and not at all on texts with 2.5 or more marks per 100
words, where the old score was already under the cap.

- **Fixed:** wrong accusations of real writers fell from 7 of 7 scorable
  false-positive attacks to 4. FP01 (plain), FP06 (a formal template) and FP07
  (deliberate repetition) moved to unsure, and PI06's human campsite text did
  too. My own writing went from 5 of 10 labeled AI to 2 of 10, which turned
  criterion 1 from MISSED to MET.
- **Cost:** AI text escaping the AI label rose from 3 to 6 (EV01, EV06 and
  PI01 joined EV02, EV05 and PI02, all now "unsure"). The cap can't tell an AI
  text with no punctuation from a human one, so it lowers both. The spread
  between the two samples shrank from 0.609 to 0.539, still well above 0.30.
- **Not fixed:** FP02 to FP05 (formal register, a non-native speaker, a
  student essay, technical documentation) are still labeled AI, now between
  0.669 and 0.771. Signal one scores them 0.74 to 0.83 by itself, and their
  even sentences keep style above 0.6, so two signals still agree and the guard
  still lets it through. The punctuation fix removed one wrong reason to accuse
  them, not the main one.

Total broken attacks stayed at 10, but which 10 changed: three fewer writers
falsely accused, three more AI texts let through as "unsure". On a writing
site that is the direction I want, because "unsure" makes no accusation,
while the AI label does.

### Second improvement (stretch): the AI threshold from 0.65 to 0.80

**What I changed:** `AI_THRESHOLD` in `config.py`, from 0.65 to 0.80, on top
of improvement 1. The unsure band is now 0.35 to 0.80, and the AI label covers
0.80 to 1.00. The agreement guard in `scoring.py::combine_signals` caps at the
threshold minus 0.01, so its cap moved with it, from 0.64 to 0.79. Nothing
else changed.

**Which diagnosis pointed at it:** what was left of problem 1 after
improvement 1. FP02 to FP05 and my paragraphs 3 and 9 were still labeled AI at
0.669 to 0.771, and the cause was signal one: gpt2 alone rated those formal,
plain texts 0.74 to 0.83. That blind spot can't be tuned out of the signal,
so the remaining lever was how much evidence the AI label demands.

#### Attack Run — After improvement 2

`python run_attacks.py --set attack_set --label after2`
(`results/attack_run_2026-11-04_2103_after2.md`). The Note column gives the
improvement-1 result wherever it changed.

| ID | Family | Targeting | Status | Guess | Score | Verdict | Note |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | unsure | 0.611 | **BROKE** |  |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.578 | **BROKE** |  |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | unsure | 0.727 | **BROKE** | after improvement 1: ai 0.727 |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | unsure | 0.785 | **BROKE** | after improvement 1: ai 0.785 |
| EV05 | evasion | both signals: heavy human editing pass | 200 | unsure | 0.384 | **BROKE** |  |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | unsure | 0.599 | **BROKE** |  |
| EV07 | evasion | signal two: padding with punctuation | 200 | unsure | 0.670 | **BROKE** | after improvement 1: ai 0.670 |
| EV08 | evasion | signal one: text below the token window | 400 | — | — | HELD | refused at 10 words; never scored |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | unsure | 0.772 | **BROKE** | after improvement 1: ai 0.772 |
| EV10 | evasion | signal two: repeated stanza structure | 200 | ai | 0.830 | HELD |  |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | unsure | 0.576 | HELD |  |
| FP02 | false_positive | human writing in a formal register | 200 | unsure | 0.669 | HELD | after improvement 1: ai 0.669 |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | unsure | 0.726 | HELD | after improvement 1: ai 0.726 |
| FP04 | false_positive | a student essay written to a rubric | 200 | unsure | 0.771 | HELD | after improvement 1: ai 0.771 |
| FP05 | false_positive | technical documentation written by a person | 200 | unsure | 0.700 | HELD | after improvement 1: ai 0.700 |
| FP06 | false_positive | a person imitating a formal template | 200 | unsure | 0.668 | HELD | after improvement 1: unsure 0.640 |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | unsure | 0.597 | HELD |  |
| FP08 | false_positive | very short genuine human submission | 400 | — | — | HELD | 8 words, refused with a 400 |
| PI01 | prompt_injection | instruction to ignore the check | 200 | unsure | 0.636 | **BROKE** |  |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | unsure | 0.558 | **BROKE** |  |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | unsure | 0.694 | **BROKE** | after improvement 1: ai 0.694 |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | unsure | 0.500 | HELD | label text is fixed; nothing echoed back |
| PI05 | prompt_injection | attempt to inject into the audit log | 400 | — | — | HELD | refused at 28 words; nothing injected |
| PI06 | prompt_injection | instruction plus real human text | 200 | unsure | 0.551 | HELD | instruction did nothing; human text stays unsure |
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
| RQ10 | malformed | body is form-encoded, not JSON | 429 | — | — | HELD | 429 on the shared-address bucket |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | — | — | HELD | 429 on the shared-address bucket |
| RQ12 | malformed | deeply nested JSON | 400 | — | — | HELD | refused with a 400 |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD | refused with a 400 (counted) |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | rate limited after 5 |

| Family | Attacks | Broke before | Broke after 1 | Broke after 2 |
|---|---|---|---|---|
| evasion | 10 | 2 | 4 | 8 (all but EV08 and EV10) |
| false_positive | 8 | 7 | 4 | 0 |
| prompt_injection | 6 | 1 | 2 | 3 (PI01, PI02, PI03) |
| malformed | 20 | 0 | 0 | 0 |
| flood_same_creator | 12 | 0 | 0 | 0 |
| **Total** | **56** | **10** | **10** | **11** |

#### Run Log — After improvement 2

`python run_eval.py --label after2` (`results/run_2026-11-04_2105_after2.md`),
`python run_appeals.py --label after2` (`results/appeals_2026-11-04_2105_after2.md`),
and the JSON-list body by hand, in the same order and timing as the other two
runs.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict | Before | After 1 |
|---|---|---|---|---|---|---|---|
| 1. My own writing is rarely called AI | at most 2 of 10 labeled `ai` | 0/10 | 0/10 | 0/10 | **MET** | 5/10 MISSED | 2/10 MET |
| 2. Clearly-AI and clearly-human score far apart | gap of at least 0.30 | 0.539 | 0.539 | 0.539 | **MET** | 0.609 MET | 0.539 MET |
| 3. All three labels are reachable | ai, unsure, human on the 3 samples | 3/3 | 3/3 | 3/3 | **MET** | MET | MET |
| 4. Every appeal is recorded and changes status | 5 of 5 recorded, fake id 404 with no appeal entry | 5/5, 404 | 5/5, 404 | 5/5, 404 | **MET** | MET | MET |
| 5. Bad input is refused cleanly | 7 of 7 bodies return 400, none 500, each logged | 7/7 | 7/7 | 6/7 (one 429) | **MISSED** | MISSED | MISSED |

Criterion 3 is MET by a hair: `clearly_ai.json` scored 0.8137 against the new
0.80 line, a margin of 0.014. Criterion 2's number didn't change (0.539), but
my reason for 0.30 was that it matched the width of the unsure band, and the
band is now 0.45 wide, so a 0.30 gap no longer guarantees that both samples
can't sit inside it together.

Criterion 1, trial 1, after improvement 2 (`run_eval.py::main` against
`app.py::submit`):

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5259,
    "model_score": 0.5643,
    "style_score": 0.4874,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Few nations in the world share polarizing views among people in the wo"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5478,
    "model_score": 0.3913,
    "style_score": 0.7044,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Pakistan is considered by many in the West as two-faced, claiming that"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6937,
    "model_score": 0.6715,
    "style_score": 0.7159,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "Others on the other hand see Pakistan as a land filled with vast cultu"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5871,
    "model_score": 0.5793,
    "style_score": 0.5949,
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
    "guess": "unsure",
    "confidence": 0.6331,
    "model_score": 0.5645,
    "style_score": 0.7016,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "However after the 1979 Iranian Revolution, with the Iranian Monarchy r"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.5878,
    "model_score": 0.5933,
    "style_score": 0.5824,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "After 2001, with the fall of the Taliban, through proxy groups, Iran a"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6111,
    "model_score": 0.6223,
    "style_score": 0.6,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
    "sent": "With all this in mind one should consider the other side in this relat"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6736,
    "model_score": 0.7288,
    "style_score": 0.6184,
    "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it.",
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

**Did it help, and how do I know:** It did what it was aimed at and made the
detector close to useless as a detector, and the three result sets side by
side show both. No human text in the attack set is labeled AI any more (7, then
4, then 0), and none of my own paragraphs are (5, then 2, then 0). But AI text
escaping the AI label went from 3, to 6, to 11 of the 12 scorable evasion and
injection attacks. Only EV10, a repeated-stanza text at 0.830, is still caught.
The total of broken attacks rose from 10 to 11, and almost every result is now
"unsure", which is close to the system not answering at all.

I'd keep improvement 1 and not ship improvement 2 as it stands. Improvement 1
removed a wrong reason to accuse people at a modest cost. Improvement 2 removes
the accusations by mostly removing the AI label, so the system is safer for
writers only because it has stopped saying much. I'm leaving it in the
repository because it's the last measured state, and What's Still Broken says
what I'd do instead.

---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->

As the repository stands (both improvements in), these still fail:

**AI text escaping into "unsure": EV01 to EV07, EV09, PI01, PI02, PI03.**
Most of these escaped because of improvement 2, not because the attacks
got smarter: at 0.65 the threshold caught EV03, EV04, EV07, EV09 and PI03. What
I'd do: set the line back near 0.70 and send AI results to a person (the
trade below), then fix the two tricks the diagnosis named. For EV02, ignore
sentences under three words when measuring sentence-length spread, so a
string of "Really." can't fake human lumpiness. For PI02, score only the prose:
drop lines that read as instructions to a system ("SYSTEM:", "Ignore all
previous instructions") before gpt2 sees the text, and log that they were
dropped. EV05 I'd leave as it is; after a rewrite that heavy, "unsure" is
honest.

**Criterion 5 (and RQ10, RQ11): the limiter answers before the route.** What
I'd do: give requests with no usable `creator_id` their own, roomier address
limit (around 20 a minute), or check the body's shape before the limiter so a
malformed request always gets its 400. Either needs its own before-and-after
run against criterion 5.

**Formal and plain human writing (FP02 to FP05) is only protected by the
threshold.** Their scores didn't fall far: 0.669 to 0.771, with gpt2 alone at
0.74 to 0.83. If the line comes back down to 0.70, three of the four are
labeled AI again (FP02 at 0.669 stays unsure). The real fix is upstream of
anything I can tune: a stronger model than gpt2 for signal one, or human
review before any AI label is shown.

**Criterion 3 holds by 0.014.** `clearly_ai.json` scores 0.8137 against the
0.80 line. A slightly different AI sample would fail it. At 0.70 the margin
would be 0.11.

**Not touched by this unit's runs:** the verified-writer gate from unit 7
still refuses writers on the same detector that misjudges them, and
per-creator limits can still be dodged by inventing a new `creator_id` per
request (8 of 8 got through in my test).

**Why I stopped:** the unit allows one improvement (plus the stretch one),
because every extra change needs its own before-and-after run to mean
anything. Each fix above changes a different stage, so making them all at once
would leave me unable to say which one did what.

**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->

I'd set the AI line around 0.70 and never show the AI label automatically:
anything that scores AI goes to a person first, and the writer only ever sees
"unsure" or "human" unless that person agrees. The site pays for it in
moderators' time, and flagged writers pay by waiting for a review, which costs
them far less than a public accusation the site later has to take back.

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

## Capstone

Unit 9. Everything under this heading is the capstone. The sections above it
are units 7 and 8 and are left as they were.

**What This Extends**

This extends Provenance Guard, the fourth of my four systems (units 7 and 8).
It is the Flask service that takes a piece of writing on `POST /submit`, scores
it with three signals (gpt2 perplexity, sentence style, stock phrases) and
answers with a label: high-confidence AI, unsure, or high-confidence human.

Before this unit the service only ever ran from my editor with `python app.py`,
on Flask's development server. The one record it kept was the audit log
(`logs/audit.jsonl`), which stores decisions, appeals and rejections. That log
cannot answer two questions about a running service: how long did a request
take, and what happened to a request that never became a decision (a wrong
URL, a crash, a `GET /health`)?

What is new in this unit:

1. A run log. `runlog.py` writes one JSON record per HTTP request to
   `logs/runs.jsonl`, whatever the outcome: timestamp, what came in, what went
   out, how long it took, and how that time split across the three signals.
2. A run path that is not my editor. The service starts under `gunicorn` from
   one command, documented in [RUNNING.md](RUNNING.md) with the environment it
   needs.
3. A cost measurement. `measure_cost.py` sends ten real submissions and reads
   their compute time back out of the run log.

**The Shape**

Shape A, deploy and instrument. The extension is the operational layer around
a service whose scoring I am leaving alone: the start command, the run log,
and the numbers that come out of it.

Out of scope, each of which I considered and decided against:

- I am not fixing the unit 8 miss where the rate limiter answers before the
  route does (old criterion 5). That is failure hardening, which is Shape B,
  and it would need its own before and after run.
- I am not touching the detector, the weights or the thresholds. Every score
  the service returns should be the same as it was at the end of unit 8.
- I am not hosting it. `torch` plus the gpt2 weights need more memory than
  the 512 MB a free host gives, so this runs locally with a committed log
  (Path B). The arithmetic is in RUNNING.md.
- I am not building a dashboard or a metrics endpoint. The run log is a file
  that gets read with a script.

**Stretch (declared before building)**

Declared on the day I started the capstone, before any of this code existed:

- A latency breakdown: where the time goes across the stages of one run,
  measured from the per-stage timings in the run log.
- A load observation: the service run at about ten times its normal request
  rate, with a report on what changed.

**Running It**

Path B, local with logs. The service starts from one command, run in a
terminal from the repository folder with the virtual environment active:

```bash
gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 120
```

[RUNNING.md](RUNNING.md#the-capstone-run-path-unit-9) has the whole path from
a clean checkout: the Python version, each dependency with the version I ran,
the model file and its size, how to check the service is up, and what went
wrong when I followed my own instructions in a fresh clone.

I did not host it. Measured with `ps`, the worker process holds 39 MB before
its first submission and about 1,000 MB once gpt2 is loaded. A free host gives
512 MB.

The committed record of it running is `logs/runs.jsonl`: 36 requests
from one session on 2026-11-12 (UTC), against the service started with the
command above. Every log line quoted below is copied from that file.

**Instrumentation**

Every HTTP request writes one JSON record to `logs/runs.jsonl`, whatever
happens to it. The record is built in `app.py::_build_run_record` and written
by `runlog.py::write`. Both are called from a Flask `after_request` hook
(`app.py::_write_run_record`), which Flask runs for every response, so a route
cannot forget to log. Print the latest records with `python runlog.py --tail 10`.

What each record holds:

| Field | What it holds |
|---|---|
| `timestamp` | When the request arrived, UTC, to the millisecond |
| `request_id` | A random id for this request. It is also sent back in the `X-Request-ID` response header, so a caller can find their own row |
| `method`, `path` | Which route was asked for, e.g. `POST /submit` |
| `input` | What came in: body size in bytes, body type (`object`, `list`, `empty`, `unparseable`), the field names, the `creator_id`, and for a text its length in characters and words plus its first 60 characters. The full text is not stored |
| `output` | What went out: the HTTP status code, and where present the `content_id`, `guess`, `confidence`, the three signal scores, and the `error` code |
| `outcome` | `ok` (status 2xx), `rejected` (4xx: the caller's request was refused) or `error` (5xx: the service failed) |
| `duration_ms` | Elapsed time for the whole request, in milliseconds |
| `cpu_ms` | Processor time the service used during the request, summed over all cores. This is the cost figure |
| `stages_ms` | Only on requests that scored a text: milliseconds spent in gpt2 (`model`), the style measures, the stock-phrase search and the scoring rule |
| `cold_start` | `true` if gpt2 was not yet in memory when the request arrived |

Ten entries from the session, in the order they happened. The first `/submit`
is the cold start (2,031 ms); the next one took 37.9 ms.

```text
{"timestamp": "2026-11-12T01:49:32.767+00:00", "request_id": "r_bd6ac4bd3850", "method": "GET", "path": "/health", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 200, "ok": true}, "outcome": "ok", "duration_ms": 1.9, "cpu_ms": 1.8, "cold_start": true}
{"timestamp": "2026-11-12T01:49:32.803+00:00", "request_id": "r_544e503895f9", "method": "POST", "path": "/submit", "input": {"body_bytes": 728, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_6f4724424ba7", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2031.3, "cpu_ms": 1431.1, "cold_start": true, "stages_ms": {"model": 2029.5, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:34.848+00:00", "request_id": "r_42e5b217e895", "method": "POST", "path": "/submit", "input": {"body_bytes": 450, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 400, "text_words": 68, "text_preview": "Time management matters more than people admit, especially n"}, "output": {"status_code": 200, "content_id": "c_f0b78552a503", "guess": "unsure", "confidence": 0.4441, "model_score": 0.3489, "style_score": 0.5393, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 37.9, "cpu_ms": 53.4, "cold_start": false, "stages_ms": {"model": 36.3, "style": 0.1, "markers": 0.2, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:35.017+00:00", "request_id": "r_1b834adfd591", "method": "POST", "path": "/submit", "input": {"body_bytes": 355, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_1", "text_chars": 312, "text_words": 48, "text_preview": "The relations of these two nations are strained and tense, w"}, "output": {"status_code": 200, "content_id": "c_f3b30bd31a00", "guess": "unsure", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 30.3, "cpu_ms": 41.1, "cold_start": false, "stages_ms": {"model": 28.9, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:35.048+00:00", "request_id": "r_f26385f1f283", "method": "POST", "path": "/submit", "input": {"body_bytes": 378, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_2", "text_chars": 340, "text_words": 54, "text_preview": "The histories of both nations have always been tied together"}, "output": {"status_code": 200, "content_id": "c_f83e97b97f47", "guess": "unsure", "confidence": 0.5486, "model_score": 0.6255, "style_score": 0.4718, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 33.2, "cpu_ms": 45.2, "cold_start": false, "stages_ms": {"model": 31.8, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:35.083+00:00", "request_id": "r_f4702e3536e8", "method": "POST", "path": "/submit", "input": {"body_bytes": 444, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_3", "text_chars": 401, "text_words": 58, "text_preview": "However after the 1979 Iranian Revolution, with the Iranian "}, "output": {"status_code": 200, "content_id": "c_3e7470cd92ea", "guess": "unsure", "confidence": 0.6331, "model_score": 0.5645, "style_score": 0.7016, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 35.9, "cpu_ms": 48.1, "cold_start": false, "stages_ms": {"model": 34.5, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:35.201+00:00", "request_id": "r_085cca2ccba3", "method": "POST", "path": "/appeal", "input": {"body_bytes": 89, "body_type": "object", "fields": ["content_id", "reasoning"], "content_id": "c_f3b30bd31a00"}, "output": {"status_code": 200, "content_id": "c_f3b30bd31a00", "status": "under_review"}, "outcome": "ok", "duration_ms": 1.0, "cpu_ms": 1.0, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.226+00:00", "request_id": "r_4610c4305a99", "method": "GET", "path": "/content/c_f3b30bd31a00", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 200, "content_id": "c_f3b30bd31a00", "guess": "unsure", "confidence": 0.5871, "model_score": 0.5793, "style_score": 0.5949, "marker_score": 0.0, "status": "under_review"}, "outcome": "ok", "duration_ms": 0.8, "cpu_ms": 0.8, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.428+00:00", "request_id": "r_f7e280147233", "method": "POST", "path": "/submit", "input": {"body_bytes": 385, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_in_a_hurry", "text_chars": 338, "text_words": 54, "text_preview": "With all this in mind one should consider the other side in "}, "output": {"status_code": 200, "content_id": "c_53a9a8f4ca33", "guess": "unsure", "confidence": 0.6111, "model_score": 0.6223, "style_score": 0.6, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 29.4, "cpu_ms": 39.7, "cold_start": false, "stages_ms": {"model": 28.1, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
{"timestamp": "2026-11-12T01:49:35.579+00:00", "request_id": "r_9399928f588a", "method": "POST", "path": "/submit", "input": {"body_bytes": 548, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "cost_5e115b_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_970a65efa42e", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 40.1, "cpu_ms": 57.4, "cold_start": false, "stages_ms": {"model": 38.6, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
```

Failed runs from the same session. All six were refused by the service (status
400, 404 or 429) and each left a record with `"outcome": "rejected"`: an empty
text, a JSON list instead of an object, a body that is not valid JSON, an
appeal against a `content_id` that does not exist, a mistyped URL, and the
sixth submission in a minute from one writer.

```text
{"timestamp": "2026-11-12T01:49:35.142+00:00", "request_id": "r_211f5b4655d0", "method": "POST", "path": "/submit", "input": {"body_bytes": 38, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_4", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.165+00:00", "request_id": "r_f1ddd8159644", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.177+00:00", "request_id": "r_1e3a7d4babe8", "method": "POST", "path": "/submit", "input": {"body_bytes": 28, "body_type": "unparseable"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.213+00:00", "request_id": "r_512045e2e08b", "method": "POST", "path": "/appeal", "input": {"body_bytes": 70, "body_type": "object", "fields": ["content_id", "reasoning"], "content_id": "c_doesnotexist"}, "output": {"status_code": 404, "error": "not_found"}, "outcome": "rejected", "duration_ms": 1.0, "cpu_ms": 1.0, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.238+00:00", "request_id": "r_26066a21bd40", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
{"timestamp": "2026-11-12T01:49:35.459+00:00", "request_id": "r_95d1dc18bd58", "method": "POST", "path": "/submit", "input": {"body_bytes": 385, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "writer_in_a_hurry", "text_chars": 338, "text_words": 54, "text_preview": "With all this in mind one should consider the other side in "}, "output": {"status_code": 429, "error": "rate_limited"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": false}
```

No request in the session ended in a 5xx, so the committed log has no
`"outcome": "error"` record. I tested that path separately, through Flask's
test client, by making `_score_text` raise a `RuntimeError`. The request
returned 500 and left a record with `"outcome": "error"` and
`"error_type": "RuntimeError"`. That record is not in `logs/runs.jsonl`
because it did not come from the running service.

**What It Costs**

One run (one `POST /submit` that scores a text) costs **50.1 milliseconds of
processor time**, on an Apple M5 Pro. The service calls no paid API, so there
is no charge per request. What a run uses up is compute on the machine
holding the model.

How I measured it: `python measure_cost.py --save`, against the service
started from RUNNING.md. The script sends one warm-up submission, then ten of
my own paragraphs (42 to 86 words) one at a time, each from a different
`creator_id`. It reads the `X-Request-ID` header off each response, finds that
row in `logs/runs.jsonl`, and averages the `cpu_ms` the service recorded for
itself. The timing comes from inside the service (`time.process_time()` in
`app.py::_start_run_record` and `app.py::_build_run_record`), so it excludes
the time to send the request and receive the reply. The saved output is
`results/cost_2026-11-11_2049.md`:

```text
Cost measurement, 2026-11-11T20:49:35-05:00
Service: http://127.0.0.1:5000   model: gpt2   runs: 10

Warm-up (not in the average): 40.9 ms elapsed, 58.3 ms CPU, cold_start=False

| Run | Words | Status | Elapsed ms | CPU ms | Model ms | Client ms |
|---|---|---|---|---|---|---|
| 1 | 86 | 200 | 40.1 | 57.4 | 38.6 | 41.3 |
| 2 | 51 | 200 | 29.8 | 40.7 | 28.4 | 30.9 |
| 3 | 62 | 200 | 32.7 | 44.4 | 31.5 | 34.1 |
| 4 | 48 | 200 | 29.3 | 40.1 | 28.1 | 30.7 |
| 5 | 54 | 200 | 32.9 | 44.9 | 31.7 | 34.1 |
| 6 | 58 | 200 | 47.9 | 57.8 | 46.5 | 49.0 |
| 7 | 78 | 200 | 45.3 | 60.7 | 43.9 | 46.6 |
| 8 | 54 | 200 | 32.9 | 43.5 | 31.5 | 34.2 |
| 9 | 83 | 200 | 52.6 | 68.3 | 51.0 | 53.9 |
| 10 | 42 | 200 | 32.0 | 42.8 | 30.7 | 33.6 |

Successful runs averaged: 10 of 10
Elapsed per run:  mean 37.5 ms   (min 29.3, max 52.6)
CPU per run:      mean 50.1 ms   (min 40.1, max 68.3)
gpt2 share:       mean 36.2 ms of the elapsed time (96%)
```

CPU time is higher than elapsed time because gpt2 runs on more than one core
at once. gpt2 is 96% of the elapsed time, so the cost of a run is the cost of
one gpt2 pass over the text.

Two costs are not per run:

- The first submission after a start loads the model. In the session log that
  request took 2,031 ms elapsed and 1,431 ms of CPU, about 29 normal runs'
  worth (1,431 / 50.1 = 28.6). It is paid once per start.
- The loaded model holds about 1,000 MB of memory for as long as the service
  is up, whether or not anyone submits anything.

A hundred people a day, one submission each:

```text
100 runs x 50.1 ms CPU per run = 5,010 ms  = 5.0 seconds of CPU per day
plus one cold start per day    = 1,431 ms  = 1.4 seconds
total                          = 6,441 ms  = 6.4 seconds of CPU per day

one core has 86,400 seconds in a day
6.4 / 86,400 = 0.0000745 = 0.007% of one core
```

So at a hundred people a day the processor is idle for all but about six
seconds, and the cost that decides where this can run is the 1,000 MB of
memory held all day.

**Run Log and Verdicts**

The five capstone criteria are in [criteria.md](criteria.md) under "Capstone
criteria (unit 9)". They were committed on their own in `dab6067`, before any
trial was run. Everything below comes from one command, run against commit
`2d276f8`:

```bash
python run_capstone.py --label before
```

How the test runs, so the numbers can be judged:

- `run_capstone.py` starts the service itself with the command from
  RUNNING.md and restarts it before each criterion, so one criterion's
  requests cannot use up another's rate-limit allowance. Inside a criterion
  the three trials run back to back against the same running service.
- Criterion 1 cloned this repository's folder, not the GitHub URL, because
  the capstone commits were not pushed yet. Every other line of the
  RUNNING.md block ran as written.
- A criterion is MET only when all three trials reach the target.

The full output of all fifteen trials is in
`results/capstone_2026-11-11_2136_before.md`.

Run Log, before:

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible local run path | 2 of 2 checks (health, submit) per clean start | 2/2 | 2/2 | 2/2 | MET |
| 2. Complete structured run logging | 10 of 10 requests | 9/10 | 9/10 | 9/10 | MISSED |
| 3. Bad submission input is rejected and logged | 5 of 5 bodies | 5/5 | 5/5 | 5/5 | MET |
| 4. Warm submissions remain responsive | 9 of 10 within 500 ms | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeals preserve the original evidence | 4 of 4 checks | 4/4 | 4/4 | 4/4 | MET |

Real output, trial 1 of each criterion.

Criterion 1. Produced by `run_capstone.py::criterion_1`, which runs the
"From a clean checkout" block of RUNNING.md in an empty folder, then calls
`app.py::health` and `app.py::submit` on the service that block started. The
three clean starts took 26.7, 28.2 and 24.4 seconds to reach
`Booting worker with pid`.

```text
source cloned: /Users/darabonakdar/ai201-project4-provenance-guard-starter-v2026
'Booting worker with pid' seen after 26.7s
last lines of the start output:
  perplexity     12.5
  model_signal   0.8864   (higher = more likely AI)
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Starting gunicorn 23.0.0
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Listening at: http://127.0.0.1:5000 (17651)
  [2026-11-11 21:35:27 -0500] [17651] [INFO] Using worker: sync
  [2026-11-11 21:35:27 -0500] [17687] [INFO] Booting worker with pid: 17687
GET /health -> 200 {"detector_loaded": false, "detector_model": "gpt2", "log_entries": 575, "ok": true, "rate_limiting": true}
POST /submit -> 200 {"confidence": 0.8137, "content_id": "c_7b79071cd586", "creator_id": "demo_instructor", "guess": "ai", "label": "This reads very much like text written by an AI tool. Our check can be wrong. If you wr
last record in the clone's logs/runs.jsonl:
  {"timestamp": "2026-11-12T02:35:27.731+00:00", "request_id": "r_0b30a6949ec0", "method": "POST", "path": "/submit", "input": {"body_bytes": 725, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "demo_instructor", "text_chars": 680, "text_words": 91, "text_preview": "The importance of effective time management cannot be overst"}, "output": {"status_code": 200, "content_id": "c_7b79071cd586", "guess": "ai", "confidence": 0.8137, "model_score": 0.7544, "style_score": 0.7145, "marker_score": 0.9943, "status": "decided"}, "outcome": "ok", "duration_ms": 2248.7, "cpu_ms": 1583.8, "cold_start": true, "stages_ms": {"model": 2247.0, "style": 0.2, "markers": 0.2, "scoring": 0.0}}
```

Criterion 2. Produced by `run_capstone.py::criterion_2`. Each record it
quotes was written by `app.py::_write_run_record` through `runlog.py::write`.

```text
 1. GET /health -> 200  r_319de5bacbd3  ok
 2. POST /submit -> 200  r_ac7fb41ff53f  ok
 3. POST /submit -> 200  r_536e192607fc  ok
 4. POST /submit -> 200  r_b1978c40682b  ok
 5. POST /submit -> 200  r_f024ef0294ec  ok
 6. POST /submit -> 400  r_19068964b076  ok
 7. POST /submit -> 400  r_f12685745cf2  ok
 8. POST /appeal -> 200  r_17187aa1a9bc  ok
 9. POST /appeal -> 404  r_9e58a5832dea  ok
10. GET /submitt -> 404  r_5b1241aaba3f  FAIL: output has no error
    {"timestamp": "2026-11-12T02:36:36.724+00:00", "request_id": "r_5b1241aaba3f", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

Criterion 3. Produced by `run_capstone.py::criterion_3`. The 400s come from
`app.py::_check_submission`.

```text
missing text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.321+00:00", "request_id": "r_30562a1abb0d", "method": "POST", "path": "/submit", "input": {"body_bytes": 34, "body_type": "object", "fields": ["creator_id"], "creator_id": "c3_3133e8_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.7, "cpu_ms": 0.8, "cold_start": true}
empty text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.324+00:00", "request_id": "r_7be1819eca1e", "method": "POST", "path": "/submit", "input": {"body_bytes": 46, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1", "text_chars": 0, "text_words": 0, "text_preview": ""}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
whitespace-only text: -> 400 {"error": "bad_request", "message": "The \"text\" field is empty."}  ok
    {"timestamp": "2026-11-12T02:36:38.327+00:00", "request_id": "r_b66523e6f1d7", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1", "text_chars": 3, "text_words": 0, "text_preview": "   "}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
non-string text: -> 400 {"error": "bad_request", "message": "The \"text\" field is required and must be a string."}  ok
    {"timestamp": "2026-11-12T02:36:38.329+00:00", "request_id": "r_62545b7e8d07", "method": "POST", "path": "/submit", "input": {"body_bytes": 49, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c3_3133e8_trial1"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.3, "cpu_ms": 0.3, "cold_start": true}
JSON array: -> 400 {"error": "bad_request", "message": "Send a JSON object like {\"text\": \"...\", \"creator_id\": \"...\"}."}  ok
    {"timestamp": "2026-11-12T02:36:38.331+00:00", "request_id": "r_dd9f71e56ddc", "method": "POST", "path": "/submit", "input": {"body_bytes": 9, "body_type": "list"}, "output": {"status_code": 400, "error": "bad_request"}, "outcome": "rejected", "duration_ms": 0.2, "cpu_ms": 0.2, "cold_start": true}
```

Criterion 4. Produced by `run_capstone.py::criterion_4`. `duration_ms` is
measured in `app.py::_start_run_record` and `app.py::_build_run_record`.

```text
warm-up -> 200, duration_ms 2203.4, cold_start True
GET /health -> detector_loaded: True
 1. 86 words -> 200, duration_ms 47.8, within
    {"timestamp": "2026-11-12T02:36:41.446+00:00", "request_id": "r_e9d849ee0556", "method": "POST", "path": "/submit", "input": {"body_bytes": 549, "body_type": "object", "fields": ["creator_id", "text"], "creator_id": "c4_3133e8_t1_00", "text_chars": 494, "text_words": 86, "text_preview": "Few nations in the world share polarizing views among people"}, "output": {"status_code": 200, "content_id": "c_a1629da39dfd", "guess": "unsure", "confidence": 0.5259, "model_score": 0.5643, "style_score": 0.4874, "marker_score": 0.0, "status": "decided"}, "outcome": "ok", "duration_ms": 47.8, "cpu_ms": 66.3, "cold_start": false, "stages_ms": {"model": 46.1, "style": 0.1, "markers": 0.1, "scoring": 0.0}}
 2. 51 words -> 200, duration_ms 33.8, within
 3. 62 words -> 200, duration_ms 39.9, within
 4. 48 words -> 200, duration_ms 34.0, within
 5. 54 words -> 200, duration_ms 38.4, within
 6. 58 words -> 200, duration_ms 38.2, within
 7. 78 words -> 200, duration_ms 41.6, within
 8. 54 words -> 200, duration_ms 32.7, within
 9. 83 words -> 200, duration_ms 45.3, within
10. 42 words -> 200, duration_ms 32.1, within
```

Criterion 5. Produced by `run_capstone.py::criterion_5`. The appeal is
`app.py::appeal`, the audit entries are written by `audit.py::log_decision`
and `audit.py::log_appeal`, and the status read-back is `app.py::get_content`.

```text
POST /submit -> 200 {"content_id": "c_bb796c445be8", "guess": "unsure", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
POST /appeal -> 200 {"appealed_at": "2026-11-12T02:36:46+00:00", "content_id": "c_bb796c445be8", "message": "Thank you. Your appeal has been recorded and this piece is now marked a
    audit: {"combined_score": 0.5478, "content_id": "c_bb796c445be8", "creator_id": "c5_3133e8_t1", "guess": "unsure", "label": "We couldn't tell either way whether this was written by a person or an AI tool, so we're not making a call on it
    audit: {"content_id": "c_bb796c445be8", "creator_id": "c5_3133e8_t1", "event": "appeal", "reasoning": "I wrote this myself for a history class.", "status": "under_review", "timestamp": "2026-11-12T02:36:46+00:00"}
GET /content/c_bb796c445be8 -> 200 {"status": "under_review", "confidence": 0.5478, "model_score": 0.3913, "style_score": 0.7044}
```

Verdicts, each against the target in criteria.md:

1. **MET.** All three clean starts returned 200 with `"ok": true` from
   `GET /health` and 200 from `POST /submit`.
2. **MISSED.** The target is 10 of 10 requests in every session. Each session
   scored 9 of 10.
3. **MET.** All five invalid bodies returned 400 with a JSON `error` in every
   trial, none returned a 5xx, and each left one `rejected` record with status
   400, an error code and a duration.
4. **MET.** The target is at least 9 of 10 within 500 ms. All 30 requests were
   within it. The spread of `duration_ms` was trial 1: 32.1 to 47.8 ms; trial 2: 32.7 to 47.1 ms; trial 3: 35.0 to 49.8 ms, so the slowest
   request (49.8 ms) used about a tenth of the allowance.
5. **MET.** In every trial the appeal returned 200 with `under_review`, the
   audit log held the decision followed by the appeal, and
   `GET /content/<id>` showed the original scores and label with status
   `under_review`.

Diagnosis of the one miss, criterion 2.

The same request failed in all three sessions: request 10, `GET /submitt`,
the mistyped URL. Its record exists, matches its `X-Request-ID` exactly once
and has all eight required fields. What it lacks is the error code: its
`output` is `{"status_code": 404}` and nothing else, where the criterion
requires `output.error` on every 4xx.

The stage is the run log's summary of what went out:
`runlog.py::summarize_output`, called from `app.py::_write_run_record`.

The mechanism: `summarize_output` gets the error code by copying the `error`
field out of the response's JSON body. That works for every refusal my own
routes write, because they all answer with JSON like
`{"error": "bad_request", ...}`. A URL that matches no route never reaches
any of my routes. Flask answers it by itself with an HTML "Not Found" page,
`response.get_json(silent=True)` returns `None` for HTML, and there is no body
to copy an error code from.

Request 9 in the same session shows the difference. It is also a 404 (an
appeal against `c_doesnotexist`) and it passed, because that 404 is written by
`app.py::appeal` as JSON with `"error": "not_found"`. So the gap is in
responses Flask writes for me, and the status code alone does not predict it.
By the same code path a request with the wrong method (Flask's own 405) would
lose its error code too. I have not tested that.

The three sessions scored an identical 9 of 10 because nothing about this
failure involves the model or chance: the same URL takes the same path every
time. The request ids and timestamps differ in each session
(`r_5b1241aaba3f` in session 1), so the sessions were three separate runs.

There is one miss and one cause, so there is no wider pattern to report.

**The Improvement**

What I changed: one function, `runlog.py::summarize_output`, plus a small
helper beside it, `runlog.py::error_code_for`. When a response has status 400
or above and its body supplied no `error`, the run log now derives an error
code from the HTTP status (`404` becomes `not_found`, `405` becomes
`method_not_allowed`) and adds `"error_source": "http_status"` to mark the
code as derived. Nothing the service sends back to a caller changed.

Why this change: it is aimed at the mechanism in the diagnosis above.
Criterion 2 missed because `summarize_output` could only copy an error code
out of a JSON body, and the response Flask writes for an unknown URL is HTML.
The fix gives that function a second source for the code, so it no longer
depends on who wrote the response.

Then I re-ran the full set, three trials each, with the same command and
`--label after`. Full output: `results/capstone_2026-11-11_2144_after.md`.

Run Log, before (from `results/capstone_2026-11-11_2136_before.md`):

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible local run path | 2 of 2 checks (health, submit) per clean start | 2/2 | 2/2 | 2/2 | MET |
| 2. Complete structured run logging | 10 of 10 requests | 9/10 | 9/10 | 9/10 | MISSED |
| 3. Bad submission input is rejected and logged | 5 of 5 bodies | 5/5 | 5/5 | 5/5 | MET |
| 4. Warm submissions remain responsive | 9 of 10 within 500 ms | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeals preserve the original evidence | 4 of 4 checks | 4/4 | 4/4 | 4/4 | MET |

Run Log, after:

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible local run path | 2 of 2 checks (health, submit) per clean start | 2/2 | 2/2 | 2/2 | MET |
| 2. Complete structured run logging | 10 of 10 requests | 10/10 | 10/10 | 10/10 | MET |
| 3. Bad submission input is rejected and logged | 5 of 5 bodies | 5/5 | 5/5 | 5/5 | MET |
| 4. Warm submissions remain responsive | 9 of 10 within 500 ms | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeals preserve the original evidence | 4 of 4 checks | 4/4 | 4/4 | 4/4 | MET |

Request 10 of session 1, before:

```text
10. GET /submitt -> 404  r_5b1241aaba3f  FAIL: output has no error
    {"timestamp": "2026-11-12T02:36:36.724+00:00", "request_id": "r_5b1241aaba3f", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

Request 10 of session 1, after (the summary line from
`run_capstone.py::criterion_2`, then its record from `logs/runs.jsonl`):

```text
10. GET /submitt -> 404  r_53d8518017d4  ok
    {"timestamp": "2026-11-12T02:44:26.258+00:00", "request_id": "r_53d8518017d4", "method": "GET", "path": "/submitt", "input": {"body_bytes": 0, "body_type": "empty"}, "output": {"status_code": 404, "error": "not_found", "error_source": "http_status"}, "outcome": "rejected", "duration_ms": 0.1, "cpu_ms": 0.1, "cold_start": false}
```

Did it help: yes. Criterion 2 went from 9 of 10 in every session to 10 of 10
in every session, and the request that changed is the one the diagnosis
named. The record for `GET /submitt` now carries `"error": "not_found"`. The
other four criteria came out the same as before, so the change broke nothing
that I measure.

What it cost elsewhere:

- The derived code is generic. An unknown URL and an appeal against an
  unknown `content_id` now both log `"error": "not_found"`. They can still be
  told apart by `path` and by `error_source`, which is only present on the
  derived one, but a search of the log for `not_found` alone now returns both.
- Time: I can't show a cost, and I can't rule out a small one. Criterion 4's
  `duration_ms` over its 30 requests was 32.1 to 49.8 ms (mean 39.0) before
  and 33.4 to 83.4 ms (mean 42.3) after. The 83.4 ms is one request (trial
  1, request 9, 83 words); the next slowest after-run request took
  54.2 ms. For a 200 response the fix adds a single comparison, so I
  read the difference as run-to-run variation, but one run of each is not
  enough to prove that.
- The log is append-only, so the four unknown-URL records written before the
  fix stay as they were, without an error code.

What the after run does not show:

- Criterion 1's three clean starts cloned the last commit (`72aef9a`), and the
  fix was not committed yet when I ran it. Those clones ran the code from
  before the fix. Criterion 1 only checks `GET /health` and one `POST /submit`,
  which the fix does not touch.
- The 405 case is covered by a direct call only: `summarize_output(405, None)`
  returns `method_not_allowed`. I did not send a wrong-method request through
  the running service.
- `run_capstone.py` changed between the two runs in one place: the report's
  "Code tested" line now names any uncommitted `.py` files. No check changed.

**Stretch: Latency Breakdown**

Where the time goes inside one scored request, measured from the `stages_ms`
field that `app.py::_score_text` writes into every run record. Produced by
`python runlog.py --stages` (`runlog.py::stage_breakdown`) over every warm
scored request in `logs/runs.jsonl` up to that point, before the load test
below was run. Saved in `results/latency_breakdown_2026-11-11.md`.

Warm scored requests: 111   mean total: 40.13 ms

| Stage | Mean ms | Share of the request |
|---|---|---|
| gpt2 perplexity (detector.py) | 38.53 | 96.0% |
| style measures (stylometry.py) | 0.11 | 0.3% |
| stock-phrase search (markers.py) | 0.11 | 0.3% |
| combine and label (scoring.py) | 0.00 | 0.0% |
| everything else (checks, audit write, response) | 1.39 | 3.5% |
| **whole request** | 40.13 | 100.0% |

Cold starts: 7   mean total: 2265.4 ms, of which the model stage (load + first pass): 2263.4 ms (99.9%)

The gpt2 pass dominates: 96.0% of a warm request, and 99.9% of a cold start,
where it also includes loading the model. My own code (the style measures, the
stock-phrase search and the scoring rule) adds up to 0.22 ms, about half a
percent. Checking the input, writing the audit entry and building the response
take 1.39 ms together. So the only change that could make a request noticeably
faster is one to the model stage, such as reading fewer than 400 tokens.

**Stretch: Load Observation**

The service at a normal rate and at ten times that rate. Produced by
`python load_test.py --save` against the service started from RUNNING.md, and
saved in `results/load_2026-11-11_2150.md`. "Normal" is 2 submissions a
second, which is already 120 a minute. Ten times that, 20 a second, was chosen
to sit near what one worker can do at about 40 ms a request (1000 / 40 = 25 a
second). Requests are sent when they are due, without waiting for earlier
answers, each from its own `creator_id` so the rate limiter is not what gets
measured.

```text
Load observation, 2026-11-11T21:50:40-05:00
Service: http://127.0.0.1:5000   each phase: 15 s   run tag: 65a750

| Measure | Normal (2 a second) | Ten times (20 a second) |
|---|---|---|
| Requests sent | 30 | 300 |
| Responses by status | 200: 30 | 200: 300 |
| Found in the run log | 30 of 30 | 300 of 300 |
| Client latency ms, median / 95th / max | 56.4 / 69.4 / 70.8 | 38.3 / 51.3 / 86.3 |
| Service time ms, median / 95th / max | 53.6 / 66.8 / 68.7 | 36.4 / 47.7 / 76.3 |
| CPU ms per request, mean | 71.1 | 49.6 |
| Seconds until every answer was in | 14.6 | 15.0 |
| Answers per second achieved | 2.1 | 20.0 |
```

What changed, and what did not:

- Nothing failed. At 20 a second all 300 requests returned 200, all 300 are in
  the run log, and the service answered as fast as requests arrived (20.0 a
  second).
- Queueing was small. The slowest caller waited 86.3 ms at 20 a second against
  70.8 ms at 2 a second. At 20 a second the worker is busy about 73% of the
  time (20 x 36.4 ms = 728 ms of work each second), so most requests found it
  free.
- Each request got cheaper under load, which I did not expect. Median service
  time fell from 53.6 ms to 36.4 ms, and CPU per request from 71.1 ms to
  49.6 ms. My best explanation is that at 2 a second the process sits idle for
  about 450 ms between requests and each one starts from a slowed-down
  processor, while at 20 a second it never goes idle. I have not confirmed
  that.

That last point matters for What It Costs. I measured the 50.1 ms per run with
requests sent back to back, which matches the 49.6 ms seen here under load. A
hundred people a day arrive with long idle gaps, which is the 2-a-second
situation or slower, so the per-run cost there is more likely near 71.1 ms:
100 x 71.1 ms = 7.1 seconds of CPU a day, where I had worked out 5.0. Both are
far below anything that would limit the service.

I did not test above 20 a second. By the arithmetic, one worker runs out of
room at about 1000 / 36.4 = 27 a second, and past that requests would queue.

**What's Still Broken**

After the improvement all five criteria are met in all three trials, so no
criterion is still missed. That tells me at least one target was set too low.

The target I would tighten is criterion 4. It allows 500 ms, and across the
before and after runs the slowest of 60 warm requests took 83.4 ms, with a
mean near 40 ms. A target that sits six times above the worst case seen cannot
detect anything short of the model being reloaded. I would tighten it to: at
least 9 of 10 within 100 ms. That is about two and a half times the mean, and
the 83.4 ms request shows it could be missed on a busier or slower machine,
which is what makes it a real test.

Criterion 1 is the other soft one. It passed from a clone of my local folder
with gpt2 already in the Hugging Face cache, so the 525 MB download and the
GitHub clone were never exercised. A stricter version would clone the GitHub
URL with an empty model cache each time.

Things that are still wrong and that no criterion of mine measures:

- A request can succeed without leaving a run record. If the log cannot be
  written, `app.py::_write_run_record` catches the error so the caller still
  gets an answer. I checked this by pointing the log at a folder that does not
  exist: `POST /ping` returned 200 with an `X-Request-ID` header, and that id
  matched no record. The only trace was one line on the server's terminal.
- The unit 8 problem is untouched: the rate limiter still answers before the
  route does, so a malformed request from a caller over the limit gets a 429
  where it should get a 400. I ruled that out of scope in The Shape.
- The service runs one worker, and I have not tested past 20 requests a
  second.
- Since writing The Improvement I did send a wrong-method request through the
  running service: `GET /submit` returned 405 and its record carries
  `"error": "method_not_allowed"`. That case is now covered once, by hand,
  and is not part of any criterion.

Why I stopped: the unit allows one improvement, each further change needs its
own before and after run to mean anything, and every criterion I had written
was met.

The one thing I would do first with another unit: make a failed log write
visible, by counting failures and reporting the count in `GET /health`. I
would do that before tightening any target, because the whole claim of this
extension is that every request leaves a record, and this is the one case I
know of where it silently does not.

**How I Used AI**

I used Claude Code for most of the building in this unit. It wrote the
instrumentation (`runlog.py` and the hooks in `app.py`), the three scripts
(`measure_cost.py`, `run_capstone.py`, `load_test.py`), and the first drafts
of these capstone sections, filling in the tables and log lines from the saved
result files. It recommended Shape A and the out-of-scope list, and I agreed
to them. Two moments where what I asked for and what I did with the answer
are worth spelling out:

1. Choosing the system. I gave it the unit brief, the rubric and all four of
   my repositories and asked which one would be best for the local run path.
   It recommended Provenance Guard and gave reasons I could check: its
   `test.py` passed 9 of 9 that day, it needs no API key (so thirty trials
   would not run into the Gemini rate limits that projects 1 and 2 have retry
   code for), and it already wrote an audit log. It also pointed out that I
   had mixed up the run path "B" with the shape "B", which are different
   choices. I went with Provenance Guard.

2. Reviewing my criteria. I wrote five criteria and asked how they were. It
   did not rewrite them. It listed where a stranger would test them
   differently from me: criterion 2 did not say which ten requests to send,
   and whether it passed depended on whether a mistyped URL was among them;
   criteria 3 and 4 depended on which `creator_id` was used, because of the
   rate limiter; and criterion 4's 5-second target could not fail when warm
   requests took 29 to 53 ms. I then asked for help closing those gaps. It
   proposed additions and I took them: the ten requests named in order with
   the mistyped URL included, a fresh `creator_id` per trial, 500 ms read
   from `duration_ms` in place of 5 seconds, and my own ten paragraphs in
   place of "100 to 400 words". The mistyped URL is the request that made
   criterion 2 miss, so that review is where this unit's one diagnosis and
   improvement came from.

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
