"""Guided creation flow — the actionable half of the product.

Step 1 (generate_hooks): 10 hooks built from the creator's MEASURED formula
(hook patterns + metrics) and the verified facts from the research stage.
Step 2 (generate_copy): the user picks one hook; the full video copy is
orchestrated around it — ~170–200 spoken words (~60–90s shorts), the creator's
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

# Short-form monologue for ~60–90s at ~140–160 WPM (not 2+ minute scripts).
MIN_SPOKEN_WORDS = 150
TARGET_SPOKEN_WORDS = 185
MAX_COPY_WORDS = 200
MIN_SCRIPT_BLOCKS = 6


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
- Output AT LEAST {MIN_SCRIPT_BLOCKS} separate lines (blocks), ideally 6–9, covering ~0:00 to ~1:00–1:30 max.
- HARD LENGTH TARGET: spoken words in TEXT fields MUST be between {MIN_SPOKEN_WORDS} and {MAX_COPY_WORDS}.
  Aim for ~{TARGET_SPOKEN_WORDS}. NEVER exceed {MAX_COPY_WORDS} spoken words — keep it a short, not a 2-minute lecture.
- COMPLETE NARRATION arc: hook → context → 2–4 concrete points → quick caveat → takeaway/CTA.
  The chosen hook is ONLY the first spoken line — continue with real dialogue, stay tight.
- At most ONE block may use "(no speech — music only)". Almost every block needs real dialogue (1–2 sentences each).
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


def _slim_profile_json(profile_obj) -> str:
    """Drop heavy per_video dumps so the model spends tokens on spoken copy."""
    import json

    slim = profile_obj.model_dump()
    if isinstance(slim.get("metrics"), dict):
        m = slim["metrics"]
        editing = m.get("editing") or {}
        speech = m.get("speech") or {}
        slim["metrics"] = {
            "editing": {
                "avg_cuts_per_min": editing.get("avg_cuts_per_min"),
                "avg_shot_length_s": editing.get("avg_shot_length_s"),
            },
            "speech": {"avg_wpm": speech.get("avg_wpm")},
            "signature_ngrams": (m.get("signature_ngrams") or [])[:6],
        }
    if isinstance(slim.get("thumbnail"), dict):
        th = slim["thumbnail"]
        slim["thumbnail"] = {"score": th.get("score"), "composition": (th.get("composition") or "")[:200]}
    return json.dumps(slim, ensure_ascii=False, indent=2)


def _spoken_word_count(copy: VideoCopy) -> int:
    return normalize_script(copy.script).spoken_word_count


def generate_copy(
    creator: str, theme: str, chosen_hook: str, *, research: ResearchReport | None = None, profile: dict | None = None
) -> VideoCopy:
    """Step 2: short-form copy (~170–200 spoken words, ~60–90s) around the chosen hook."""
    if profile is not None:
        profile_obj = store.CreatorProfile.model_validate(profile)
    else:
        profile_obj = _profile_or_raise(creator)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"copy_director_{creator}",
        description="Scriptwriter for 60–90s short-form monologues (170–200 spoken words max).",
        instructions=COPY_INSTRUCTIONS,
        output_schema=VideoCopy,
    )
    logger.info("Generating copy for '%s' x '%s' with the chosen hook...", creator, theme)

    profile_json = _slim_profile_json(profile_obj)
    facts = _facts_block(research)

    base_prompt = (
        f"CREATOR PROFILE (measured evidence — JSON):\n{profile_json}\n"
        f"{facts}\n\n"
        f"USER THEME: {theme}\n"
        f'CHOSEN HOOK: "{chosen_hook}"\n\n'
        "Write a COMPLETE SHORT-FORM shooting script for ~60–90 SECONDS (max ~1:30, never 2+ minutes).\n"
        f"Spoken length: {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} words the host SAYS out loud "
        f"(target ~{TARGET_SPOKEN_WORDS}). HARD CAP: do NOT exceed {MAX_COPY_WORDS} spoken words.\n"
        f"Use {MIN_SCRIPT_BLOCKS}–9 timeline blocks, one line each:\n"
        "  [TIMESTAMP] | [SHOT] | [TEXT TO SAY] | [EDITING] | [WHY IT WORKS]\n"
        f'Block 1 TEXT = exactly the hook: "{chosen_hook}"\n'
        "Then: brief context → 2–4 concrete points → one caveat → clear close/CTA.\n"
        "Each speaking block: 1–2 full sentences (~15–30 words). Stay punchy for Shorts.\n"
        "At most ONE '(no speech — music only)' block. No timestamps inside WHY.\n"
        "Use measured cuts/min and shot grammar from the profile."
    )
    response = agent.run(base_prompt)
    copy = coerce_structured(response.content, VideoCopy, stage="Copy generation")
    copy = _normalize_video_copy(copy)

    # One light expansion only if truly short (under ~150). Do NOT push past 200 words.
    spoken_n = _spoken_word_count(copy)
    if spoken_n < MIN_SPOKEN_WORDS:
        logger.warning(
            "Copy only %d spoken words (min %d) — one expansion pass...",
            spoken_n,
            MIN_SPOKEN_WORDS,
        )
        spoken_preview = normalize_script(copy.script).spoken_copy
        expand_prompt = (
            f"THEME: {theme}\n"
            f'HOOK (must stay line 1): "{chosen_hook}"\n'
            f"{facts}\n\n"
            f"CURRENT NARRATION IS TOO SHORT ({spoken_n} words). "
            f"Rewrite to {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} spoken words "
            f"(target {TARGET_SPOKEN_WORDS}, NEVER over {MAX_COPY_WORDS}).\n\n"
            f"CURRENT SPOKEN TEXT:\n---\n{spoken_preview}\n---\n\n"
            "Pipe format, 6–9 blocks, ~0:00–1:20 max. Punchy short-form, not a lecture."
        )
        try:
            expand = agent.run(expand_prompt)
            expanded = coerce_structured(expand.content, VideoCopy, stage="Copy expansion")
            expanded = _normalize_video_copy(expanded)
            new_n = _spoken_word_count(expanded)
            if MIN_SPOKEN_WORDS <= new_n <= MAX_COPY_WORDS or (
                new_n > spoken_n and new_n <= MAX_COPY_WORDS + 20
            ):
                copy = expanded
                logger.info("Copy expansion: %d → %d spoken words", spoken_n, new_n)
        except Exception:
            logger.exception("Copy expansion pass failed")

    final_n = _spoken_word_count(copy)
    if final_n > MAX_COPY_WORDS + 30:
        logger.warning(
            "Copy is long (%d words, cap %d) — model over-wrote; leaving as-is for editor trim.",
            final_n,
            MAX_COPY_WORDS,
        )
    elif final_n < MIN_SPOKEN_WORDS:
        logger.warning(
            "Copy still short after expansion (%d < %d). Returning best effort.",
            final_n,
            MIN_SPOKEN_WORDS,
        )
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
