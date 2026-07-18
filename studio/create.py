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
        description="Complete copy in markdown with [HOOK] / [DEVELOPMENT] / [CLOSING] blocks, "
        f"maximum {MAX_COPY_WORDS} words in total"
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
You are a scriptwriter and director of short videos specialized in retention.

You receive: (1) a creator's MEASURED profile (copy structure, tone, rhythm in
words/minute, editing grammar), (2) verified facts about the theme, and
(3) the hook the user chose.

Your task: orchestrate the user's complete video around that hook.

Structure rules:
- The script has AT MOST {MAX_COPY_WORDS} words (~1 minute video at the
  creator's measured rhythm). Blocks: [HOOK] (the chosen one, word for word),
  [DEVELOPMENT] (the creator's copy structure applied to the theme),
  [CLOSING] (result + CTA compatible with their style).
- Dopaminergic structure: each sentence must justify the next; no filler.
- Only use facts from the VERIFIED FACTS block. Where data is missing, leave a
  clear [INSERT: ...] placeholder instead of inventing — and list those points
  in data_notes.
- editing_directions: use the MEASURED NUMBERS (e.g. "cut every ~3.1s",
  "on-screen text at the bottom highlighting the number") — never vague
  direction.
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
        f"Creator profile (measured evidence — JSON):\n{profile_obj.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f'User\'s theme: {theme}\nHook chosen by the user: "{chosen_hook}"\n\n'
        "Orchestrate the complete video."
    )
    return coerce_structured(response.content, VideoCopy, stage="Copy generation")
