# Viral Formula Studio — API backend (FastAPI + ffmpeg)
FROM python:3.12-slim

# ffmpeg/ffprobe are required by the metrics + transcription pipeline
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# uv for dependency management (uv.lock guarantees reproducibility)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY studio ./studio
COPY api.py ./
# data/ is intentionally NOT copied: profiles and transcripts are runtime artifacts
# (seed them at runtime or ingest through the UI).

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
