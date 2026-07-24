"""Guided creation flow — the actionable half of the product.

Step 1 (generate_hooks): 10 hooks built from the creator's MEASURED formula
(hook patterns + metrics) and the verified facts from the research stage.
Step 2 (generate_copy): the user picks one hook; the full video copy is
orchestrated around it — ~170–200 spoken words (~60–90s shorts), the creator's
copy structure, measured editing directions, and explicit data-honesty notes.

Nothing here invents facts: hooks and copy may only use facts from the
ResearchReport; anything else becomes a placeholder for the user to fill.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher

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

_GARBAGE_HOOK_RE = re.compile(
    r"\bgt\b|https?://|www\.|&[a-z]+;|<\s*\w+|transcription|quota|rate.?limit",
    re.IGNORECASE,
)


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

You receive a COMPACT measured profile (tone, structure, hook patterns, cuts/min,
WPM) plus verified facts and the chosen hook.

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

NARRATION ARC + WORD BUDGET (~{TARGET_SPOKEN_WORDS} spoken words total):
1. Hook (block 1 TEXT = the chosen hook exactly) ~15–25 words
2. Setup / context ~25–35 words
3. Point A with concrete detail ~30–40 words
4. Point B ~30–40 words
5. Caveat / honesty beat ~20–30 words
6. Takeaway + soft CTA ~20–30 words
Optional 7–9 short blocks if needed — stay under {MAX_COPY_WORDS} spoken words.

RULES:
- CRITICAL: Do NOT use line breaks (newlines) inside a single block. Each timestamp block must be exactly one line.
- Output AT LEAST {MIN_SCRIPT_BLOCKS} separate lines (blocks), ideally 6–9, covering ~0:00 to ~1:00–1:30 max.
- HARD LENGTH TARGET: spoken words in TEXT fields MUST be between {MIN_SPOKEN_WORDS} and {MAX_COPY_WORDS}.
  Aim for ~{TARGET_SPOKEN_WORDS}. NEVER exceed {MAX_COPY_WORDS} spoken words.
- At least TWO EDITING fields must cite MEASURED numbers from the profile
  (e.g. "~X cuts/min", "shot ~Ys", "~Z WPM pace").
- COMPLETE NARRATION: the chosen hook is ONLY the first spoken line — continue with real dialogue.
- At most ONE block may use "(no speech — music only)". Almost every block needs real dialogue (1–2 sentences each).
- Every block MUST include all 5 fields separated by `|`: timestamp, shot, text, editing, psychology.
- SHOT TYPES must match the creator's measured grammar when provided.
- Never put the next timestamp inside the WHY field — start a NEW line instead.
- Respond in English (or the user's language if the theme is clearly non-English).
"""


# ---------------------------------------------------------------------------
# Profile slim + quality helpers (no extra LLM)
# ---------------------------------------------------------------------------


def slim_profile_for_prompt(profile_obj) -> dict:
    """Compact evidence for hooks/copy — cuts tokens, keeps measured formula."""
    full = profile_obj.model_dump() if hasattr(profile_obj, "model_dump") else dict(profile_obj)
    style = full.get("style") or {}
    editing = full.get("editing") or {}
    metrics = full.get("metrics") if isinstance(full.get("metrics"), dict) else {}
    m_edit = metrics.get("editing") or {}
    m_speech = metrics.get("speech") or {}
    ngrams = metrics.get("signature_ngrams") or []
    if isinstance(ngrams, list):
        ngrams = ngrams[:6]

    hooks = style.get("hook_patterns") or []
    if isinstance(hooks, list):
        hooks = hooks[:5]

    exprs = style.get("signature_expressions") or []
    if isinstance(exprs, list):
        exprs = [e for e in exprs if isinstance(e, str) and len(e) > 2][:8]

    return {
        "creator": full.get("creator"),
        "videos_analyzed": full.get("videos_analyzed"),
        "metrics": {
            "editing": {
                "avg_cuts_per_min": m_edit.get("avg_cuts_per_min"),
                "avg_shot_length_s": m_edit.get("avg_shot_length_s"),
                "videos_measured": m_edit.get("videos_measured"),
            },
            "speech": {"avg_wpm": m_speech.get("avg_wpm")},
            "signature_ngrams": ngrams,
        },
        "style": {
            "tone": style.get("tone"),
            "sentence_rhythm": style.get("sentence_rhythm"),
            "persona": style.get("persona"),
            "copy_structure": style.get("copy_structure"),
            "hook_patterns": hooks,
            "signature_expressions": exprs,
            "persuasion_tactics": (style.get("persuasion_tactics") or [])[:5],
            "evidence_notes": (style.get("evidence_notes") or "")[:300],
        },
        "editing": {
            "cut_cadence": editing.get("cut_cadence"),
            "shot_types": editing.get("shot_types"),
            "text_overlay_style": editing.get("text_overlay_style"),
            "b_roll_usage": editing.get("b_roll_usage"),
            "retention_tricks": (editing.get("retention_tricks") or [])[:5],
            "evidence_notes": (editing.get("evidence_notes") or "")[:200],
        },
    }


def _is_bad_hook_text(text: str) -> bool:
    t = (text or "").strip()
    if len(t.split()) < 5:
        return True
    if len(t) > 180:
        return True
    if _GARBAGE_HOOK_RE.search(t):
        return True
    low = t.lower()
    if "let s " in low or low.startswith("let s"):
        return True
    return False


def _hook_dedupe_key(text: str) -> str:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return " ".join(words[:4])


def filter_hooks(hooks: list[Hook], theme: str) -> list[Hook]:
    """Drop garbage / near-duplicate hooks. No LLM."""
    theme_tokens = {w for w in re.findall(r"[a-z0-9']+", theme.lower()) if len(w) > 3}
    cleaned: list[Hook] = []
    seen: set[str] = set()
    pattern_counts: dict[str, int] = {}

    for h in hooks:
        text = (h.text or "").strip()
        if _is_bad_hook_text(text):
            continue
        key = _hook_dedupe_key(text)
        if not key or key in seen:
            continue
        # Soft theme check: if theme has content words, prefer hooks that share ≥1
        if theme_tokens:
            hook_tokens = set(re.findall(r"[a-z0-9']+", text.lower()))
            if not (theme_tokens & hook_tokens) and len(cleaned) >= 6:
                # allow early variety; after 6 good ones skip off-theme
                continue
        pat = (h.pattern or "pattern").strip() or "pattern"
        if pattern_counts.get(pat, 0) >= 2:
            continue
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1
        seen.add(key)
        cleaned.append(Hook(text=text, pattern=pat))
        if len(cleaned) >= 10:
            break
    return cleaned


def _pad_hooks_to_ten(hooks: list[Hook], theme: str, profile_obj) -> list[Hook]:
    """Deterministic fillers from measured patterns when model returns < 10 clean hooks."""
    out = list(hooks)
    patterns: list[str] = []
    style = getattr(profile_obj, "style", None)
    if style and getattr(style, "hook_patterns", None):
        patterns = [hp.pattern for hp in style.hook_patterns if hp.pattern]
    if not patterns:
        patterns = [
            "Direct promise",
            "Problem → fix",
            "Curiosity gap",
            "Counterintuitive claim",
            "Social proof angle",
        ]
    templates = [
        "Stop scrolling — here's the truth about {theme}.",
        "What nobody tells you about {theme}.",
        "I tested {theme} so you don't waste time.",
        "The {theme} mistake almost everyone makes.",
        "Want better results with {theme}? Start here.",
        "Three seconds on {theme} that change the game.",
        "If you care about {theme}, hear this first.",
        "The simple {theme} fix that actually sticks.",
        "Before you try {theme}, watch this.",
        "Here's how {theme} actually works — no hype.",
    ]
    seen = {_hook_dedupe_key(h.text) for h in out}
    i = 0
    while len(out) < 10 and i < 40:
        text = templates[i % len(templates)].format(theme=theme.strip() or "this")
        key = _hook_dedupe_key(text)
        i += 1
        if key in seen or _is_bad_hook_text(text):
            continue
        seen.add(key)
        out.append(Hook(text=text, pattern=patterns[len(out) % len(patterns)]))
    return out[:10]


def _strip_quotes(text: str) -> str:
    t = (text or "").strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("“") and t.endswith("”")):
        return t[1:-1].strip()
    return t


def _hook_aligned(chosen_hook: str, first_block_text: str) -> bool:
    a = _strip_quotes(chosen_hook).lower()
    b = _strip_quotes(first_block_text).lower()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.55


def _spoken_word_count(copy: VideoCopy) -> int:
    return normalize_script(copy.script).spoken_word_count


def _truncate_copy_words(copy: VideoCopy) -> VideoCopy:
    """Drop trailing blocks until spoken words ≤ MAX_COPY_WORDS (deterministic)."""
    norm = normalize_script(copy.script)
    if not norm.blocks or norm.spoken_word_count <= MAX_COPY_WORDS:
        return copy

    blocks = list(norm.blocks)
    while len(blocks) > 4 and normalize_script(
        "\n".join(
            f"{b.timestamp} | {b.shot} | {b.text} | {b.editing} | {b.why}" for b in blocks
        )
    ).spoken_word_count > MAX_COPY_WORDS:
        blocks.pop()

    script = "\n".join(
        f"{b.timestamp} | {b.shot} | {b.text} | {b.editing} | {b.why}" for b in blocks
    )
    directions = list(copy.editing_directions or [])
    if len(directions) > len(blocks):
        directions = directions[: len(blocks)]
    note = (copy.data_notes or "").strip()
    trim_note = " [Script auto-trimmed to ~60–90s spoken length.]"
    if trim_note.strip() not in note:
        note = (note + trim_note).strip()
    logger.info(
        "Copy truncated to %d blocks / ~%d spoken words",
        len(blocks),
        normalize_script(script).spoken_word_count,
    )
    return VideoCopy(script=script, editing_directions=directions, data_notes=note)


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
    # Cap facts for prompt budget
    slim = {
        "summary": (research.summary or "")[:400],
        "facts": [
            {"claim": f.claim[:280], "source": f.source} for f in (research.facts or [])[:5]
        ],
        "unconfirmed": (research.unconfirmed or [])[:5],
    }
    return (
        "\nVERIFIED FACTS ABOUT THE THEME (single factual source — JSON):\n"
        f"{json.dumps(slim, ensure_ascii=False, indent=2)}"
    )


def _coerce_profile(creator: str, profile: dict | None):
    """Prefer client-sent profile (survives restarts); fall back to disk; never crash on partial JSON."""
    if profile is not None:
        try:
            return store.CreatorProfile.model_validate(profile)
        except Exception as e:
            logger.warning("Client profile invalid for '%s' (%s) — loading from disk", creator, e)
    return _profile_or_raise(creator)


def generate_hooks(
    creator: str, theme: str, *, research: ResearchReport | None = None, profile: dict | None = None
) -> HookList:
    """Step 1: 10 hooks from the creator's formula + verified facts."""
    profile_obj = _coerce_profile(creator, profile)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"hook_strategist_{creator}",
        description="Hook strategist based on creators' measured formulas.",
        instructions=HOOKS_INSTRUCTIONS,
        output_schema=HookList,
        temperature=0.4,
    )
    slim = slim_profile_for_prompt(profile_obj)

    logger.info("Generating 10 hooks from '%s' for '%s'...", creator, theme)
    response = agent.run(
        f"USER'S THEME (the hooks MUST be about this topic): {theme}\n\n"
        f"Creator profile (measured evidence — compact JSON):\n"
        f"{json.dumps(slim, ensure_ascii=False, indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f"Generate exactly 10 hooks. Every single hook MUST reference the user's theme: '{theme}'. "
        "Apply the creator's patterns to THIS theme — do NOT use the creator's original topic. "
        "Return structured JSON only — be concise."
    )
    raw = coerce_structured(response.content, HookList, stage="Hook generation")
    cleaned = filter_hooks(raw.hooks, theme)
    if len(cleaned) < 10:
        logger.info("Hooks after filter: %d — padding to 10 with measured-pattern templates", len(cleaned))
        cleaned = _pad_hooks_to_ten(cleaned, theme, profile_obj)
    return HookList(hooks=cleaned[:10])


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

    directions = list(copy.editing_directions or [])
    if len(directions) < max(3, len(normalized.blocks) // 2):
        directions = [
            f"{b.timestamp}: {b.editing}".strip(": ") for b in normalized.blocks if b.editing
        ] or directions

    return VideoCopy(
        script=repaired_script,
        editing_directions=directions,
        data_notes=copy.data_notes,
    )


def generate_copy(
    creator: str,
    theme: str,
    chosen_hook: str,
    *,
    research: ResearchReport | None = None,
    profile: dict | None = None,
) -> VideoCopy:
    """Step 2: short-form copy (~170–200 spoken words, ~60–90s) around the chosen hook."""
    profile_obj = _coerce_profile(creator, profile)

    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"copy_director_{creator}",
        description="Scriptwriter for 60–90s short-form monologues (170–200 spoken words max).",
        instructions=COPY_INSTRUCTIONS,
        output_schema=VideoCopy,
        temperature=0.25,
    )
    logger.info("Generating copy for '%s' x '%s' with the chosen hook...", creator, theme)

    profile_json = json.dumps(slim_profile_for_prompt(profile_obj), ensure_ascii=False, indent=2)
    facts = _facts_block(research)
    cuts = None
    wpm = None
    try:
        m = slim_profile_for_prompt(profile_obj).get("metrics") or {}
        cuts = (m.get("editing") or {}).get("avg_cuts_per_min")
        wpm = (m.get("speech") or {}).get("avg_wpm")
    except Exception:
        pass
    metrics_hint = ""
    if cuts is not None or wpm is not None:
        metrics_hint = (
            f"\nMEASURED TARGETS TO CITE IN EDITING FIELDS: "
            f"cuts/min={cuts!s}, WPM={wpm!s}.\n"
        )

    base_prompt = (
        f"CREATOR PROFILE (measured evidence — compact JSON):\n{profile_json}\n"
        f"{facts}\n"
        f"{metrics_hint}\n"
        f"USER THEME: {theme}\n"
        f'CHOSEN HOOK (block 1 TEXT must match): "{chosen_hook}"\n\n'
        "Write a COMPLETE SHORT-FORM shooting script for ~60–90 SECONDS (max ~1:30).\n"
        f"Spoken length: {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} words "
        f"(target ~{TARGET_SPOKEN_WORDS}). HARD CAP: do NOT exceed {MAX_COPY_WORDS}.\n"
        f"Use {MIN_SCRIPT_BLOCKS}–9 timeline blocks, one line each:\n"
        "  [TIMESTAMP] | [SHOT] | [TEXT TO SAY] | [EDITING] | [WHY IT WORKS]\n"
        f'Block 1 TEXT = exactly: "{chosen_hook}"\n'
        "Arc: hook → setup → 2 concrete points → caveat → CTA. Stay punchy for Shorts.\n"
        "At most ONE '(no speech — music only)' block. Cite measured cuts/min or WPM in ≥2 EDITING fields."
    )

    def _once(prompt: str, stage: str) -> VideoCopy:
        response = agent.run(prompt)
        copy = coerce_structured(response.content, VideoCopy, stage=stage)
        return _normalize_video_copy(copy)

    copy = _once(base_prompt, "Copy generation")

    # Expand if too short
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
            expanded = _once(expand_prompt, "Copy expansion")
            new_n = _spoken_word_count(expanded)
            if MIN_SPOKEN_WORDS <= new_n <= MAX_COPY_WORDS or (
                new_n > spoken_n and new_n <= MAX_COPY_WORDS + 20
            ):
                copy = expanded
                logger.info("Copy expansion: %d → %d spoken words", spoken_n, new_n)
        except Exception:
            logger.exception("Copy expansion pass failed")

    # Align opening hook if model drifted
    norm = normalize_script(copy.script)
    first_text = norm.blocks[0].text if norm.blocks else ""
    if norm.blocks and not _hook_aligned(chosen_hook, first_text):
        logger.warning("First block hook misaligned — one repair pass...")
        repair_prompt = (
            f"THEME: {theme}\n"
            f'CHOSEN HOOK (MUST be block 1 TEXT exactly): "{chosen_hook}"\n'
            f"{facts}\n\n"
            "Rewrite the full pipe-format script. Block 1 TEXT must be the chosen hook. "
            f"Keep {MIN_SPOKEN_WORDS}–{MAX_COPY_WORDS} spoken words, 6–9 blocks.\n\n"
            f"CURRENT SCRIPT:\n{copy.script[:3500]}"
        )
        try:
            repaired = _once(repair_prompt, "Copy hook repair")
            rnorm = normalize_script(repaired.script)
            if rnorm.blocks and _hook_aligned(chosen_hook, rnorm.blocks[0].text):
                copy = repaired
            elif rnorm.blocks:
                # Force-inject hook into first block text
                b0 = rnorm.blocks[0]
                lines = [
                    f'{b0.timestamp} | {b0.shot} | "{_strip_quotes(chosen_hook)}" | {b0.editing} | {b0.why}'
                ]
                for b in rnorm.blocks[1:]:
                    lines.append(f"{b.timestamp} | {b.shot} | {b.text} | {b.editing} | {b.why}")
                copy = VideoCopy(
                    script="\n".join(lines),
                    editing_directions=repaired.editing_directions,
                    data_notes=repaired.data_notes,
                )
                copy = _normalize_video_copy(copy)
        except Exception:
            logger.exception("Copy hook repair failed")

    # Hard cap spoken length
    if _spoken_word_count(copy) > MAX_COPY_WORDS:
        copy = _truncate_copy_words(copy)

    final_n = _spoken_word_count(copy)
    if final_n > MAX_COPY_WORDS + 30:
        logger.warning(
            "Copy still long (%d words, cap %d) after truncate.",
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
