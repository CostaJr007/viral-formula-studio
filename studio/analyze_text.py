"""Textual analysis — reverse-engineers a creator's copy and hook fingerprint.

Consumes real transcriptions and returns a structured CreatorStyle. Runs once
per creator; the result is cached in the creator profile.
"""

import json
import logging

from . import store
from .config import get_settings
from .factory import create_agent
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
- Respond in English.
"""


def analyze_style(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> CreatorStyle:
    settings = get_settings()
    items = store.get_creator_transcriptions(creator)
    if not items:
        raise ValueError(f"No transcriptions found for '{creator}'. Run the transcription first.")

    sample = items[: max_videos or settings.max_videos_per_creator]
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
    if not isinstance(response.content, CreatorStyle):
        # Agno returns the provider's error text as content instead of raising
        raise RuntimeError(f"Textual analysis failed — model response: {str(response.content)[:200]}")
    return response.content
