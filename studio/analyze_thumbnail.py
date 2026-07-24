"""Thumbnail Analysis — extracts and analyzes the first frame of a creator's video."""

import logging
import subprocess

from agno.media import Image

from .config import get_settings
from .factory import create_agent
from .parse import coerce_structured
from .schemas import ThumbnailAnalysis

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are a thumbnail design expert specialized in YouTube, TikTok and Instagram content.

You will receive the FIRST FRAME (thumbnail candidate) extracted from a creator's video.
Your task is to analyze its visual effectiveness for social media platforms.

Analyze:
1. COMPOSITION: Rule of thirds, visual balance, focal point placement.
2. DOMINANT COLORS: List the 3-5 most prominent colors (use common names like "vibrant red", "dark blue").
3. CONTRAST LEVEL: Rate as High/Medium/Low and explain why.
4. FACIAL EXPRESSION: If a person is visible, describe the emotion captured. If no person, say "No face detected".
5. TEXT READABILITY: If text is overlaid, assess font size, color contrast, and legibility. If no text, say "No text detected".
6. SCORE: Rate overall thumbnail effectiveness 0-10 for social media click-through.
7. SUGGESTIONS: Give 2-4 specific, actionable improvements.

Honesty rules (CRITICAL):
- Base conclusions ONLY on what is visible in the image.
- If the image quality is too low to assess something, state it in evidence_notes.
- Respond in English.
"""


def analyze_thumbnail(creator: str, max_videos: int | None = None) -> ThumbnailAnalysis:
    settings = get_settings()
    video_dir = settings.videos_dir / creator

    if not video_dir.exists():
        raise FileNotFoundError(f"Video directory not found for '{creator}'")

    videos = list(video_dir.glob("*.mp4"))
    if not videos:
        raise ValueError(f"No videos found in {video_dir}")

    first_video = videos[0]
    out_dir = settings.frames_dir / creator
    out_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = out_dir / "thumbnail.jpg"

    cmd = [
        "ffmpeg",
        "-i",
        str(first_video),
        "-vf",
        "scale=480:-2",
        "-vframes",
        "1",
        str(thumbnail_path),
        "-y",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to extract thumbnail frame: %s\n%s", e, e.stderr)
        raise ValueError(f"Failed to extract thumbnail frame for '{creator}'")

    if not thumbnail_path.exists():
        raise ValueError(f"Thumbnail extraction failed for '{creator}'")

    agent = create_agent(
        name=f"thumbnail_analyst_{creator}",
        description="Thumbnail design expert specialized in visual effectiveness.",
        instructions=INSTRUCTIONS,
        output_schema=ThumbnailAnalysis,
        vision=True,
        temperature=0.15,
    )

    logger.info("Analyzing thumbnail for %s...", creator)
    response = agent.run(
        "Analyze this thumbnail candidate.",
        images=[Image(filepath=thumbnail_path)],
    )

    return coerce_structured(response.content, ThumbnailAnalysis, stage="Thumbnail analysis")
