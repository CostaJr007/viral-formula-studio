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


def _clean_transcription(text: str) -> str:
    """Remove common transcription artifacts that pollute hooks and analysis."""
    import re

    # YouTube auto-caption HTML entities
    text = text.replace("&gt;", "").replace("&lt;", "").replace("&amp;", "&")
    # Standalone "gt" tokens (usually from "&gt;" being stripped incorrectly)
    text = re.sub(r'\bgt\b\s+', '', text)
    text = re.sub(r'\s+\bgt\b', '', text)
    # Fix broken contractions: "let s" -> "let's", "don t" -> "don't"
    text = re.sub(r"\blet\s+s\b", "let's", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdon\s+t\b", "don't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcan\s+t\b", "can't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwon\s+t\b", "won't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bain\s+t\b", "ain't", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(i|you|he|she|it|we|they)\s+(ll|ve|re|d|m)\b",
                  r"\1'\2", text, flags=re.IGNORECASE)
    # Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def _base_opts(out_dir: Path) -> dict:
    """Shared yt-dlp options tuned for cloud / datacenter IPs.

    YouTube increasingly requires a JS runtime for web clients. Prefer mobile
    player clients (android/ios/mweb) which still work without deno/node, and
    keep retries polite so burst rate-limits don't kill the whole job.
    """
    return {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "retries": 5,
        "fragment_retries": 5,
        "sleep_interval_requests": 1.0,
        "sleep_interval": 1.5,
        "max_sleep_interval": 6,
        # Prefer clients that work without a JS challenge solver in containers.
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb", "tv"],
                "player_skip": ["webpage", "configs"],
            }
        },
        # Some hosts block the default Python UA; a browser-like UA helps TikTok.
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        # Allow remote EJS components when a JS runtime (node/deno) is present.
        "remote_components": ["ejs:github"],
    }


def probe(url: str) -> dict:
    """Fetch metadata only (no download): id, title, duration, uploader, platform."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb", "tv"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("yt-dlp returned empty metadata (blocked or invalid URL)")
    return {
        "id": info.get("id"),
        "title": info.get("title", ""),
        "duration": info.get("duration") or 0,
        "uploader": info.get("uploader") or info.get("channel") or "",
        "platform": info.get("extractor_key", ""),
    }


def fetch_captions(url: str, out_dir: Path) -> str | None:
    """Try to get free captions (YouTube). Returns plain text or None.

    Subtitle 429s / missing tracks must NOT fail the whole ingest — Whisper is the fallback.
    """
    opts = _base_opts(out_dir) | {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": CAPTION_LANGS + ["en.*", "pt.*"],
        "subtitlesformat": "vtt",
        # Don't raise when one language track is rate-limited
        "ignoreerrors": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
            base = Path(ydl.prepare_filename(info))
    except Exception:
        logger.warning("Failed to fetch captions for %s — will try Whisper.", url)
        return None

    stem = base.stem
    candidates = list(out_dir.glob(f"{stem}.*.vtt")) + list(out_dir.glob("*.vtt"))
    for vtt in sorted(set(candidates)):
        try:
            text = parse_vtt(vtt.read_text(encoding="utf-8", errors="ignore"))
        finally:
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
    # Broad format ladder: mobile clients often only expose progressive streams.
    format_ladder = (
        "best[height<=480][ext=mp4]/"
        "best[height<=720][ext=mp4]/"
        "worst[ext=mp4]/"
        "best[height<=480]/"
        "best[ext=mp4]/"
        "best"
    )
    opts = _base_opts(out_dir) | {
        "format": format_ladder,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise RuntimeError("Download returned no info (platform may block this IP)")
        path = Path(ydl.prepare_filename(info))
        # Sometimes extension differs from template after merge
        if not path.exists():
            candidates = list(out_dir.glob(f"{info.get('id', '')}.*"))
            candidates = [c for c in candidates if c.suffix.lower() in {".mp4", ".webm", ".mkv", ".m4a"}]
            if candidates:
                path = candidates[0]
        if not path.exists():
            raise RuntimeError(f"Downloaded file missing after yt-dlp: expected {path.name}")
        return path


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


def _fix_transcription_coherence(text: str) -> str:
    """Optionally polish auto-captions with an LLM — NEVER replace good speech with errors.

    If watsonx/OpenAI returns quota/HTML/error text, we keep the regex-cleaned Whisper
    transcript. A bad "fix" previously caused ingest to reject valid videos.
    """
    from .text_quality import is_error_blob, is_speech_like

    original = (text or "").strip()
    if not original:
        return original

    try:
        from agno.agent import Agent

        from .factory import get_model

        agent = Agent(
            model=get_model(),
            name="transcription_cleaner",
            description="Cleans auto-generated transcripts while preserving meaning.",
            instructions=(
                "You are a transcript cleaner. Fix garbled words, broken sentences, "
                "stuttering, transcription artifacts, and HTML entities. Preserve the "
                "original meaning, tone, and word count as closely as possible. "
                "Return ONLY the cleaned spoken transcript — no explanations, no headers, "
                "no apologies, no system messages."
            ),
        )
        response = agent.run(f"Clean this transcript:\n\n{original}")
        if not isinstance(response.content, str):
            return original
        fixed = response.content.strip()
        if len(fixed) < 10:
            return original
        # Reject model failures that look like API errors / refusals
        if is_error_blob(fixed):
            logger.warning("Coherence fix returned error-like text — keeping Whisper/captions original.")
            return original
        if not is_speech_like(fixed, min_tokens=6) and is_speech_like(original, min_tokens=6):
            logger.warning("Coherence fix destroyed speech quality — keeping original.")
            return original
        # If the model gutted the transcript, keep original
        if len(fixed.split()) < max(8, int(len(original.split()) * 0.4)):
            logger.warning("Coherence fix too short vs original — keeping original.")
            return original
        return fixed
    except Exception:
        logger.warning("Transcription coherence fix failed — using regex-cleaned text.")
    return original


def ingest_urls(creator: str, urls: list[str], max_new: int | None = None) -> dict:
    """Ingest a list of video URLs for a creator. Returns a per-URL status report."""
    settings = get_settings()
    creator_dir = settings.videos_dir / creator
    creator_dir.mkdir(parents=True, exist_ok=True)

    transcriptions = store.load_transcriptions()
    existing = {item["video"] for item in transcriptions.get(creator, [])}
    transcriptions.setdefault(creator, [])

    limit = max_new or settings.max_videos_per_creator
    report: dict = {"ok": [], "skipped": [], "failed": [], "reused": []}

    # Normalize: only real links, preserve order, drop blanks (1st empty + 2nd filled is fine)
    clean_urls = []
    for raw in urls:
        u = (raw or "").strip()
        if not u:
            continue
        if not u.startswith(("http://", "https://")):
            report["failed"].append({"url": u[:80], "reason": "not a valid http(s) URL"})
            continue
        clean_urls.append(u)

    if not clean_urls:
        report["failed"].append(
            {
                "url": "",
                "reason": "no http links in the request (empty slots are OK — paste at least one full URL in any row)",
            }
        )
        return report

    for url in clean_urls:
        if len(report["ok"]) >= limit:
            report["skipped"].append({"url": url, "reason": f"limit of {limit} videos reached"})
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
            # Already have speech for this file — counts as success (not a failure skip)
            logger.info("Already transcribed, reusing: %s", video_path.name)
            report["ok"].append(url)
            report["reused"].append(url)
            continue

        # Captions first (free); Whisper as fallback
        text = fetch_captions(url, creator_dir) or _transcribe_with_whisper(video_path)
        if text is None:
            settings = get_settings()
            if not settings.groq_api_key:
                reason = (
                    "no captions available and GROQ_API_KEY is missing "
                    "(needed for Whisper fallback)"
                )
            else:
                reason = "no captions and Whisper transcription failed or too short"
            report["failed"].append({"url": url, "reason": reason})
            continue

        # Clean: regex first; optional LLM polish (must not replace good speech with errors)
        cleaned = _clean_transcription(text)
        fixed = _fix_transcription_coherence(cleaned)

        from .text_quality import is_error_blob, is_speech_like

        # Prefer polished text, but fall back to cleaned Whisper/captions if polish is junk
        final_text = fixed
        if is_error_blob(final_text) or not is_speech_like(final_text, min_tokens=6):
            if is_speech_like(cleaned, min_tokens=6) and not is_error_blob(cleaned):
                logger.warning("Using raw cleaned transcript (polish rejected) for %s", video_path.name)
                final_text = cleaned
            else:
                report["failed"].append(
                    {
                        "url": url,
                        "reason": (
                            "no usable spoken transcript after captions/Whisper "
                            "(empty, too short, or error text). Check GROQ_API_KEY and try again."
                        ),
                    }
                )
                continue

        transcriptions[creator].append({"video": video_path.name, "transcription": final_text})
        store.save_transcriptions(transcriptions)  # incremental save
        logger.info("[OK] %s ingested (%s, %ds)", video_path.name, meta["uploader"], meta["duration"])
        report["ok"].append(url)

    return report
