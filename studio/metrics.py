"""Deterministic measurements — the provable layer of the analysis.

Everything here is computed directly from the video/audio/text files with plain
ffmpeg + Python. No LLM involved: these are MEASURED facts about the creator
(cuts/min, words/min, repeated expressions with counts). The LLM stages then
INTERPRET these numbers instead of guessing them — which is what makes the
final dossier data-based rather than "an AI that wrote a copy".
"""

import logging
import re
import subprocess
from collections import Counter
from pathlib import Path

from . import store
from .config import get_settings
from .frames import get_video_duration

logger = logging.getLogger(__name__)

SCENE_THRESHOLD = 0.3

# Portuguese stopwords — matches the language of the source transcriptions
# (the analyzed creators speak Portuguese). Changing this set changes the
# measured n-grams, so it stays as-is on purpose.
_STOPWORDS_PT = {
    "a", "o", "e", "é", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "um", "uma",
    "que", "pra", "para", "com", "se", "eu", "você", "ele", "ela", "isso", "esse", "essa", "isto",
    "ao", "aos", "à", "às", "por", "mais", "muito", "muita", "como", "mas", "ou", "quando", "já",
    "também", "só", "tem", "têm", "ter", "ser", "estar", "foi", "são", "era", "vai", "vou", "meu",
    "minha", "seu", "sua", "dele", "dela", "aí", "lá", "aqui", "hoje", "então", "assim", "porque",
    "pois", "nem", "não", "sim", "me", "te", "lhe", "vos", "lo", "la", "aquilo",
}


def detect_cuts(video_path: Path, threshold: float = SCENE_THRESHOLD) -> list[float]:
    """Detect scene-change timestamps (seconds) via ffmpeg's scene score."""
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", result.stderr)]


def cut_metrics(video_path: Path) -> dict:
    """Real editing cadence of one video: cuts/min and average shot length."""
    duration = get_video_duration(video_path)
    cuts = detect_cuts(video_path)
    shots = len(cuts) + 1
    return {
        "duration_s": round(duration, 1),
        "cuts": len(cuts),
        "cuts_per_min": round(len(cuts) / duration * 60, 1) if duration else 0.0,
        "avg_shot_length_s": round(duration / shots, 1) if shots else 0.0,
    }


def editing_metrics(creator: str, max_videos: int | None = None) -> dict:
    """Aggregate real cut metrics over a sample of the creator's videos."""
    settings = get_settings()
    creator_dir = settings.videos_dir / creator
    if not creator_dir.is_dir():
        return {}

    videos = sorted(creator_dir.glob("*.mp4"))[: max_videos or settings.max_videos_per_creator]
    per_video, total_cuts, total_duration = [], 0, 0.0

    for video in videos:
        try:
            metrics = cut_metrics(video)
            per_video.append({"video": video.name, **metrics})
            total_cuts += metrics["cuts"]
            total_duration += metrics["duration_s"]
            logger.info("Measured %s: %d cuts (%.1f/min)", video.name, metrics["cuts"], metrics["cuts_per_min"])
        except Exception:
            logger.exception("Failed to measure cuts of %s", video.name)

    if not per_video:
        return {}

    return {
        "videos_measured": len(per_video),
        "total_cuts": total_cuts,
        "total_duration_s": round(total_duration, 1),
        "avg_cuts_per_min": round(total_cuts / total_duration * 60, 1) if total_duration else 0.0,
        "avg_shot_length_s": round(total_duration / (total_cuts + len(per_video)), 1),
        "per_video": per_video,
    }


def speech_metrics(creator: str, max_videos: int | None = None) -> dict:
    """Real speech rate: transcription words / video duration, per video and average."""
    settings = get_settings()
    items = store.get_creator_transcriptions(creator)[: max_videos or settings.max_videos_per_creator]
    per_video, wpms = [], []

    for item in items:
        video_path = settings.videos_dir / creator / item["video"]
        if not video_path.exists():
            continue
        try:
            duration = get_video_duration(video_path)
        except Exception:
            logger.exception("Failed to measure duration of %s", video_path.name)
            continue

        words = len(item["transcription"].split())
        wpm = round(words / duration * 60, 1) if duration else 0.0
        wpms.append(wpm)
        per_video.append(
            {"video": item["video"], "words": words, "duration_s": round(duration, 1), "wpm": wpm}
        )

    if not wpms:
        return {}

    return {"avg_wpm": round(sum(wpms) / len(wpms), 1), "per_video": per_video}


def signature_ngrams(creator: str, n: int = 3, top_k: int = 10, min_count: int = 2) -> list[dict]:
    """Most repeated n-grams across the creator's transcriptions, with real counts."""
    counter: Counter = Counter()
    for item in store.get_creator_transcriptions(creator):
        words = re.findall(r"[a-záàâãéêíóôõúç]+", item["transcription"].lower())
        for i in range(len(words) - n + 1):
            gram = tuple(words[i : i + n])
            if gram[0] in _STOPWORDS_PT or gram[-1] in _STOPWORDS_PT:
                continue
            counter[gram] += 1

    return [
        {"ngram": " ".join(gram), "count": count}
        for gram, count in counter.most_common(top_k)
        if count >= min_count
    ]


def measure_creator(creator: str, max_videos: int | None = None) -> dict:
    """Full deterministic measurement pass for a creator (no LLM)."""
    logger.info("Measuring '%s' (cuts, speech rate, expressions)...", creator)
    return {
        "editing": editing_metrics(creator, max_videos),
        "speech": speech_metrics(creator, max_videos),
        "signature_ngrams": signature_ngrams(creator),
    }
