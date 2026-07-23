"""Central configuration — pydantic-settings as the single source of truth.

Everything (paths, API keys, model ids, analysis tuning) lives here and can be
overridden via .env or real environment variables. No hardcoded paths elsewhere.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Priority: init > .env > machine env vars.

        The project .env is the source of truth. A stale machine-wide variable
        (e.g. an old OPENAI_API_KEY) must never silently override it.
        """
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    # Provider switch: "openai" (prototyping) | "watsonx" (IBM submission) | "gemini" (free tier)
    model_provider: str = "openai"

    # OpenAI (prototyping)
    openai_api_key: str | None = None
    openai_model_id: str = "gpt-4o"
    openai_vision_model_id: str = "gpt-4o"

    # IBM watsonx.ai (Granite) — names match what Agno's WatsonX integration reads
    ibm_watsonx_api_key: str | None = None
    ibm_watsonx_project_id: str | None = None
    ibm_watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    # granite-3-8b-instruct lacks tools/structured-output support on watsonx;
    # granite-4-h-small supports both (verified live)
    watsonx_model_id: str = "ibm/granite-4-h-small"
    # watsonx has no Granite vision model in the current regions; the frame-analysis
    # stage uses this supporting vision model while Granite stays the product's voice
    watsonx_vision_model_id: str = "meta-llama/llama-3-2-11b-vision-instruct"
    # Unspecified max_tokens falls back to 1024 on watsonx and truncates long
    # structured JSON (hook lists, dossiers). 4096 is enough for our schemas.
    # Long shooting scripts (200–250 spoken words + pipe metadata) need headroom
    watsonx_max_tokens: int = 6144

    # Google Gemini
    google_api_key: str | None = None
    gemini_model_id: str = "gemini-2.0-flash"  # fast multimodal Llama/Granite equivalents

    # Groq Whisper (audio transcription)
    groq_api_key: str | None = None
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # Tavily (optional web research)
    tavily_api_key: str | None = None

    # Paths (all anchored to the project root, never to the CWD)
    videos_dir: Path = PROJECT_ROOT / "videos"
    data_dir: Path = PROJECT_ROOT / "data"
    transcriptions_file: Path = PROJECT_ROOT / "data" / "transcriptions.json"
    profiles_dir: Path = PROJECT_ROOT / "data" / "profiles"
    frames_dir: Path = PROJECT_ROOT / "data" / "frames"
    output_dir: Path = PROJECT_ROOT / "output"
    db_file: Path = PROJECT_ROOT / "tmp" / "storage.db"

    # Analysis tuning
    max_videos_per_creator: int = 5
    frames_per_video: int = 8
    max_frames_per_analysis: int = 24
    min_transcription_words: int = 20

    def export_to_environ(self) -> None:
        """Mirror keys into the process env — Agno/OpenAI/Groq clients read them from there.

        Overrides any pre-existing machine env var: the project .env is the
        source of truth (a stale key elsewhere must not shadow it).
        """
        mapping = {
            "OPENAI_API_KEY": self.openai_api_key,
            "GROQ_API_KEY": self.groq_api_key,
            "TAVILY_API_KEY": self.tavily_api_key,
            "IBM_WATSONX_API_KEY": self.ibm_watsonx_api_key,
            "IBM_WATSONX_PROJECT_ID": self.ibm_watsonx_project_id,
            "IBM_WATSONX_URL": self.ibm_watsonx_url,
            "GOOGLE_API_KEY": self.google_api_key,  # Agno and the Gemini SDK read from here
            "GEMINI_API_KEY": self.google_api_key,  # Convention fallback
        }
        for key, value in mapping.items():
            if value:
                os.environ[key] = str(value)

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.profiles_dir, self.frames_dir, self.output_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.export_to_environ()
    settings.ensure_dirs()
    return settings
