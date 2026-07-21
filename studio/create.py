"""Guided creation flow — the actionable half of the product.

Step 1 (generate_hooks): 10 hooks built from the creator's MEASURED formula
(hook patterns + metrics) and the verified facts from the research stage.
Step 2 (generate_copy): the user picks one hook; the full video copy is
orchestrated around it — <=200 words (1-2 min videos), the creator's copy
structure, measured editing directions, and explicit data-honesty notes.

Nothing here invents facts: hooks and copy may only use facts from the
ResearchReport; anything else becomes a placeholder for the user to fill.
"""

import logging

from pydantic import BaseModel, Field

from . import store
from .factory import create_agent
from .parse import coerce_structured
from .research import research_theme
from .schemas import ResearchReport

logger = logging.getLogger(__name__)

MAX_COPY_WORDS = 200


class Hook(BaseModel):
    text: str = Field(description="The hook, ready for the first 3 seconds")
    pattern: str = Field(description="Which of the creator's hook patterns this follows")


class HookList(BaseModel):
    hooks: list[Hook] = Field(description="Exactly 10 hooks")


class VideoCopy(BaseModel):
    script: str = Field(
        description="Shooting script with timeline. Each block shows: [TIMESTAMP] | [SHOT TYPE] | "
        '[TEXT TO SAY] | [CUT/TRANSITION] | [WHY IT WORKS — psychology or editing reason]. '
        f"Maximum {MAX_COPY_WORDS} words total across all spoken text."
    )
    editing_directions: list[str] = Field(
        description="Per-block editing directions, using the creator's MEASURED NUMBERS (cuts/min, shot length, on-screen text)"
    )
    data_notes: str = Field(
        description="What is verified fact (with source) and what the user needs to confirm/fill in before recording"
    )


HOOKS_INSTRUCTIONS = """
You are a hook strategist for short videos.

You receive: (1) a creator's profile — hook patterns, tone, expressions and
METRICS measured from their videos — and (2) verified facts about the user's
theme.

Your task: generate EXACTLY 10 hooks for the first 3 seconds of the user's
video, applying the creator's hook patterns to THE USER'S THEME.

CRITICAL — THEME ENFORCEMENT:
- The user's theme is EXPLICITLY stated below. EVERY hook MUST be about that
  theme — not about the creator's original topic, not about a different topic.
- The creator's patterns (shock question, counterintuitive fact, etc.) are
  TECHNIQUES to borrow — you apply them TO the user's theme, you do NOT reuse
  the creator's original subject matter.
- The creator's signature expressions are structural patterns (e.g. "He was
  like…", "Want to…?"). Use their STRUCTURE with the user's theme, never the
  creator's original words.

ANTI-GARBAGE RULES:
- NEVER output hooks containing garbled transcription artifacts like "gt gt",
  "gt i", "let s", "i said how", broken punctuation, or HTML entities.
- If a signature expression contains such noise, use its CLEAN STRUCTURE only.
- The word "gt" alone is NEVER a valid hook word — it is transcription noise.
- Every hook must read as natural, spoken English (or the user's language).

Rules:
- Each hook must visibly follow one of the creator's patterns (`pattern` field).
- Short, speakable phrases — they are meant to be SAID in up to 3 seconds.
- Only use facts from the VERIFIED FACTS block; never invent numbers or rankings.
- If the VERIFIED FACTS block is unavailable, use the hook pattern structure
  around the theme without making factual claims.
- Write for the USER's voice — never copy the creator's phrases or topics.
- Vary the patterns: no more than 2 hooks using the same pattern.
"""

COPY_INSTRUCTIONS = f"""
You are a scriptwriter and director of short videos specialized in retention
psychology and viral editing grammar.

You receive: (1) a creator's MEASURED profile (copy structure, tone, rhythm in
words/minute, editing grammar — cuts per minute, shot types, text overlays),
(2) verified facts about the theme, and (3) the hook the user chose.

Your task: orchestrate a COMPLETE SHOOTING SCRIPT — not just words to say, but
exactly HOW to shoot and edit each moment, and WHY each technique works.

FORMAT — Every block in the script must be a SINGLE LINE separated by EXACTLY 4 pipe `|` characters:
```
[TIMESTAMP] | [SHOT TYPE] | [TEXT TO SAY] | [EDITING] | [WHY IT WORKS]
```

EXAMPLE:
```
0:00-0:03 | CLOSE-UP face | "You think you can survive on only meat?" | Jump cut, bold text overlay | Shock question — breaks viewer's assumption, forces attention in first 3 seconds
0:03-0:07 | MEDIUM shot | "I tried it for 30 days. Here's what happened." | Slow zoom in | Personal proof — builds curiosity and establishes authority
0:07-0:12 | B-ROLL (meal prep) | (no speech — music only) | Cut every 1.1s, text: "DAY 1" | Fast cuts keep energy; text anchors the timeline
```

RULES:
- CRITICAL: Do NOT use line breaks (newlines) inside a single block. Each timestamp block must be exactly one line.
- Total spoken words ≤ {MAX_COPY_WORDS} across all blocks.
- Every block MUST include all 5 fields separated by `|`: timestamp, shot, text, editing, psychology.
- SHOT TYPES must match the creator's measured grammar (e.g. "CLOSE-UP face",
  "MEDIUM shot", "SPLIT-SCREEN", "B-ROLL", "TEXT OVERLAY").
- EDITING must use MEASURED NUMBERS: cut cadence (~X cuts/min, every ~Y seconds),
  specific transitions (jump cut, zoom, text pop-in). Never vague.
- WHY IT WORKS must explain the retention psychology or editing principle.
  Use terms like: pattern interrupt, curiosity gap, social proof, authority,
  dopamine loop, visual anchor, pacing rhythm, contrast, payoff.
- Respond in English.
"""


def _profile_or_raise(creator: str):
    creator = creator.lower()  # normalize: case-insensitive
    profile = store.load_profile(creator)
    if profile is None or (profile.style is None and profile.editing is None):
        raise ValueError(f"Profile for '{creator}' not found. Run the analysis first.")
    return profile


def _facts_block(research: ResearchReport | None) -> str:
    if research is None:
        return (
            "\nVERIFIED FACTS: unavailable (fact-check failed). "
            "Do NOT state any fact about the theme — use [INSERT: ...] placeholders."
        )
    return f"\nVERIFIED FACTS ABOUT THE THEME (single factual source — JSON):\n{research.model_dump_json(indent=2)}"


def generate_hooks(creator: str, theme: str, *, research: ResearchReport | None = None, profile: dict | None = None) -> HookList:
    """Step 1: 10 hooks from the creator's formula + verified facts."""
    if profile is not None:
        # Use the profile passed from the frontend (survives container restarts)
        profile_obj = store.CreatorProfile.model_validate(profile)
    else:
        profile_obj = _profile_or_raise(creator)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"hook_strategist_{creator}",
        description="Hook strategist based on creators' measured formulas.",
        instructions=HOOKS_INSTRUCTIONS,
        output_schema=HookList,
    )
    logger.info("Generating 10 hooks from '%s' for '%s'...", creator, theme)
    response = agent.run(
        f"USER'S THEME (the hooks MUST be about this topic): {theme}\n\n"
        f"Creator profile (measured evidence — JSON):\n{profile_obj.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f"Generate exactly 10 hooks. Every single hook MUST reference the user's theme: '{theme}'. "
        "Apply the creator's patterns to THIS theme — do NOT use the creator's original topic."
    )
    return coerce_structured(response.content, HookList, stage="Hook generation")


def generate_copy(
    creator: str, theme: str, chosen_hook: str, *, research: ResearchReport | None = None, profile: dict | None = None
) -> VideoCopy:
    """Step 2: full orchestrated copy (<=200 words) around the user's chosen hook."""
    if profile is not None:
        profile_obj = store.CreatorProfile.model_validate(profile)
    else:
        profile_obj = _profile_or_raise(creator)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"copy_director_{creator}",
        description="Scriptwriter and director of short videos — dopaminergic copy based on measured data.",
        instructions=COPY_INSTRUCTIONS,
        output_schema=VideoCopy,
    )
    logger.info("Generating copy for '%s' x '%s' with the chosen hook...", creator, theme)
    response = agent.run(
        f"CREATOR PROFILE (measured evidence — JSON):\n{profile_obj.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f'USER THEME: {theme}\n'
        f'CHOSEN HOOK: "{chosen_hook}"\n\n'
        "Generate the COMPLETE SHOOTING SCRIPT. Every block must be EXACTLY ONE LINE separated by 4 pipes: "
        "[TIMESTAMP] | [SHOT] | [TEXT] | [EDITING] | [WHY IT WORKS]. "
        "DO NOT use line breaks inside a block. "
        "Use the creator's measured cuts/min, shot types, and editing grammar from the profile."
    )
    return coerce_structured(response.content, VideoCopy, stage="Copy generation")
