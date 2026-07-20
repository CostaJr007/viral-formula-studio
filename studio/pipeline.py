"""Full per-creator pipeline: transcribe -> measure -> frames -> style + editing -> cached profile.

Stage order matters: the deterministic measurements (studio/metrics.py) run
BEFORE the LLM analyses, so the models interpret measured numbers instead of
guessing. Runs once per creator; the dossier step consumes the cached profile.
"""

import logging

from . import store
from .analyze_text import analyze_style
from .analyze_thumbnail import analyze_thumbnail
from .analyze_visual import analyze_editing
from .config import get_settings
from .metrics import measure_creator
from .schemas import CreatorProfile
from .transcribe import process_new_videos

logger = logging.getLogger(__name__)


def analyze_creator(
    creator: str, *, transcribe: bool = True, max_videos: int | None = None
) -> CreatorProfile:
    settings = get_settings()

    if transcribe:
        logger.info("Checking for new videos to transcribe...")
        process_new_videos()

    try:
        profile = store.load_profile(creator) or CreatorProfile(creator=creator, videos_analyzed=0)
    except Exception:
        # Corrupted/poisoned profile (e.g. saved during a failed run) — start fresh
        logger.warning("Profile for '%s' unreadable; regenerating from scratch.", creator)
        profile = CreatorProfile(creator=creator, videos_analyzed=0)

    # Deterministic layer first: measured numbers, no LLM
    profile.metrics = measure_creator(creator, max_videos)

    transcriptions = store.get_creator_transcriptions(creator)
    if transcriptions:
        profile.style = analyze_style(creator, max_videos, metrics=profile.metrics)
        profile.videos_analyzed = min(len(transcriptions), max_videos or settings.max_videos_per_creator)
    else:
        logger.warning("No transcriptions for '%s' — textual analysis skipped.", creator)

    try:
        profile.editing = analyze_editing(creator, max_videos, metrics=profile.metrics)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Visual analysis skipped: %s", e)

    try:
        profile.thumbnail = analyze_thumbnail(creator, max_videos)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Thumbnail analysis skipped: %s", e)

    if profile.style is None and profile.editing is None:
        raise RuntimeError(f"Nothing to analyze in '{creator}': no transcriptions or videos.")

    path = store.save_profile(profile)
    logger.info("Profile for '%s' saved to %s", creator, path)
    return profile
