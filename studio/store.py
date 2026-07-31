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
    data = load_transcriptions()
    if creator in data:
        return data[creator]
    # Case-insensitive fallback (UI may send "Bryan", disk may use "bryan")
    lower = creator.lower()
    for key, rows in data.items():
        if key.lower() == lower:
            return rows
    return []


def _is_junk_creator_name(name: str) -> bool:
    """Skip test fixtures and OS noise so demos/API stay clean."""
    if not name or name.startswith((".", "__")):
        return True
    n = name.lower()
    return n.startswith("test_") or n.endswith("_test") or "rickroll" in n


def list_creators() -> list[str]:
    """Creators with a saved profile (demo seeds + finished analyses).

    Incomplete local folders (videos only, no profile) are omitted so the
    judge/demo path only shows click-ready creators with ffmpeg metrics already
    baked into data/profiles/*.json. Custom ingest still works via POST /api/ingest.
    """
    settings = get_settings()
    by_lower: dict[str, str] = {}

    if not settings.profiles_dir.exists():
        return []

    for path in settings.profiles_dir.glob("*.json"):
        if _is_junk_creator_name(path.stem):
            continue
        display = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Require measured metrics so empty stubs never appear as demos
            metrics = data.get("metrics")
            if not isinstance(metrics, dict) or not metrics:
                continue
            creator = data.get("creator")
            if isinstance(creator, str) and creator.strip():
                display = creator.strip()
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        by_lower[display.lower()] = display

    return sorted(by_lower.values(), key=str.lower)


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
    profile = CreatorProfile.model_validate_json(path.read_text(encoding="utf-8"))
    # Heal legacy profiles saved with N/A / "Insufficient transcript evidence"
    # so the UI never shows a broken fingerprint again.
    if profile.style is not None:
        from .analyze_text import _fallback_style, _field_is_bad

        s = profile.style
        if (
            _field_is_bad(s.tone)
            or _field_is_bad(s.persona)
            or _field_is_bad(s.copy_structure)
            or "insufficient transcript" in f"{s.tone} {s.copy_structure}".lower()
        ):
            logger.info("Healing unusable style on profile '%s'", creator)
            profile.style = _fallback_style(
                profile.creator,
                profile.metrics,
                reason="Healed legacy empty/N/A fingerprint on load.",
            )
            try:
                save_profile(profile)
            except Exception:
                logger.warning("Could not persist healed profile for '%s'", creator)
    return profile


def save_profile(profile: CreatorProfile) -> Path:
    # Always save as lowercase to keep the filesystem consistent
    path = get_settings().profiles_dir / f"{profile.creator.lower()}.json"
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return path
