"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

Working that out is Milestone 3's first step, and this file is where you write
it down. `run_eval.py` runs everything here three times.

Two are filled in as examples. Replace them with what your criteria actually
need — these are a shape, not a set.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.
"""

# ── My scenarios, one or more per criterion in criteria.md ──────────────────
#
# run_eval.py sends every body in a scenario three times (three trials) and
# saves what came back to results/run_<date>_<label>.md.
#
# Two pieces of criteria 4 and 5 can't be expressed here, so they're tested
# elsewhere and the README says so:
#   - Criterion 4 (appeals) needs a submission, then an appeal against the
#     content_id that came back: run_appeals.py does that.
#   - Criterion 5's seventh body is a JSON list, and validate() below only
#     accepts dict bodies, so that one is sent by hand with curl.

# The two calibration samples, read from samples/ so the scenarios always test
# exactly the files the criteria name.
import json as _json
from pathlib import Path as _Path

_SAMPLES = _Path(__file__).parent / "samples"


def _sample(name: str) -> str:
    return _json.loads((_SAMPLES / f"{name}.json").read_text(encoding="utf-8"))["text"]


# Criterion 1: ten paragraphs I wrote myself, pasted exactly as written
# (spelling and curly quotes included). Each is over the 40-word minimum.
MY_OWN_WRITING = [
    "Few nations in the world share polarizing views among people in the world, Iran is viewed by many in the West as Anti-Western with its rhetoric on the destruction of Israel and its nuclear program, while others view Iran as the land that brought so much culture with the poems of Rumi and Hafez and its ancient history. In the non-Western nations Iran is considered by many to be the “standing force” against the USA and Imperialist nations, particularly when it comes to Palestine and Lebanon.",
    "Pakistan is considered by many in the West as two-faced, claiming that the they actively support USA/NATO’s War on Terror however only a few months ago the former most wanted terrorist in the world, Osama Bin Laden, was found in a million dollar fortress near the primary military academy in Abbottabad.",
    "Others on the other hand see Pakistan as a land filled with vast culture, art and its people considered to be trustworthy and warm hearted. With all this in mind it is almost no surprise that Iran, and to a lesser extent Pakistan, are viewed as nations where the rhetoric of their respective governments are different than the views of the people.",
    "The relations of these two nations are strained and tense, with their own self-interests conflicting other nation’s interests, which sometimes spill to other nations, particularly the nation of Afghanistan. It is no surprise to see the relations between these two nations as, at its best, complicated and uneasy.",
    "The histories of both nations have always been tied together, from Ancient times both nations have been closely linked. Even up to 1979, the Pahlavi Dynasty, there was were close ties between the two nations, with Iran being the first nation to recognize the independence of Pakistan and co-creating the Central Treaty Organization (CENTO).",
    "However after the 1979 Iranian Revolution, with the Iranian Monarchy replaced by the Islamic Republic, both nations aimed to prioritize their own self-interests over the consideration of others. During the 1990s the Iranian regime openly supported Afghanistan’s Northern Alliance, whereas Pakistan opened links with the Taliban, which caused a rift and dominated the relations between the two nations.",
    "After 2001, with the fall of the Taliban, through proxy groups, Iran and Pakistan supported opposing groups, a measure intended for each of their nations to spread their own influences. However this is not limited to Afghanistan, even now Iran is accused of supporting Shiite paramilitary groups in Pakistan, where Pakistan is accused of supporting Sunni paramilitary groups in South East Iran, the most infamous attack being the 2009 mosque bombing in Zahedan, close to the Pakistani border.",
    "With all this in mind one should consider the other side in this relationship, there are current talks to establish a pipeline between Iran and Pakistan, with somewhat limited success in the actual implementation, and there are current talks between the two nations to stabilize relations in the region, including in terms of Afghanistan.",
    "It must also be stressed that, as cold as it sounds, a nation should prioritize their own self-interests before the interests of others. In one hand Iran is looking to spread their own influence by supporting groups within the region, in particular Palestine and Lebanon. With a nation that has been under the reign of the Macedonians, the Arabs, the Mongolians, the Russians, the British and to a lesser extent the Americans, Iran now aims to spread their own influence in the regions.",
    "Even now Iran think of themselves as surrounded by their enemies, the Arabs to the West and South, their “conquers” and the Russians to the North, the nation that took much land from Iran and on many attempts attempted to colonize Iran.",
]

SCENARIOS = [
    {
        # Criterion 1: at most 2 of 10 get "guess": "ai", in every trial.
        "name": "my own writing",
        "criterion": 1,
        "texts": MY_OWN_WRITING,
    },
    {
        # Criterion 2: clearly_ai's confidence is at least 0.30 above
        # clearly_human's, in every trial. Order matters: AI first, human second.
        "name": "spread ai vs human",
        "criterion": 2,
        "texts": [_sample("clearly_ai"), _sample("clearly_human")],
    },
    {
        # Criterion 3: ai, unsure, human, in that order, in every trial.
        "name": "label coverage",
        "criterion": 3,
        "texts": [_sample("clearly_ai"), _sample("borderline"), _sample("clearly_human")],
    },
    {
        # Criterion 5: six of the seven malformed bodies (the JSON list is sent
        # by hand). Each must return 400, never 500, and log a rejection.
        "name": "bad input",
        "criterion": 5,
        "bodies": [
            {"text": "", "creator_id": "eval_bad_empty"},
            {"creator_id": "eval_bad_missing"},
            {"text": None, "creator_id": "eval_bad_null"},
            {"text": " ".join(["word"] * 39), "creator_id": "eval_bad_short"},
            # "word " is 5 characters; 2,000 of them is 10,000, plus "x" = 10,001.
            {"text": "word " * 2000 + "x", "creator_id": "eval_bad_huge"},
            {"text": _sample("clearly_human")},  # creator_id missing, text valid
        ],
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
