"""Audio transcription pipeline — Groq Whisper with retry and incremental saves.

Processes every new .mp4 under videos/<creator>/ and appends results to
data/transcriptions.json after each video, so a crash never loses progress.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings
from .store import load_transcriptions, save_transcriptions

logger = logging.getLogger(__name__)

SKIP_DIRS = {"__MACOSX", "__pycache__"}


def extract_audio(video_path: Path, audio_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "mp3",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
        "-y",
    ]
    subprocess.run(cmd, check=True, capture_output=True)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
def transcribe_audio(audio_path: Path, client: object, model: str) -> str:
    with open(audio_path, "rb") as audio_file:
        res = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="text",
        )
        return str(res.text) if hasattr(res, "text") else str(res)


def process_new_videos() -> dict[str, list[dict]]:
    settings = get_settings()
    if settings.openai_api_key and settings.model_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        model = "whisper-1"
    elif settings.groq_api_key:
        client = Groq(api_key=settings.groq_api_key)
        model = settings.groq_whisper_model
    elif settings.openai_api_key:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        model = "whisper-1"
    else:
        logger.warning("No API key configured for Whisper — cannot process new videos.")
        return load_transcriptions()

    transcriptions = load_transcriptions()

    if not settings.videos_dir.exists():
        logger.warning("Videos folder not found: %s", settings.videos_dir)
        return transcriptions

    for creator_dir in sorted(settings.videos_dir.iterdir()):
        if not creator_dir.is_dir() or creator_dir.name in SKIP_DIRS or creator_dir.name.startswith("."):
            continue

        creator = creator_dir.name
        existing = {item["video"] for item in transcriptions.get(creator, [])}
        transcriptions.setdefault(creator, [])

        media_files = [f for f in sorted(creator_dir.iterdir()) if f.suffix.lower() in {".mp4", ".m4a", ".webm", ".mp3", ".mkv"}]
        for video_file in media_files:
            if video_file.name in existing:
                continue

            logger.info("Transcribing %s/%s", creator, video_file.name)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = Path(tmp.name)

            try:
                extract_audio(video_file, audio_path)
                text = transcribe_audio(audio_path, client, settings.groq_whisper_model).strip()

                words = len(text.split())
                if words < settings.min_transcription_words:
                    logger.warning(
                        "Transcription too short (%d words), ignored: %s", words, video_file.name
                    )
                    continue

                transcriptions[creator].append({"video": video_file.name, "transcription": text})
                save_transcriptions(transcriptions)  # incremental save per video
                logger.info("[OK] %s transcribed (%d words)", video_file.name, words)

            except Exception:
                logger.exception("[ERROR] Failed to transcribe %s", video_file.name)
            finally:
                audio_path.unlink(missing_ok=True)

    save_transcriptions(transcriptions)
    return transcriptions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    process_new_videos()
