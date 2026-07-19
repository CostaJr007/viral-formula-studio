# AGENTS.md — Viral Formula Studio

Guidance for any AI agent (or human) working on this repository.

## What this is

Multimodal reverse engineering of a content creator's viral formula. Input: up to 5
short-video links + a topic. Output: a measured shooting script with timestamps,
shot types, editing directions, and retention psychology — plus 10 hooks and a
full viralization playbook.
Positioning: **inspiration, not imitation** — the formula migrates, the user's voice stays.

## Layout

- `studio/` — Python engine (the product brain). All analysis logic lives here.
- `api.py` — FastAPI layer exposing the engine to the React frontend.
  Rate-limited (IP-based, 8 creators + 8 dossiers per IP/hour via `studio/limits.py`).
- `frontend/` — React 19 + Vite + TanStack Start + Tailwind 4 UI (5-step wizard).
- `app.py` — legacy Gradio UI (kept for quick local demos).
- `main.py` — terminal CLI. `tests/` — pytest suite (25 tests). `data/` — transcripts + cached profiles.

## Non-negotiable rules

1. **Measured, not guessed.** Any claim about a creator's rhythm/editing/expressions must
   come from `studio/metrics.py` (deterministic ffmpeg/Python numbers). LLMs interpret
   measurements; they never invent them.
2. **Honesty by design.** Every analysis prompt keeps `evidence_notes` / `unconfirmed` /
   `[INSERT: ...]` placeholders. Never fabricate facts, rankings, or creator behavior.
3. **Provider switch stays in `studio/factory.py`.** OpenAI for prototyping, IBM Granite
   (watsonx) for submission, OpenAI as automatic fallback. Do not hardcode providers elsewhere.
4. **English everywhere** — code, prompts, UI strings, docs (submission is international).
5. No secrets in the repo. Keys live only in `.env` (gitignored). `.env.example` documents them.

## Commands

```bash
uv sync                       # Python deps
uv run pytest                 # engine tests (no API keys needed)
uv run ruff check .           # lint
uv run python api.py          # FastAPI backend -> http://localhost:8000
cd frontend && npm install && npm run dev   # React UI -> http://localhost:3000
```

## Conventions

- Python: ruff (line-length 110), Pydantic for every LLM output, structured JSON for data.
- Frontend: TypeScript strict-ish, shadcn-style components in `src/components/ui`,
  Tailwind tokens from `src/styles.css` (no inline hex in components).
- Commits: small, descriptive, English. No force-push on `main`.
