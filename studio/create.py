"""Guided creation flow — the actionable half of the product.

Step 1 (generate_hooks): 10 hooks built from the creator's MEASURED formula
(hook patterns + metrics) and the verified facts from the research stage.
Step 2 (generate_copy): the user picks one hook; the full video copy is
orchestrated around it — ~200–250 spoken words (~90–120s videos), the creator's
copy structure, measured editing directions, and explicit data-honesty notes.

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
from .script_format import normalize_script

logger = logging.getLogger(__name__)

# Target a full short-form monologue (~90–120s at ~140–160 WPM), not a 30s teaser.
MIN_SPOKEN_WORDS = 200
TARGET_SPOKEN_WORDS = 225
MAX_COPY_WORDS = 260
MIN_SCRIPT_BLOCKS = 8


class Hook(BaseModel):
    text: str = Field(description="The hook, ready for the first 3 seconds")
    pattern: str = Field(description="Which of the creator's hook patterns this follows")


class HookList(BaseModel):
    hooks: list[Hook] = Field(description="Exactly 10 hooks")


class VideoCopy(BaseModel):
    script: str = Field(
        description="Shooting script with timeline. Each block shows: [TIMESTAMP] | [SHOT TYPE] | "
        '[TEXT TO SAY] | [CUT/TRANSITION] | [WHY IT WORKS — psychology or editing reason]. '
        f"Spoken TEXT fields alone must total {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} words "
        f"(target ~{TARGET_SPOKEN_WORDS}). Minimum {MIN_SCRIPT_BLOCKS} blocks. "
        "COMPLETE narration — not just the opening hook."
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

EXAMPLE (abbreviated — your output must be LONGER, ~{TARGET_SPOKEN_WORDS} spoken words total):
```
0:00-0:05 | CLOSE-UP face | "You think you can survive on only meat?" | Jump cut, bold text overlay | Shock question — breaks viewer's assumption
0:05-0:15 | MEDIUM shot | "I tried a full carnivore reset for thirty days and tracked energy, sleep, and digestion every morning." | Slow zoom in | Personal proof — curiosity + authority
0:15-0:28 | B-ROLL (meal prep) | "Breakfast was eggs and ribeye. Lunch was ground beef. Dinner was salmon when I needed variety — still zero plants." | Cut every ~2s, text: "DAY 1" | Concrete detail makes the claim believable
0:28-0:45 | MEDIUM shot | "By week two my afternoon crash was gone. Focus felt sharper. But I also watched for red flags: fiber loss, electrolyte dips, lipid panels." | Pattern interrupt on risks | Honesty builds trust before the CTA
```

RULES:
- CRITICAL: Do NOT use line breaks (newlines) inside a single block. Each timestamp block must be exactly one line.
- Output AT LEAST {MIN_SCRIPT_BLOCKS} separate lines (blocks), ideally 8–12, covering ~0:00 to ~1:30–2:00.
- HARD LENGTH TARGET: spoken words in TEXT fields MUST be between {MIN_SPOKEN_WORDS} and {MAX_COPY_WORDS}.
  Aim for ~{TARGET_SPOKEN_WORDS}. Scripts under {MIN_SPOKEN_WORDS} spoken words are INVALID — expand with
  steps, proof, caveats, and a clear close (do NOT pad with filler words only).
- COMPLETE NARRATION arc: hook → context → 3–5 concrete points/steps → risks or nuance → takeaway/CTA.
  The chosen hook is ONLY the first spoken line — you MUST continue with substantial dialogue.
- At most ONE block may use "(no speech — music only)". Almost every block needs real dialogue (1–3 sentences each).
- Every block MUST include all 5 fields separated by `|`: timestamp, shot, text, editing, psychology.
- SHOT TYPES must match the creator's measured grammar (e.g. "CLOSE-UP face",
  "MEDIUM shot", "SPLIT-SCREEN", "B-ROLL", "TEXT OVERLAY").
- EDITING must use MEASURED NUMBERS: cut cadence (~X cuts/min, every ~Y seconds),
  specific transitions (jump cut, zoom, text pop-in). Never vague.
- WHY IT WORKS must explain the retention psychology or editing principle.
  Use terms like: pattern interrupt, curiosity gap, social proof, authority,
  dopamine loop, visual anchor, pacing rhythm, contrast, payoff.
- Never put the next timestamp inside the WHY field — start a NEW line instead.
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
    # Slim profile for the prompt — huge per_video metric dumps slow watsonx and bloat tokens
    slim = profile_obj.model_dump()
    if isinstance(slim.get("metrics"), dict):
        m = slim["metrics"]
        editing = m.get("editing") or {}
        speech = m.get("speech") or {}
        slim["metrics"] = {
            "editing": {
                "avg_cuts_per_min": editing.get("avg_cuts_per_min"),
                "avg_shot_length_s": editing.get("avg_shot_length_s"),
                "videos_measured": editing.get("videos_measured"),
            },
            "speech": {"avg_wpm": speech.get("avg_wpm")},
            "signature_ngrams": (m.get("signature_ngrams") or [])[:8],
        }
    # Drop heavy frame-level thumbnail noise if present
    if isinstance(slim.get("thumbnail"), dict):
        th = slim["thumbnail"]
        slim["thumbnail"] = {
            "score": th.get("score"),
            "composition": th.get("composition"),
            "suggestions": (th.get("suggestions") or [])[:3],
        }

    logger.info("Generating 10 hooks from '%s' for '%s'...", creator, theme)
    response = agent.run(
        f"USER'S THEME (the hooks MUST be about this topic): {theme}\n\n"
        f"Creator profile (measured evidence — JSON):\n{__import__('json').dumps(slim, ensure_ascii=False, indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f"Generate exactly 10 hooks. Every single hook MUST reference the user's theme: '{theme}'. "
        "Apply the creator's patterns to THIS theme — do NOT use the creator's original topic. "
        "Return structured JSON only — be concise."
    )
    return coerce_structured(response.content, HookList, stage="Hook generation")


def generate_copy(
    creator: str, theme: str, chosen_hook: str, *, research: ResearchReport | None = None, profile: dict | None = None
) -> VideoCopy:
    """Step 2: full orchestrated copy (~200–250 spoken words) around the user's chosen hook."""
    if profile is not None:
        profile_obj = store.CreatorProfile.model_validate(profile)
    else:
        profile_obj = _profile_or_raise(creator)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"copy_director_{creator}",
        description="Scriptwriter and director of short videos — full 90–120s monologue based on measured data.",
        instructions=COPY_INSTRUCTIONS,
        output_schema=VideoCopy,
    )
    logger.info("Generating copy for '%s' x '%s' with the chosen hook...", creator, theme)

    base_prompt = (
        f"CREATOR PROFILE (measured evidence — JSON):\n{profile_obj.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f"USER THEME: {theme}\n"
        f'CHOSEN HOOK: "{chosen_hook}"\n\n'
        "Generate the COMPLETE SHOOTING SCRIPT for a 90–120 SECOND video (not a 30s teaser).\n"
        f"- Minimum {MIN_SCRIPT_BLOCKS} lines (blocks), ideally 8–12, each EXACTLY ONE LINE with 4 pipes:\n"
        "  [TIMESTAMP] | [SHOT] | [TEXT] | [EDITING] | [WHY IT WORKS]\n"
        f"- HARD REQUIREMENT: spoken TEXT fields MUST total {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} words "
        f"(target ~{TARGET_SPOKEN_WORDS}). Count only words the host says out loud.\n"
        f'- Line 1 TEXT must be the chosen hook: "{chosen_hook}"\n'
        "- Lines 2+ MUST continue with NEW spoken sentences: context, 3–5 concrete points/steps, "
        "risks or nuance, and a clear close/CTA.\n"
        "- Each speaking block should have 1–3 full sentences (not three-word fragments).\n"
        "- DO NOT put timestamps inside the WHY field; each new moment is a new line.\n"
        "Use the creator's measured cuts/min, shot types, and editing grammar from the profile."
    )
    response = agent.run(base_prompt)
    copy = coerce_structured(response.content, VideoCopy, stage="Copy generation")
    copy = _normalize_video_copy(copy)

    # One expansion pass if the model under-wrote (common with short hooks / thin profiles)
    spoken_n = normalize_script(copy.script).spoken_word_count
    if spoken_n < MIN_SPOKEN_WORDS:
        logger.warning(
            "Copy only %d spoken words (min %d) — requesting expansion pass...",
            spoken_n,
            MIN_SPOKEN_WORDS,
        )
        expand = agent.run(
            f"{base_prompt}\n\n"
            f"YOUR PREVIOUS SCRIPT WAS TOO SHORT ({spoken_n} spoken words). "
            f"Rewrite a LONGER version with AT LEAST {MIN_SPOKEN_WORDS} spoken words "
            f"(target {TARGET_SPOKEN_WORDS}). Keep the same hook as line 1. "
            "Add more spoken blocks with real sentences — steps, examples, caveats, close. "
            "Still use the pipe format, one block per line."
        )
        try:
            expanded = coerce_structured(expand.content, VideoCopy, stage="Copy expansion")
            expanded = _normalize_video_copy(expanded)
            if normalize_script(expanded.script).spoken_word_count >= spoken_n:
                copy = expanded
        except Exception:
            logger.exception("Copy expansion pass failed — keeping first draft")

    return copy


def _normalize_video_copy(copy: VideoCopy) -> VideoCopy:
    """Repair pipe-format drift so API consumers always get a full multi-block script."""
    normalized = normalize_script(copy.script)
    if not normalized.blocks:
        logger.warning("Copy normalization found 0 blocks — returning raw script")
        return copy

    repaired_script = normalized.script
    if normalized.was_repaired:
        logger.info(
            "Copy script repaired: %d blocks, %d spoken words (was_repaired=True)",
            len(normalized.blocks),
            normalized.spoken_word_count,
        )

    # Keep model editing_directions if rich enough; otherwise synthesize from blocks
    directions = list(copy.editing_directions or [])
    if len(directions) < max(3, len(normalized.blocks) // 2):
        directions = [
            f"{b.timestamp}: {b.editing}".strip(": ")
            for b in normalized.blocks
            if b.editing
        ] or directions

    return VideoCopy(
        script=repaired_script,
        editing_directions=directions,
        data_notes=copy.data_notes,
    )


def copy_payload(copy: VideoCopy) -> dict:
    """API-ready dict with structured blocks + spoken narration for the frontend."""
    normalized = normalize_script(copy.script)
    spoken = normalized.spoken_copy
    word_count = normalized.spoken_word_count or len((copy.script or "").split())
    return {
        "script": normalized.script or copy.script,
        "spoken_copy": spoken,
        "blocks": [
            {
                "timestamp": b.timestamp,
                "shot": b.shot,
                "text": b.text,
                "editing": b.editing,
                "why": b.why,
            }
            for b in normalized.blocks
        ],
        "editing_directions": copy.editing_directions,
        "data_notes": copy.data_notes,
        "word_count": word_count,
        "format_repaired": normalized.was_repaired,
        "block_count": len(normalized.blocks),
    }
