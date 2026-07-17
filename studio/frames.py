"""Frame extraction for the visual editing analysis (ffmpeg).

Low resolution is a feature, not a limitation: 480p frames are enough to read
text overlays, framing and cut cadence, and keep the vision model fast and cheap.
"""

import logging
import subprocess
from pathlib import Path

from .config import get_settings

logger = logging.getLogger(__name__)


def get_video_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_frames(video_path: Path, out_dir: Path, max_frames: int) -> list[Path]:
    """Uniformly sample up to max_frames frames from a video, at 480p."""
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = get_video_duration(video_path)
    interval = max(duration / max_frames, 1.0)  # never faster than 1 frame/second

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        f"fps=1/{interval:.2f},scale=480:-2",
        "-frames:v",
        str(max_frames),
        str(out_dir / "frame_%03d.jpg"),
        "-y",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out_dir.glob("frame_*.jpg"))


def extract_frames_for_creator(creator: str, max_videos: int | None = None) -> list[Path]:
    """Extract (or reuse cached) frames for a sample of a creator's videos."""
    settings = get_settings()
    creator_dir = settings.videos_dir / creator
    if not creator_dir.is_dir():
        raise FileNotFoundError(f"Pasta de vídeos não encontrada para '{creator}': {creator_dir}")

    videos = sorted(creator_dir.glob("*.mp4"))[: max_videos or settings.max_videos_per_creator]
    all_frames: list[Path] = []

    for video in videos:
        out_dir = settings.frames_dir / creator / video.stem
        cached = sorted(out_dir.glob("frame_*.jpg"))
        if cached:
            all_frames.extend(cached)
            continue

        logger.info("Extraindo frames de %s", video.name)
        try:
            all_frames.extend(extract_frames(video, out_dir, settings.frames_per_video))
        except Exception:
            logger.exception("[ERRO] Falha ao extrair frames de %s", video.name)

    return all_frames[: settings.max_frames_per_analysis]
