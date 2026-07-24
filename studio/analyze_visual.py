"""Visual analysis — reverse-engineers a creator's editing grammar from frames.

This is the multimodal heart of the product: real video frames go to the active
multimodal model (GPT-4o today, Granite vision on watsonx for the submission)
and come back as a structured EditingProfile. Cut cadence itself is MEASURED
deterministically (studio/metrics.py) — the vision model interprets what the
numbers cannot see (framing, text overlays, b-roll, identity).
"""

import json
import logging

from agno.media import Image

from .factory import create_agent
from .frames import extract_frames_for_creator
from .parse import coerce_structured
from .schemas import EditingProfile

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are a professional video editor specialized in short-form content (Reels/TikTok/Shorts)
and in retention psychology.

You will receive a sequence of REAL frames extracted from a creator's videos, in
chronological order, and real MEASUREMENTS of the cut cadence (cuts/minute and
average shot length, computed by ffmpeg scene detection). Your task is to decode
their EDITING GRAMMAR.

Honesty rules (CRITICAL):
- In cut_cadence, use the MEASURED NUMBERS (exact) — your visual reading complements
  them with what the numbers do not show (cut type, angle, movement).
- Base every conclusion ONLY on what is visible in the frames + the measurements.
  Do not presume anything that cannot be observed directly.
- If something cannot be observed with the available frames, state it in evidence_notes.
- Respond in English.
"""


def analyze_editing(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> EditingProfile:
    frames = extract_frames_for_creator(creator, max_videos)
    if not frames:
        raise ValueError(f"No frames extracted for '{creator}' — check the videos/{creator}/ folder.")

    metrics_block = ""
    if metrics and metrics.get("editing"):
        metrics_block = (
            "\n\nReal MEASUREMENTS of the cut cadence (ffmpeg scene detection — use the exact numbers):\n"
            f"{json.dumps(metrics['editing'], ensure_ascii=False, indent=2)}"
        )

    agent = create_agent(
        name=f"editing_analyst_{creator}",
        description="Senior video editor specialized in retention and editing grammar.",
        instructions=INSTRUCTIONS,
        output_schema=EditingProfile,
        vision=True,
        temperature=0.15,
    )
    logger.info("Analyzing editing grammar of %s (%d frames)...", creator, len(frames))
    response = agent.run(
        f"These are {len(frames)} real frames, in chronological order, from videos by "
        f"creator '{creator}'. Decode their editing grammar.{metrics_block}",
        images=[Image(filepath=frame) for frame in frames],
    )
    return coerce_structured(response.content, EditingProfile, stage="Visual analysis")
