# Viral Formula Studio

**Multimodal reverse engineering of a content creator's viral formula.** Paste up to
5 short-video links (YouTube Shorts, TikTok, Instagram Reels) from any creator and
your topic — the AI watches, learns their technique, and delivers an actionable
shooting script with hooks, editing directions, and retention psychology transposed
to *your* theme, in *your* voice.

> Inspiration, not imitation. Every great creator started by studying someone.
> We hand you the notebook that used to take months to build.

🚀 **Live demo (production on IBM Code Engine):** [bit.ly/viral-studio](https://bit.ly/viral-studio)

![Demo](demo.gif)

**Built with IBM technologies:** IBM Bob (architecture & implementation), IBM Granite 4 (language model), Llama 3.2 Vision (frame analysis), IBM watsonx.ai (deployment), IBM Code Engine (serverless hosting).

---

## Problem Statement

Content creators spend months studying successful creators before finding their own
voice. They watch hundreds of videos, manually note hook patterns, editing rhythm,
speech pace, persuasion triggers — and still end up guessing. Marketing teams and
agencies lack a systematic, data-driven method to decode *why* specific short-form
content goes viral and transpose those techniques to a new topic.

Existing AI writing tools generate generic scripts from prompts with no connection
to real creator behavior. They don't *measure* anything — they guess based on the
model's prior training, producing hallucinated claims like "this creator uses fast
cuts" without ever counting a single cut.

---

## Solution

Viral Formula Studio **reverse-engineers the measurable formula behind any creator's
viral videos** and transposes it to the user's own theme and voice.

**How it works:**
1. The user pastes up to 5 short-video links and a topic.
2. The system **measures** (not estimates) editing cadence, speech rate, n-gram
   frequency, and shot structure using deterministic tools (ffmpeg, Python).
3. AI interprets those measurements — text style via Granite 4, visual editing
   grammar via Llama 3.2 Vision — and caches a reusable creator profile.
4. The system generates 10 hooks built from the creator's *measured* patterns,
   a full shooting script with timestamps, shot types, editing directions, and
   the retention psychology behind each choice.

**What makes it different:**
- **Measured, not guessed** — the AI interprets deterministic ffmpeg numbers, never
  invents metrics. Every claim has a source.
- **Multimodal** — text analysis (Granite 4) + frame-by-frame visual analysis
  (Llama 3.2 Vision) + deterministic metrics (ffmpeg/Python). Three layers of
  evidence, not just text.
- **Honesty by design** — every output includes `evidence_notes`, `unconfirmed`
  flags, and `[INSERT: ...]` placeholders. The system states what it doesn't know.
- **Production-deployed** — not a prototype. Live on IBM Cloud Code Engine with
  auto-scaling, rate limiting, and CI/CD via GitHub Actions → Docker Hub → Code Engine.
- **Any creator, any language** — Whisper Large v3 handles 99+ languages; Granite 4
  extracts universal style patterns from native-language transcriptions.

> 📖 For a deep dive into what makes this approach unique, see
> [docs/INNOVATION.md](docs/INNOVATION.md).

---

## Selected Challenge Theme

**IBM AI Builders Challenge — July 2026 · "Reimagine Creative Industries with AI"**

The creative industry's core bottleneck is not *generating* content — it's
*understanding what works and why*. This project reimagines the creator workflow by
turning weeks of manual study into a measured, evidence-based playbook generated in
minutes, powered entirely by the IBM AI stack.

---

## Quick Start (Try it in 2 minutes)

The demo comes with **3 pre-analyzed creators** — no uploads needed:

1. Open **[bit.ly/viral-studio](https://bit.ly/viral-studio)**
2. Creator name: type **`jeffnippard`**
3. Paste a Shorts link (any from [@jeffnippard](https://youtube.com/@jeffnippard)) or skip — the seed data is ready
4. Your topic: type anything, e.g. **`carnivore diet`**
5. Click **"Decode formula"** → instant profile from cache
6. Click **"Generate 10 hooks"** → pick one
7. Click **"Generate script"** → see the full shooting script with timestamps, shot types, and editing directions

> 💡 Want a different topic? Click **"New Topic"** — same creator, new theme, zero re-analysis.

---

## Use Cases

- **Content Creators:** Copy winning strategies from creators in your niche — hooks, pacing, editing rhythm
- **Marketing Teams:** Reverse-engineer viral campaigns and adapt them to your brand voice
- **Influencer Agencies:** Analyze client competitors and generate data-backed scripts in minutes
- **Course Creators:** Study how top educators capture attention and convert viewers
- **Social Teams:** Generate 10 variations of hooks from a single creator's pattern

---

## AI Approach & Architecture

### Pipeline Overview

```
┌──────────────────────┐     ┌─────────────────────────────────┐     ┌──────────────────────┐
│       INPUT          │     │           PIPELINE               │     │       OUTPUT         │
├──────────────────────┤     ├─────────────────────────────────┤     ├──────────────────────┤
│ YouTube Shorts       │ ──▶ │ ① yt-dlp download + transcribe  │ ──▶ │ Creator profile      │
│ TikTok               │     │ ② ffmpeg cuts / WPM / n-grams   │     │ 10 AI hooks          │
│ Instagram Reels      │     │ ③ Granite 4 text style analysis │     │ Shooting script      │
│                      │     │ ④ Llama Vision reads frames      │     │ Editing directions   │
│                      │     │ ⑤ Tavily fact-checks topic       │     │ Retention psychology │
│                      │     │ ⑥ Granite 4 writes final copy    │     │                      │
└──────────────────────┘     └─────────────────────────────────┘     └──────────────────────┘
```

**Example flow:** Creator → Profile → Topic → 10 Hooks → Pick Hook → Copy → Report

**Transcription pipeline:**

```
Raw captions → regex cleanup (HTML entities, contractions) → Granite 4 coherence fix
```

### Four-Stage Evidence Chain

Every output is grounded in **measured evidence**:
- **Stage 0 — MEASURE (no AI):** ffmpeg computes cuts/min, shot length, words/min, n-grams
- **Stage 1 — EVIDENCE (cached):** Granite 4 decodes text style + vision model reads frames
- **Stage 2 — SCOUT:** Tavily + Granite 4 verify facts about the topic with source URLs
- **Stage 3 — COMMENTATOR:** Granite 4 synthesizes a shooting script with timestamps, shot types, editing directions, and retention psychology

### AI Models Deep Dive

<table width="100%">
  <thead>
    <tr>
      <th width="25%">Stage</th>
      <th width="55%">Model</th>
      <th width="20%">Runs On</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>🎤 Transcription</td>
      <td>Whisper Large v3 Turbo</td>
      <td>Groq</td>
    </tr>
    <tr>
      <td>📊 Metrics</td>
      <td>Python + ffmpeg (deterministic, no AI)</td>
      <td>IBM Code Engine</td>
    </tr>
    <tr>
      <td>✍️ Text Analysis</td>
      <td><strong>Granite 4</strong> (<code>ibm/granite-4-h-small</code>)</td>
      <td><strong>IBM watsonx.ai</strong></td>
    </tr>
    <tr>
      <td>👁️ Visual Analysis</td>
      <td><strong>Llama 3.2 11B Vision</strong></td>
      <td><strong>IBM watsonx.ai</strong></td>
    </tr>
    <tr>
      <td>🔍 Fact-Check</td>
      <td><strong>Granite 4</strong> + Tavily</td>
      <td><strong>IBM watsonx.ai</strong></td>
    </tr>
    <tr>
      <td>📝 Hooks & Copy</td>
      <td><strong>Granite 4</strong></td>
      <td><strong>IBM watsonx.ai</strong></td>
    </tr>
    <tr>
      <td>🛡️ Fallback</td>
      <td>GPT-4o</td>
      <td>OpenAI</td>
    </tr>
  </tbody>
</table>

**Granite 4** (`ibm/granite-4-h-small`) is the **single voice** of the product.
Every sentence the user reads — from the creator's style fingerprint to the final
video script — is generated by Granite on watsonx.ai.

**OpenAI GPT-4o** is configured only as an automatic safety net: if watsonx
experiences rate limits or an outage, agents transparently fall back to OpenAI.
In normal operation, all AI traffic goes through IBM watsonx.

### 🏗️ Built on IBM Cloud — 100% End-to-End

| Component | IBM Service |
|---|---|
| **AI Engine** | IBM watsonx.ai (Granite 4 text + Llama 3.2 Vision multimodal) |
| **Hosting** | IBM Cloud Code Engine (serverless, auto-scale) |
| **Registry** | IBM Container Registry (CI/CD pipeline) |
| **Developer AI** | IBM Bob (architecture, implementation, debugging) |

**Every output:** Granite 4 on watsonx.ai
**Every frame analysis:** Llama 3.2 Vision on watsonx.ai
**Every deployment:** Code Engine container

### Production Status

This is **not a prototype** — the system is deployed and serving real traffic:

- **API:** `vfs-api` on IBM Code Engine (us-south), serverless, scales 0→2 instances
- **Web:** `vfs-web` on IBM Code Engine, React 19 SSR
- **CI/CD:** GitHub Actions → Docker Hub → Code Engine (automatic on push to `main`)
- **Rate limiting:** IP-based, max 8 creator analyses + 8 dossier exports per IP/hour
- **Seed data:** 3 pre-analyzed creators baked into the Docker image for instant demo
- **Cold start:** ~30s on free tier (min-scale 0); set min-scale 1 on demo day

### Infrastructure & Feasibility

**Production Environment:**
- **Hosting:** IBM Cloud Code Engine (auto-scaling, free tier, $0 when idle)
- **Pipeline:** GitHub → Docker Hub (via GitHub Actions) → Code Engine auto-deploy
- **Rate Limiting:** Per-IP rate limiter in production (measured, not guessed)
- **Database:** SQLite (local dev) + persistent volume (Code Engine)
- **CDN:** Code Engine's built-in edge caching for static assets

**Why This Stack:**
- Video processing (ffmpeg, yt-dlp) runs only when needed → serverless cost efficiency
- No infrastructure lock-in — can redeploy to Railway, Render, or on-prem in <1 hour
- All credentials stored in environment variables, never in code (`.env` + `.gitignore`)
- CI/CD tested and live since July 14, 2026

**Live URL:** [bit.ly/viral-studio](https://bit.ly/viral-studio) (production Code Engine deployment)

For detailed deployment instructions, see [docs/deployment/DEPLOY_IBM.md](docs/deployment/DEPLOY_IBM.md).

---

## How IBM Bob Was Used

IBM Bob was the AI development partner throughout the entire project lifecycle —
from architecture design through implementation, debugging, and documentation. All
code decisions were made by the human developer; Bob served as a spec-driven
assistant that accelerated the build process while maintaining code quality and
architectural consistency.

### Bob's Contributions by Module

| Module / Decision | How Bob Helped Specifically |
|---|---|
| **`studio/` modular engine** | Bob analyzed the legacy codebase (flat `agents/`, `prompts/`, `transcripter.py`) in Ask/Plan modes and proposed the modular `studio/` package structure with clear separation: `config`, `factory`, `schemas`, `pipeline`, `store`, plus per-stage modules. |
| **`studio/factory.py`** | Bob designed the provider-switch pattern (`MODEL_PROVIDER=watsonx` in `.env`) so that swapping OpenAI → Granite requires zero agent changes. Bob also designed the automatic fallback mechanism (`fallback_models`) — tested live on 07/17 when a frozen watsonx account triggered seamless GPT-4o fallback. |
| **`studio/config.py`** | Bob identified and fixed the CWD path bug from v0.1: the old code used relative paths that broke when run from different directories. Bob anchored all paths to `Path(__file__).resolve().parent.parent` and designed the `.env`-beats-machine-env priority to prevent stale API keys from shadowing the project `.env`. |
| **`studio/parse.py`** | Bob diagnosed the watsonx `max_tokens=1024` truncation issue — Granite's default token limit was cutting `CreatorStyle` JSON mid-object, crashing the pipeline. Bob designed the resilient `coerce_structured()` parser that recovers Pydantic output from raw strings, markdown-fenced JSON, and truncated responses. |
| **`studio/pipeline.py`** | Bob proposed the scout → commentator pipeline pattern (inspired by the June 2026 challenge winner, Kickoff Buddy): deterministic measurements first, then LLM interpretation, then fact-check, then synthesis. This became the four-stage architecture. |
| **`studio/schemas.py`** | Bob implemented the honesty rule: every Pydantic schema includes `evidence_notes` fields so the model must state what the available evidence could NOT support — preventing hallucinated claims about creators. |
| **`studio/metrics.py`** | Bob assisted in building the deterministic metrics layer: ffmpeg scene detection for cuts/min, audio duration for WPM, and regex-based n-gram extraction with counts — all running before any LLM to feed measured numbers into the analysis prompts. |
| **`studio/limits.py`** | Bob designed the IP-based rate limiter to protect the watsonx Lite plan's RPM limits in production — max 8 distinct creator analyses + 8 dossier exports per IP per hour. |
| **`studio/ingest.py`** | Bob assisted module-by-module with the link-based ingestion flow: yt-dlp download, captions-first transcription strategy (free YouTube captions before Groq Whisper fallback), and platform-honest error handling (Instagram documented as best-effort). |
| **watsonx `max_tokens` fix** | After the truncation crash, Bob recommended setting `max_tokens=4096` explicitly in `factory.py` — Granite defaults to 1024, which truncates structured JSON for `CreatorStyle` and `HookList` schemas. |
| **IBM Code Engine deploy** | Bob optimized the Code Engine deployment configuration: two apps (`vfs-api` + `vfs-web`), min-scale 0 to stay within free tier, and the `ALLOWED_ORIGINS` / `VITE_API_URL` environment variable handshake between services. |
| **Test suite** | Bob contributed to the test suite expansion from 9 tests (v0.2) to 25 tests (v0.6), including tests for real `cut_metrics`, n-gram counts, WPM calculations, resilient JSON parsing, and schema validation — all runnable without API keys. |
| **Documentation** | Bob contributed to the technical documentation structure (README, AGENTS.md, DOCUMENTATION_IA.md), ensuring it follows the challenge rubric and clearly explains the multimodal AI architecture. |

### How Bob Accelerated Development

The entire project — from architectural redesign to production deployment — was built in 3 phases with Bob as the AI pair:

1. **Phase 1 (Brainstorm & Architecture):** Bob analyzed the legacy flat structure, proposed the modular `studio/` package design, and drafted the scout→commentator pipeline pattern.
2. **Phase 2 (Implementation & Debugging):** Bob wrote the initial implementations of each module, debugged the `max_tokens` truncation issue, designed the resilient `parse.py` recovery, and built the fallback mechanism.
3. **Phase 3 (Production & Polish):** Bob assisted with Code Engine deployment config, test suite expansion (9 → 25 tests), and documentation structure to match the challenge rubric.

**Key outcomes:**
- Modular `studio/` engine: 16 focused modules, <10KB each, zero code duplication across UI layers
- Robust error handling: Graceful fallbacks for rate limits, timeouts, truncated LLM output
- 25 deterministic tests (no API keys required) covering the measurement layer, parsing, and schemas
- Zero external vision APIs (Llama Vision via watsonx.ai keeps everything in the IBM ecosystem)

**Not just code generation:** Bob participated in design decisions, not just syntax. Example: the four-stage pipeline (MEASURE → EVIDENCE → SCOUT → COMMENTATOR) emerged from Bob's proposal to separate deterministic metrics from LLM interpretation.

---

## Honesty by Design

- **Measured, not guessed** — the AI interprets deterministic ffmpeg numbers
- **Ground truth injection** — synthesis only receives extracted profiles and verified facts
- **Honesty rules** — every prompt requires `evidence_notes`, `unconfirmed`, and `[INSERT: ...]` placeholders
- **Graceful degradation** — no captions → Whisper; no search → structural mode; provider down → fallback

### Any Creator, Any Language

The pipeline masters creators from any country, in any language:

- **Transcription:** Whisper Large v3 handles 99+ languages. YouTube auto-captions tried first.
- **Text analysis:** Granite 4 reads native-language transcriptions and extracts universal style patterns.
- **Visual analysis:** Editing grammar is language-independent — the vision model reads frames.
- **Output:** Analysis in English, creator's expressions preserved in original.

### Security & Rate Limiting

- **IP-based rate limiting:** max 8 new creator analyses + 8 dossier exports per IP/hour
- **Seed creators** (Bryan, jeffnippard, kallaway) are exempt — unlimited demo usage
- **WatsonX token cap:** `max_tokens=4096` prevents structured JSON truncation
- **Resilient parsing:** `studio/parse.py` recovers Pydantic output from raw/fenced/truncated JSON

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Runtime | IBM watsonx.ai (Granite 4 + Llama 3.2 Vision) |
| Backend | Python 3.12, FastAPI, Pydantic, Agno 2.7 |
| Frontend | React 19, Vite, TanStack Start, Tailwind 4, shadcn/ui |
| Transcription | Groq Whisper Large v3 Turbo |
| Media | ffmpeg/ffprobe (scene detection, frame sampling) |
| Ingestion | yt-dlp (YouTube Shorts, TikTok, Instagram Reels) |
| Fact-Check | Tavily Search API |
| Hosting | IBM Cloud Code Engine (serverless containers) |
| CI/CD | GitHub Actions → Docker Hub → Code Engine |
| Testing | pytest (25 tests), ruff |
| Responsive | Mobile-first design — works on phones, tablets, and desktop |

---

## Running Locally

```bash
git clone https://github.com/CostaJr007/viral-formula-studio.git
cd viral-formula-studio
uv sync
```

Create `.env` from `.env.example`:

```bash
MODEL_PROVIDER=watsonx
IBM_WATSONX_API_KEY=your_key
IBM_WATSONX_PROJECT_ID=your_project
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-4-h-small
OPENAI_API_KEY=your_key             # fallback only
GROQ_API_KEY=your_key               # transcription
TAVILY_API_KEY=your_key             # fact-checking
```

```bash
uv run python api.py                      # Backend → http://localhost:8000
cd frontend && npm install && npm run dev # Frontend → http://localhost:3000
```

## Project Structure

```
studio/
├── config.py          # pydantic-settings: keys, paths, provider switch
├── factory.py         # ONLY place that knows the LLM provider + fallback
├── schemas.py         # Pydantic contracts (CreatorStyle, EditingProfile, etc.)
├── limits.py          # IP rate limiter (8 creators/IP + 8 dossiers/creator)
├── parse.py           # Resilient structured-output recovery (JSON → Pydantic)
├── store.py           # JSON persistence (transcripts, cached profiles)
├── ingest.py          # Link ingestion: yt-dlp, captions-first, Whisper fallback
├── transcribe.py      # Transcription pipeline + LLM coherence fix
├── frames.py          # ffmpeg frame sampling (480p, uniform)
├── metrics.py         # Deterministic: cuts/min, WPM, n-grams (no LLM)
├── analyze_text.py    # Agent: transcripts + metrics → CreatorStyle
├── analyze_visual.py  # Agent: frames + metrics → EditingProfile (multimodal)
├── research.py        # Agent: web fact-check → ResearchReport
├── dossier.py         # Agent: profiles + facts → viralization playbook
├── create.py          # Guided flow: 10 hooks → pick → shooting script
└── pipeline.py        # Per-creator orchestration (runs once, cached)
api.py                 # FastAPI backend (production)
app.py                 # Gradio UI (quick local demos)
main.py                # Terminal CLI
frontend/              # React 19 + Vite + TanStack Start (5-step wizard)
tests/                 # 25 pytest tests
data/                  # Transcripts + cached creator profiles
```

## Testing

```bash
uv run pytest          # 25 tests (no API keys needed)
uv run ruff check .    # lint
```

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check — returns active provider (`watsonx`) |
| `GET /api/creators` | List analyzed creators |
| `POST /api/ingest` | Start analysis (5 URLs → job) |
| `GET /api/jobs/{id}` | Poll analysis progress |
| `GET /api/profile/{creator}` | Cached creator profile (survives restarts via frontend cache) |
| `POST /api/hooks` | Generate 10 hooks in creator's style |
| `POST /api/copy` | Generate shooting script with timestamps + directions |
| `POST /api/dossier` | Export viralization playbook |
| `GET /api/usage` | Rate limit status |

---

## Documentation

| Document | Description |
|---|---|
| [docs/INNOVATION.md](docs/INNOVATION.md) | Deep dive into what makes this approach unique — measured foundation, multimodal processing, IBM ecosystem mastery, honesty layer |
| [docs/deployment/DEPLOY_IBM.md](docs/deployment/DEPLOY_IBM.md) | Step-by-step IBM Cloud Code Engine deployment guide (production) |
| [docs/deployment/DEPLOY.md](docs/deployment/DEPLOY.md) | Railway deployment guide (alternative/fallback) |
| [DOCUMENTATION_IA.md](DOCUMENTATION_IA.md) | Full project memory — architecture decisions, change log, and IBM switching strategy |
| [AGENTS.md](AGENTS.md) | Guidance for AI agents and human contributors working on this repo |

---

## License

© 2026 Costa Jr. All rights reserved. Shared publicly for review as part of the
IBM AI Builders Challenge (July 2026).
