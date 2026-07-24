# Viral Formula Studio

**Multimodal reverse engineering of a content creator’s viral formula.**

Paste short-form links (or pick a seed creator) + your topic. The system **measures** cuts, speech rate and patterns with ffmpeg, **decodes** style with IBM Granite 4 and editing grammar with Llama Vision on watsonx.ai, then delivers **10 hooks** and a **shoot-ready call-sheet script** (~60–90s) on *your* theme — in *your* voice.

> **Inspiration, not imitation.** We hand you the notebook that used to take months to build.

| | |
|---|---|
| **Live demo** | [bit.ly/viral-studio](https://bit.ly/viral-studio) |
| **Challenge** | IBM AI Builders · July 2026 · *Reimagine Creative Industries with AI* |
| **Hosting** | IBM Cloud Code Engine (us-south) |
| **Repo** | [CostaJr007/viral-formula-studio](https://github.com/CostaJr007/viral-formula-studio) |

![Demo](demo.gif)

**IBM stack:** watsonx.ai (Granite 4 + Llama 3.2 Vision) · Code Engine · Container Registry · IBM Bob (dev partner)

---

## For judges (2 minutes)

Seed creators are **pre-analyzed** — no upload, no wait for yt-dlp.

1. Open **[bit.ly/viral-studio](https://bit.ly/viral-studio)**
2. Tap **Decode formula** on **jeffnippard** (or Bryan / kallaway)
3. Review the **measured** profile (cuts/min, WPM, style, editing)
4. **Generate 10 hooks** → pick one
5. **Write script** → shooting report (spoken copy + timeline + export `.md`)

Optional: light/dark toggle · **New topic** reuses the same creator formula · custom Shorts via *Or analyze your own creator*.

---

## Problem

Creators spend weeks watching others and still **guess** what works — hooks, cut pace, speech rhythm. Generic AI writers invent claims (“fast cuts”) without ever measuring a frame.

## Solution

| Principle | What we do |
|-----------|------------|
| **Measured, not guessed** | ffmpeg/Python: cuts/min, shot length, WPM, n-grams — before any LLM |
| **Multimodal evidence** | Transcripts → Granite 4 · frames → Llama Vision · metrics stay ground truth |
| **Transpose, don’t clone** | Patterns applied to *your* topic; user voice stays |
| **Honesty by design** | `evidence_notes`, `unconfirmed`, `[INSERT: …]` when facts are missing |
| **Ship-ready** | Live on Code Engine, rate limits, seed cache, mobile + light mode |

Deep dive: [docs/INNOVATION.md](docs/INNOVATION.md)

---

## How it works

```
INPUT                         PIPELINE                              OUTPUT
─────                         ────────                              ──────
Seed creator  ──┐
  or            ├──▶  0 MEASURE   ffmpeg (no AI)              ──▶  Profile
1–5 Shorts      │     1 EVIDENCE  Granite style ∥ Vision      ──▶  10 hooks
+ your topic  ──┘     2 SCOUT     Tavily (topic facts, cached)──▶  Shooting script
                      3 CREATE    Granite hooks + copy        ──▶  Call-sheet report
```

**Product defaults (short-form):** ~**170–200** spoken words · **~60–90s** · **6–9** timeline blocks.

### Evidence stages (specialized, not one mega-prompt)

| Stage | Role | Engine |
|-------|------|--------|
| Measure | Cuts/min, shot length, WPM, n-grams | ffmpeg + Python |
| Textual analyst | Tone, hooks, copy structure | Granite 4 (watsonx) |
| Visual editor | Editing grammar from frames | Llama 3.2 Vision (watsonx) |
| Thumbnail analyst | First-frame CTR signals | Llama 3.2 Vision |
| Scout | Verified facts about **your topic** (not the influencer’s biography) | Tavily HTTP (cached per theme) |
| Hook strategist | 10 hooks + quality filter | Granite 4 |
| Script director | Call-sheet script + length repair/trim | Granite 4 |
| Fallback | Rate-limit / outage safety net | OpenAI GPT-4o (optional) |

Granite 4 is the **product voice**. OpenAI is fallback only. Fact-check targets the **user’s theme** so scripts stay honest — we do **not** scrape “how famous creator X edits” from the web; we measure the videos you provide.

### Quality without extra agents

- Slim measured profile into prompts (metrics + formula only)
- Hook post-filter (drop transcript garbage / near-dupes) + pad to 10
- Copy: word budget, hook alignment repair, hard truncate to ~200 spoken words
- Role-specific temperatures · parallel style/vision after metrics · research cache (hooks + copy share one Tavily call)

---

## Built on IBM Cloud

| Component | Service |
|-----------|---------|
| Language + vision | **IBM watsonx.ai** — `ibm/granite-4-h-small` + `meta-llama/llama-3-2-11b-vision-instruct` |
| Hosting | **IBM Cloud Code Engine** — `vfs-api` + `vfs-web` (serverless) |
| Images | Container registry via CI (GitHub Actions → Docker Hub → Code Engine) |
| Build partner | **IBM Bob** — architecture, watsonx wiring, deploy debugging |

| App | Role | Notes |
|-----|------|--------|
| `vfs-api` | FastAPI + ffmpeg | Port 8000 · seeds in image · env secrets |
| `vfs-web` | React UI | Port 4173 · `VITE_API_URL` at **build** time |

Deploy guide: [docs/deployment/DEPLOY_IBM.md](docs/deployment/DEPLOY_IBM.md)

**Production checklist**

- Rate limit: 8 new creators / IP / hour (seeds unlimited)
- Health: `GET /api/health` → `status`, `provider`, `build`
- Cold start ~30–90s on free tier (min-scale 0); use **min-scale 1** on pitch day
- Prefer public **YouTube Shorts** in cloud; TikTok/IG may block datacenter IPs

---

## Tech stack

| Layer | Stack |
|-------|--------|
| AI | watsonx.ai · Agno 2.7 · structured Pydantic outputs |
| API | Python 3.12 · FastAPI · uvicorn |
| UI | React 19 · Vite · TanStack Start · Tailwind 4 · shadcn/ui |
| Media | yt-dlp · ffmpeg · Groq Whisper (when captions fail) |
| Facts | Tavily |
| Tests | pytest (no live keys) · ruff |

---

## Run locally

```bash
git clone https://github.com/CostaJr007/viral-formula-studio.git
cd viral-formula-studio
uv sync
cp .env.example .env   # fill keys — never commit .env
```

```env
MODEL_PROVIDER=watsonx
IBM_WATSONX_API_KEY=
IBM_WATSONX_PROJECT_ID=
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-4-h-small
WATSONX_VISION_MODEL_ID=meta-llama/llama-3-2-11b-vision-instruct
OPENAI_API_KEY=          # optional fallback
GROQ_API_KEY=            # Whisper fallback
TAVILY_API_KEY=          # topic fact-check
```

```bash
uv run python api.py                       # http://localhost:8000
cd frontend && npm install && npm run dev  # http://localhost:3000
```

```bash
curl -s http://localhost:8000/api/health
uv run pytest
uv run ruff check .
```

---

## Project structure

```
studio/                 # Product engine (measure → analyze → create)
  config.py             # Settings / env
  factory.py            # Provider switch + fallback + per-role temperature
  metrics.py            # Deterministic measurements (no LLM)
  analyze_text.py       # CreatorStyle
  analyze_visual.py     # EditingProfile
  analyze_thumbnail.py  # ThumbnailAnalysis
  research.py           # Tavily scout (cached)
  create.py             # Hooks + shooting script + quality gates
  script_format.py      # Pipe script → blocks + spoken_copy
  pipeline.py           # Per-creator orchestration (parallel LLM stages)
  parse.py · store.py · limits.py · schemas.py · …
api.py                  # FastAPI (production)
frontend/               # Wizard UI (seeds, light mode, mobile)
data/profiles/          # Seed creators (bryan, jeffnippard, kallaway)
tests/                  # pytest — no API keys required
docs/                   # Innovation, deploy, hackathon demo
```

### API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Status + provider + build id |
| GET | `/api/creators` | Listed / seed creators |
| POST | `/api/ingest` | 1–5 URLs → async job |
| GET | `/api/jobs/{id}` | Job status |
| GET | `/api/profile/{creator}` | Cached profile |
| POST | `/api/hooks` | 10 hooks (+ optional client profile) |
| POST | `/api/copy` | Script payload (`blocks`, `spoken_copy`, word count) |
| POST | `/api/dossier` | Full markdown playbook |
| GET | `/api/usage` | Rate-limit remaining |

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/INNOVATION.md](docs/INNOVATION.md) | Why measured + multimodal + IBM |
| [docs/deployment/DEPLOY_IBM.md](docs/deployment/DEPLOY_IBM.md) | Code Engine deploy |
| [docs/deployment/DEPLOY.md](docs/deployment/DEPLOY.md) | Alternate host notes |
| [AGENTS.md](AGENTS.md) | Contributor / agent rules |
| [DOCUMENTATION_IA.md](DOCUMENTATION_IA.md) | Extended project memory |

---

## How IBM Bob was used

Bob was a **spec-driven build partner**, not a black-box code dump:

- Modular `studio/` engine and provider factory (watsonx primary, OpenAI fallback)
- Structured-output recovery (`parse.py`) and script normalization
- Code Engine deploy, CORS, and free-tier constraints
- Test suite expansion for metrics/schemas without live LLM keys

Product decisions and honesty rules remain human-owned.

---

## License

© 2026 Costa Jr. All rights reserved.  
Shared publicly for review as part of the **IBM AI Builders Challenge (July 2026)**.
