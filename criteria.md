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
