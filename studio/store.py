"""Persistence layer: transcriptions and creator profiles (plain JSON).

Kept deliberately simple — JSON files are enough at this scale and make the
pipeline inspectable. All paths come from studio.config, never from the CWD.
"""

import json
import logging
from pathlib import Path

from .config import get_settings
from .schemas import CreatorProfile

logger = logging.getLogger(__name__)


def load_transcriptions() -> dict[str, list[dict]]:
    path = get_settings().transcriptions_file
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.error("Corrupted transcriptions file: %s", path)
        return {}


def save_transcriptions(data: dict[str, list[dict]]) -> None:
    path = get_settings().transcriptions_file
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_creator_transcriptions(creator: str) -> list[dict]:
    return load_transcriptions().get(creator, [])


def list_creators() -> list[str]:
    """Creators known from any source: videos dir, transcriptions or saved profiles."""
    settings = get_settings()
    names = set(load_transcriptions().keys())
    if settings.videos_dir.exists():
        names |= {
            d.name for d in settings.videos_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "__"))
        }
    if settings.profiles_dir.exists():
        names |= {p.stem for p in settings.profiles_dir.glob("*.json")}
    return sorted(names)


def profile_path(creator: str) -> Path:
    # Normalize: lowercase to avoid "TEST" vs "test" creating separate profiles.
    # But seed files may use original case (e.g., "Bryan.json") — fall back.
    settings = get_settings()
    lower = settings.profiles_dir / f"{creator.lower()}.json"
    if lower.exists():
        return lower
    original = settings.profiles_dir / f"{creator}.json"
    if original.exists():
        return original
    # Neither exists — return lowercase path for saving new profiles
    return lower


def load_profile(creator: str) -> CreatorProfile | None:
    path = profile_path(creator)
    if not path.exists():
        return None
    return CreatorProfile.model_validate_json(path.read_text(encoding="utf-8"))


def save_profile(profile: CreatorProfile) -> Path:
    # Always save as lowercase to keep the filesystem consistent
    path = get_settings().profiles_dir / f"{profile.creator.lower()}.json"
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return path
