# Viral Formula Studio — API backend (FastAPI + ffmpeg)
FROM python:3.12-slim

# ffmpeg/ffprobe are required by the metrics + transcription pipeline
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv via official installer (avoids external registry pulls inside the build env)
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY studio ./studio
COPY api.py ./
# data/ is intentionally NOT copied: profiles and transcripts are runtime artifacts
# (seed them at runtime or ingest through the UI).

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
