"""Textual analysis — reverse-engineers a creator's copy and hook fingerprint.

Consumes real transcriptions and returns a structured CreatorStyle. Runs once
per creator; the result is cached in the creator profile.
"""

import json
import logging

from . import store
from .config import get_settings
from .factory import create_agent
from .parse import coerce_structured
from .schemas import CreatorStyle

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are an expert in copywriting reverse engineering and audience retention.

Your task is to extract a content creator's textual "fingerprint" from the real
transcriptions of their videos. You do NOT summarize the content — you decode
the TECHNIQUE: how they write, how they win attention, how they structure and
how they persuade.

Honesty rules (CRITICAL):
- Base every conclusion ONLY on the transcriptions and the MEASUREMENTS provided.
  Never use prior "knowledge" about the creator or their niche.
- Every hook pattern needs a real example extracted from the provided text.
- The MEASUREMENTS (words/minute, repeated expressions with counts) are truths
  measured on the files: use the exact numbers in the corresponding fields —
  never estimate what has already been measured.
- If the evidence is insufficient for any dimension, state that explicitly
  in the evidence_notes field instead of filling it with assumptions.
- NEVER put the literal strings "N/A", "None", "Unknown", or "n/a" into tone,
  persona, sentence_rhythm, or copy_structure. If you cannot assess a field,
  write a short honest phrase like "Insufficient transcript evidence" and explain
  fully in evidence_notes.
- If the provided "transcriptions" are error messages, API failures, or empty
  placeholders (not real spoken words), do NOT invent a fingerprint — set
  evidence_notes to describe the failure and use "Insufficient transcript evidence"
  for textual fields, with empty hook_patterns / signature_expressions lists.
- Respond in English.
"""


def _is_usable_transcription(text: str, *, min_words: int = 25) -> bool:
    """Reject empty, tiny, or error-message 'transcripts' that poison style analysis."""
    raw = (text or "").strip()
    if not raw:
        return False
    words = raw.split()
    if len(words) < min_words:
        return False
    lower = raw.lower()
    error_markers = (
        "error message",
        "failed request",
        "request failed",
        "rate limit",
        "unauthorized",
        "traceback",
        "exception:",
        "http error",
        "could not retrieve",
        "transcription unavailable",
        "no captions",
        "access denied",
        "403",
        "401",
        "500 internal",
    )
    # Short blobs that are clearly system errors, not speech
    if len(words) < 80 and any(m in lower for m in error_markers):
        return False
    return True


def analyze_style(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> CreatorStyle:
    settings = get_settings()
    items = store.get_creator_transcriptions(creator)
    if not items:
        raise ValueError(f"No transcriptions found for '{creator}'. Run the transcription first.")

    usable = [it for it in items if _is_usable_transcription(str(it.get("transcription") or ""))]
    if not usable:
        logger.warning(
            "All transcriptions for '%s' look empty/errored — returning insufficient-evidence style.",
            creator,
        )
        return CreatorStyle(
            tone="Insufficient transcript evidence",
            sentence_rhythm="Insufficient transcript evidence",
            persona="Insufficient transcript evidence",
            hook_patterns=[],
            copy_structure="Insufficient transcript evidence — re-ingest with working captions or Whisper.",
            signature_expressions=[],
            persuasion_tactics=[],
            evidence_notes=(
                f"No usable spoken transcriptions for '{creator}'. "
                "Captions/Whisper may have failed (error text stored instead of speech). "
                "Re-run ingest with public YouTube Shorts + GROQ_API_KEY, or use a seed creator."
            ),
        )

    sample = usable[: max_videos or settings.max_videos_per_creator]
    text = "\n\n---\n\n".join(f"[{item['video']}]\n{item['transcription']}" for item in sample)

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

    agent = create_agent(
        name=f"style_analyst_{creator}",
        description="Expert in copywriting reverse engineering and style analysis.",
        instructions=INSTRUCTIONS,
        output_schema=CreatorStyle,
    )
    logger.info("Analyzing textual style of %s (%d videos)...", creator, len(sample))
    response = agent.run(
        f"Analyze the real transcriptions of creator '{creator}' below and extract their "
        f"copywriting fingerprint:\n\n{text}{metrics_block}"
    )
    return coerce_structured(response.content, CreatorStyle, stage="Textual analysis")
