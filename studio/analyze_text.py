"""Textual analysis — reverse-engineers a creator's copy and hook fingerprint.

Consumes real transcriptions and returns a structured CreatorStyle. Runs once
per creator; the result is cached in the creator profile.

Product rule: NEVER leave the UI with empty/N/A/"Insufficient transcript"
fingerprints. When speech evidence is thin, we still return a usable
metrics-backed short-form fingerprint so hooks/copy can proceed.
"""

from __future__ import annotations

import json
import logging
import re

from . import store
from .config import get_settings
from .factory import create_agent
from .parse import coerce_structured
from .schemas import CreatorStyle, HookPattern
from .text_quality import (
    filter_expression,
    is_error_blob,
    is_speech_like,
    top_content_phrases,
)

logger = logging.getLogger(__name__)

_BAD_FIELD_RE = re.compile(
    r"^(n/?a|none|null|unknown|tbd|insufficient(\s+transcript)?(\s+evidence)?|"
    r"analysis failed|not enough|cannot (assess|determine))\.?$",
    re.IGNORECASE,
)

INSTRUCTIONS = """
You are an expert in copywriting reverse engineering and audience retention.

Your task is to extract a content creator's textual "fingerprint" from the real
transcriptions of their videos. You do NOT summarize the content — you decode
the TECHNIQUE: how they write, how they win attention, how they structure and
how they persuade.

Honesty rules (CRITICAL):
- Base every conclusion ONLY on the transcriptions and the MEASUREMENTS provided.
  Never use prior "knowledge" about the creator or their niche.
- Every hook pattern needs a real example extracted from the provided text when
  possible. If the sample is short, still propose 2 practical short-form patterns
  grounded in whatever words exist + the measured WPM/n-grams.
- The MEASUREMENTS (words/minute, repeated expressions with counts) are truths
  measured on the files: use the exact numbers in the corresponding fields —
  never estimate what has already been measured.
- NEVER output literal "N/A", "None", "Unknown", or "Insufficient transcript
  evidence" in tone, persona, sentence_rhythm, or copy_structure.
- Always fill every field with concrete, demo-usable language a creator can act on.
- Put limitations only in evidence_notes (what was thin / missing).
- Respond in English.
"""


def _is_usable_transcription(text: str, *, min_words: int = 8) -> bool:
    """Accept short but real speech; reject empty/error/URL blobs."""
    return is_speech_like(text, min_tokens=min_words)


def _field_is_bad(value: str | None) -> bool:
    if value is None:
        return True
    t = value.strip()
    if not t:
        return True
    if _BAD_FIELD_RE.match(t):
        return True
    if "insufficient transcript" in t.lower():
        return True
    return False


def _first_spoken_line(texts: list[str]) -> str:
    for t in texts:
        if is_error_blob(t):
            continue
        for part in re.split(r"[.!?]\s+", t.strip()):
            part = part.strip().strip('"“”')
            if len(part.split()) >= 4 and is_speech_like(part, min_tokens=4):
                return part[:160]
    return "Hey — watch this."


def _fallback_style(
    creator: str,
    metrics: dict | None,
    sample_texts: list[str] | None = None,
    *,
    reason: str = "",
) -> CreatorStyle:
    """Always-usable fingerprint from measured metrics + any speech crumbs."""
    metrics = metrics or {}
    speech = metrics.get("speech") or {}
    wpm = speech.get("avg_wpm")
    ngrams = metrics.get("signature_ngrams") or []
    exprs: list[str] = []
    for g in ngrams[:10]:
        if isinstance(g, dict) and g.get("ngram"):
            exprs.append(str(g["ngram"]))
        elif isinstance(g, str):
            exprs.append(g)

    texts = [t for t in (sample_texts or []) if t and is_speech_like(t, min_tokens=4)]
    # Never surface junk unigrams from error/URL text (https, ibm, quota, …)
    exprs = [e for e in exprs if filter_expression(e)]
    if not exprs and texts:
        exprs = top_content_phrases(texts, top_k=8)

    example = _first_spoken_line(texts)
    if wpm:
        if wpm >= 160:
            pace = f"Fast spoken cadence (~{wpm:.0f} WPM measured)"
            tone = "High-energy, direct short-form delivery"
        elif wpm >= 120:
            pace = f"Conversational spoken cadence (~{wpm:.0f} WPM measured)"
            tone = "Conversational, clear short-form delivery"
        else:
            pace = f"Deliberate spoken cadence (~{wpm:.0f} WPM measured)"
            tone = "Calm, deliberate on-camera delivery"
    else:
        pace = "Spoken cadence not fully measured — treat as typical short-form"
        tone = "On-camera short-form delivery"

    hooks = [
        HookPattern(
            pattern="Direct promise in the first seconds",
            why_it_works="Short-form retention requires an immediate reason to keep watching.",
            example=example,
        ),
        HookPattern(
            pattern="Problem → quick fix framing",
            why_it_works="Names a pain then implies a simple path — classic mobile hook.",
            example=example if len(example.split()) > 5 else "Stop doing this in the morning.",
        ),
        HookPattern(
            pattern="Curiosity / open loop",
            why_it_works="Withholds the full answer so the viewer stays for the payoff.",
            example="Here's the part nobody talks about…",
        ),
    ]

    note_bits = [
        f"Fingerprint for '{creator}' built to stay demo-usable.",
        "Primary sources: deterministic speech/edit metrics",
    ]
    if texts:
        note_bits.append(f"plus {len(texts)} short transcript sample(s)")
    else:
        note_bits.append("(limited/no clean transcript text)")
    if reason:
        note_bits.append(reason)
    note_bits.append("Re-ingest longer spoken Shorts for a richer linguistic fingerprint.")

    return CreatorStyle(
        tone=tone,
        sentence_rhythm=pace,
        persona="Creator speaking straight to camera in short-form format",
        hook_patterns=hooks,
        copy_structure=(
            "Open with a 1–2 second hook, deliver one clear idea with proof or steps, "
            "close with a takeaway or soft CTA — standard short-form arc."
        ),
        signature_expressions=exprs[:10],
        persuasion_tactics=[
            "Direct address (you/your)",
            "Pace matched to short-form attention",
            "Single-idea focus per video",
        ],
        evidence_notes=" ".join(note_bits),
    )


def _sanitize_style(
    style: CreatorStyle,
    creator: str,
    metrics: dict | None,
    sample_texts: list[str],
) -> CreatorStyle:
    """Replace any bad LLM fields so the UI never shows N/A / Insufficient."""
    fallback = _fallback_style(creator, metrics, sample_texts, reason="Sanitized incomplete model fields.")
    if (
        _field_is_bad(style.tone)
        and _field_is_bad(style.persona)
        and _field_is_bad(style.copy_structure)
        and not style.hook_patterns
    ):
        return fallback

    tone = fallback.tone if _field_is_bad(style.tone) else style.tone
    persona = fallback.persona if _field_is_bad(style.persona) else style.persona
    rhythm = fallback.sentence_rhythm if _field_is_bad(style.sentence_rhythm) else style.sentence_rhythm
    structure = fallback.copy_structure if _field_is_bad(style.copy_structure) else style.copy_structure
    hooks = style.hook_patterns if style.hook_patterns else fallback.hook_patterns
    exprs = [
        e
        for e in (style.signature_expressions or [])
        if e and not _field_is_bad(e) and filter_expression(e)
    ]
    if not exprs:
        exprs = fallback.signature_expressions
    tactics = [t for t in (style.persuasion_tactics or []) if t and not _field_is_bad(t)]
    if not tactics:
        tactics = fallback.persuasion_tactics
    notes = style.evidence_notes if style.evidence_notes and not _field_is_bad(style.evidence_notes) else fallback.evidence_notes

    return CreatorStyle(
        tone=tone,
        sentence_rhythm=rhythm,
        persona=persona,
        hook_patterns=hooks,
        copy_structure=structure,
        signature_expressions=exprs,
        persuasion_tactics=tactics,
        evidence_notes=notes,
    )


def analyze_style(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> CreatorStyle:
    settings = get_settings()
    items = store.get_creator_transcriptions(creator)
    raw_texts = [str(it.get("transcription") or "") for it in items]

    if not items:
        logger.warning("No transcriptions for '%s' — metrics-backed fallback fingerprint.", creator)
        return _fallback_style(
            creator,
            metrics,
            reason="No transcription rows stored for this creator.",
        )

    usable = [it for it in items if _is_usable_transcription(str(it.get("transcription") or ""))]
    sample_texts = [str(it.get("transcription") or "") for it in usable]

    if not usable:
        # Keep non-error crumbs if any (even < 8 words) for examples
        crumbs = [t for t in raw_texts if t.strip() and not is_error_blob(t)]
        logger.warning(
            "Thin/empty speech for '%s' — using metrics-backed fallback fingerprint.",
            creator,
        )
        return _fallback_style(
            creator,
            metrics,
            crumbs,
            reason="Captions/Whisper produced little usable speech; used measured metrics.",
        )

    sample = usable[: max_videos or settings.max_videos_per_creator]
    text = "\n\n---\n\n".join(f"[{item['video']}]\n{item['transcription']}" for item in sample)
    sample_texts = [str(it.get("transcription") or "") for it in sample]

    metrics_block = ""
    if metrics:
        measured = {
            "speech": metrics.get("speech"),
            "signature_ngrams": metrics.get("signature_ngrams"),
        }
        metrics_block = (
            "\n\nDeterministic MEASUREMENTS computed from the files (use the exact numbers):\n"
            f"{json.dumps(measured, ensure_ascii=False, indent=2)}"
        )

    try:
        agent = create_agent(
            name=f"style_analyst_{creator}",
            description="Expert in copywriting reverse engineering and style analysis.",
            instructions=INSTRUCTIONS,
            output_schema=CreatorStyle,
        )
        logger.info("Analyzing textual style of %s (%d videos)...", creator, len(sample))
        response = agent.run(
            f"Analyze the real transcriptions of creator '{creator}' below and extract their "
            f"copywriting fingerprint. Always fill every field with concrete actionable language "
            f"(never N/A or 'Insufficient'):\n\n{text}{metrics_block}"
        )
        style = coerce_structured(response.content, CreatorStyle, stage="Textual analysis")
        return _sanitize_style(style, creator, metrics, sample_texts)
    except Exception as e:
        logger.exception("Textual analysis failed for '%s' — fallback fingerprint.", creator)
        return _fallback_style(
            creator,
            metrics,
            sample_texts,
            reason=f"LLM style analysis error: {e!s}"[:200],
        )
