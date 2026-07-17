"""Link-based ingestion — YouTube Shorts, TikTok and best-effort Instagram.

The user pastes links instead of uploading files. This module downloads the
videos (low-res is enough for frames/metrics) into the EXISTING structure
(videos/<creator>/ + data/transcriptions.json), so the whole downstream
pipeline (frames, metrics, analyses, dossier) works unchanged.

Transcription strategy per video:
1. YouTube: try free captions first (no download, no Whisper cost).
2. Otherwise: download the audio track and use Groq Whisper (existing code).

Platform reality (be honest, don't promise what doesn't exist):
- YouTube (incl. Shorts): reliable via yt-dlp.
- TikTok: reliable for public videos, no login.
- Instagram: NO official access; yt-dlp works *sometimes* for public posts and
  may require login cookies. On failure we tell the user to drop the files
  manually into videos/<creator>/ (one-time per creator).
"""

import logging
import re
from pathlib import Path

import yt_dlp
from groq import Groq

from . import store
from .config import get_settings
from .transcribe import extract_audio, transcribe_audio

logger = logging.getLogger(__name__)

CAPTION_LANGS = ["pt", "pt-BR", "en", "en-US", "en-GB"]


def _base_opts(out_dir: Path) -> dict:
    return {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        # Politeness: platforms (esp. YouTube) rate-limit bursts — space out
        # requests and retry transparently instead of dying with a 429.
        "retries": 3,
        "fragment_retries": 3,
        "sleep_interval_requests": 1.5,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
    }


def probe(url: str) -> dict:
    """Fetch metadata only (no download): id, title, duration, uploader, platform."""
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "id": info.get("id"),
        "title": info.get("title", ""),
        "duration": info.get("duration") or 0,
        "uploader": info.get("uploader") or info.get("channel") or "",
        "platform": info.get("extractor_key", ""),
    }


def fetch_captions(url: str, out_dir: Path) -> str | None:
    """Try to get free captions (YouTube). Returns plain text or None."""
    opts = _base_opts(out_dir) | {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": CAPTION_LANGS,
        "subtitlesformat": "vtt",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base = Path(ydl.prepare_filename(info))
    except Exception:
        logger.exception("Failed to fetch captions for %s", url)
        return None

    for vtt in sorted(out_dir.glob(f"{base.stem}.*.vtt")):
        text = parse_vtt(vtt.read_text(encoding="utf-8", errors="ignore"))
        vtt.unlink(missing_ok=True)
        if len(text.split()) >= get_settings().min_transcription_words:
            return text
    return None


def parse_vtt(vtt_text: str) -> str:
    """Turn a WebVTT caption file into clean plain text (deduped lines)."""
    lines, seen = [], set()
    for raw in vtt_text.splitlines():
        line = re.sub(r"<[^>]+>", "", raw).strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return " ".join(lines)


def download_video(url: str, out_dir: Path) -> Path:
    """Download the video at the lowest usable resolution (frames/metrics only)."""
    opts = _base_opts(out_dir) | {
        "format": "worst[ext=mp4][height>=360]/worst[ext=mp4]/worst/best[height<=480]",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info))


def _transcribe_with_whisper(video_path: Path) -> str | None:
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY missing — cannot transcribe %s without captions.", video_path.name)
        return None
    client = Groq(api_key=settings.groq_api_key)
    audio_path = video_path.with_suffix(".mp3")
    try:
        extract_audio(video_path, audio_path)
        text = transcribe_audio(audio_path, client, settings.groq_whisper_model).strip()
        if len(text.split()) < settings.min_transcription_words:
            logger.warning("Transcription too short, ignored: %s", video_path.name)
            return None
        return text
    except Exception:
        logger.exception("Whisper failed for %s", video_path.name)
        return None
    finally:
        audio_path.unlink(missing_ok=True)


def ingest_urls(creator: str, urls: list[str], max_new: int | None = None) -> dict:
    """Ingest a list of video URLs for a creator. Returns a per-URL status report."""
    settings = get_settings()
    creator_dir = settings.videos_dir / creator
    creator_dir.mkdir(parents=True, exist_ok=True)

    transcriptions = store.load_transcriptions()
    existing = {item["video"] for item in transcriptions.get(creator, [])}
    transcriptions.setdefault(creator, [])

    limit = max_new or settings.max_videos_per_creator
    report = {"ok": [], "skipped": [], "failed": []}

    for url in urls:
        url = url.strip()
        if not url:
            continue
        if len(report["ok"]) >= limit:
            report["skipped"].append(url)
            continue

        logger.info("Ingesting: %s", url)
        try:
            meta = probe(url)
        except Exception as e:
            hint = (
                "Instagram blocked anonymous access — download the Reel manually into videos/"
                f"{creator}/ and run the analysis."
                if "instagram.com" in url
                else str(e)[:150]
            )
            logger.warning("Failed to access %s: %s", url, hint)
            report["failed"].append({"url": url, "reason": hint})
            continue

        try:
            video_path = download_video(url, creator_dir)
        except Exception as e:
            logger.warning("Download failed for %s: %s", url, str(e)[:150])
            report["failed"].append({"url": url, "reason": str(e)[:150]})
            continue

        if video_path.name in existing:
            logger.info("Already transcribed, skipping: %s", video_path.name)
            report["skipped"].append(url)
            continue

        # Captions first (free); Whisper as fallback
        text = fetch_captions(url, creator_dir) or _transcribe_with_whisper(video_path)
        if text is None:
            report["failed"].append({"url": url, "reason": "no captions and transcription unavailable"})
            continue

        transcriptions[creator].append({"video": video_path.name, "transcription": text})
        store.save_transcriptions(transcriptions)  # incremental save
        logger.info("[OK] %s ingested (%s, %ds)", video_path.name, meta["uploader"], meta["duration"])
        report["ok"].append(url)

    return report
