# Viral Formula Studio

**Multimodal reverse engineering of a content creator's viral formula.** Give it a
creator (up to 5 short-video links from YouTube Shorts, TikTok, or Instagram Reels)
and your topic — the AI watches, learns, and delivers an actionable playbook: hook
formulas, copy structure, editing grammar and persuasion tactics, transposed to
*your* theme, in *your* voice.

> Inspiration, not imitation. Every great creator started by studying someone.
> We hand you the notebook that used to take months to build.

**IBM AI Builders Challenge — July 2026 · "Reimagine Creative Industries with AI"**

🚀 **Live demo:** `bit.ly/vfs-studio`

---

## What It Does

1. **Paste up to 5 Shorts/TikToks/Reels** from any public creator
2. The AI **downloads, transcribes and extracts frames** from each video
3. **Deterministic measurements** (cuts/min, words/min, signature n-grams) run first
4. **Text analysis** decodes the creator's copy fingerprint (tone, hooks, structure)
5. **Visual analysis** decodes the editing grammar (cut cadence, framing, overlays)
6. **Fact-checking** gathers verified sources about your topic
7. **10 derived hooks** in the creator's proven patterns
8. **≤200-word script** with editing directions aligned to measured metrics

## AI Models — Multimodal Architecture

Viral Formula Studio uses a **hybrid, multi-model pipeline** where each stage
runs on the best-suited AI model:

| Stage | Model | Role | Provider |
|---|---|---|---|
| 🎤 **Transcription** | Whisper Large v3 Turbo | Audio → text (captions-first, Whisper fallback) | Groq |
| 📊 **Metrics** | Python + ffmpeg | Deterministic: cuts/min, WPM, n-grams | No AI |
| ✍️ **Text Analysis** | Granite 4 (ibm/granite-4-h-small) | Decodes tone, hooks, copy structure from transcripts | IBM watsonx.ai |
| 👁️ **Visual Analysis** | Llama 3.2 11B Vision | Reads frames, decodes editing grammar | IBM watsonx.ai |
| 🔍 **Fact-Check** | Granite 4 + Tavily | Web search → verified facts with sources | IBM watsonx.ai + Tavily |
| 📝 **Hooks & Copy** | Granite 4 | Generates 10 hooks + ≤200-word script | IBM watsonx.ai |
| 📋 **Dossier** | Granite 4 | Full viralization playbook (6 sections) | IBM watsonx.ai |

> **Granite is the product's voice.** All text the user reads (analysis, hooks,
> copy, dossier) comes from IBM Granite 4 on watsonx.ai. The vision stage uses a
> supporting multimodal model because watsonx doesn't yet offer a Granite vision
> model in the current regions — a hybrid pattern where the supporting model reads
> frames and Granite writes the interpretation.

**Automatic fallback:** if watsonx fails (rate limits, outage), all agents
transparently retry on OpenAI GPT-4o — the feature degrades, it never dies.

## Honesty by Design

Every claim in the output is grounded in real evidence:

```
STAGE 0 — MEASURE (no AI): cuts/min, shot length, words/min, n-grams
STAGE 1 — EVIDENCE (cached): CreatorStyle (text) + EditingProfile (frames)
STAGE 2 — SCOUT: verified facts about the topic, with source URLs
STAGE 3 — COMMENTATOR: dossier/copy grounded ONLY in injected evidence
```

- **Measured, not guessed** — the AI interprets deterministic ffmpeg numbers instead of estimating
- **Ground truth injection** — synthesis only receives extracted profiles and verified facts
- **Honesty rules** — every prompt requires `evidence_notes`, `unconfirmed`, and `[INSERT: ...]` placeholders for unverifiable data
- **Graceful degradation** — no captions → Whisper; no search → structural mode; provider down → automatic fallback

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic, Agno 2.7 (agent framework) |
| Frontend | React 19, Vite, TanStack Start, Tailwind 4, shadcn/ui |
| AI Providers | IBM watsonx.ai (Granite 4), OpenAI (GPT-4o fallback) |
| Transcription | Groq Whisper Large v3 Turbo |
| Media Processing | ffmpeg/ffprobe (scene detection, frame sampling) |
| Ingestion | yt-dlp (YouTube Shorts, TikTok, Instagram Reels) |
| Fact-Checking | Tavily Search API |
| Deploy | Docker + IBM Code Engine (us-south) |
| CI/CD | GitHub Actions → Docker Hub → Code Engine |
| Testing | pytest (25 tests), ruff (lint) |

## Running Locally

```bash
git clone https://github.com/CostaJr007/viral-formula-studio.git
cd viral-formula-studio
uv sync
```

Create `.env` from `.env.example`:

```bash
MODEL_PROVIDER=watsonx              # or openai (prototyping)
IBM_WATSONX_API_KEY=your_key
IBM_WATSONX_PROJECT_ID=your_project
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-4-h-small
OPENAI_API_KEY=your_key             # fallback
GROQ_API_KEY=your_key               # transcription
TAVILY_API_KEY=your_key             # fact-checking
```

```bash
uv run python api.py                    # Backend → http://localhost:8000
cd frontend && npm install && npm run dev  # Frontend → http://localhost:3000
```

Alternative local UIs: `uv run python app.py` (Gradio, port 7860) or `uv run python main.py` (CLI).

## Project Structure

```
studio/
├── config.py          # pydantic-settings: keys, paths, provider switch
├── factory.py         # ONLY place that knows the LLM provider + fallback
├── schemas.py         # Pydantic contracts (CreatorStyle, EditingProfile, etc.)
├── limits.py          # IP rate limiter (max 3 analyses/IP/hour)
├── parse.py           # Resilient structured-output recovery (JSON → Pydantic)
├── store.py           # JSON persistence (transcripts, cached profiles)
├── ingest.py          # Link ingestion: yt-dlp, captions-first, Whisper fallback
├── transcribe.py      # Local-folder transcription pipeline
├── frames.py          # ffmpeg frame sampling (480p, uniform)
├── metrics.py         # Deterministic: cuts/min, WPM, n-grams (no LLM)
├── analyze_text.py    # Agent: transcripts + metrics → CreatorStyle
├── analyze_visual.py  # Agent: frames + metrics → EditingProfile (multimodal)
├── research.py        # Agent: web fact-check → ResearchReport
├── dossier.py         # Agent: profiles + facts → viralization playbook
├── create.py          # Guided flow: 10 hooks → pick → ≤200-word copy
└── pipeline.py        # Per-creator orchestration (runs once, cached)
api.py                 # FastAPI backend (production)
app.py                 # Gradio UI (quick local demos)
main.py                # Terminal CLI
frontend/              # React 19 + Vite + TanStack Start (4-step wizard)
tests/                 # 25 pytest tests
data/                  # Transcripts + cached creator profiles
```

## Testing

```bash
uv run pytest          # 25 tests (no API keys needed)
uv run ruff check .    # lint
```

## Live API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check + active provider |
| `GET /api/creators` | List analyzed creators |
| `POST /api/ingest` | Start analysis (5 URLs → job) |
| `GET /api/jobs/{id}` | Poll analysis progress |
| `GET /api/profile/{creator}` | Cached creator profile |
| `POST /api/hooks` | Generate 10 hooks |
| `POST /api/copy` | Generate ≤200-word script |
| `POST /api/dossier` | Export full viralization playbook |
| `GET /api/usage` | Rate limit status |

## License

© 2026 Costa Jr. All rights reserved. Shared publicly for review as part of the
IBM AI Builders Challenge (July 2026).
