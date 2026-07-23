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
1. The user picks a seed creator **or** pastes up to 5 short-video links (any slot) + a topic.
2. The system **measures** (not estimates) editing cadence, speech rate, n-gram
   frequency, and shot structure using deterministic tools (ffmpeg, Python).
3. AI interprets those measurements — text style via Granite 4, visual editing
   grammar via Llama 3.2 Vision — and caches a reusable creator profile.
4. The system generates 10 hooks from the creator's *measured* patterns, then a
   **~60–90s** shooting script (**~170–200 spoken words**) with timestamps, shot types,
   editing directions, and retention psychology — for *your* topic, in *your* voice.

**What makes it different:**
- **Measured, not guessed** — the AI interprets deterministic ffmpeg numbers, never
  invents metrics. Every claim has a source.
- **Multimodal** — text analysis (Granite 4) + frame-by-frame visual analysis
  (Llama 3.2 Vision) + deterministic metrics (ffmpeg/Python). Three layers of
  evidence, not just text.
- **Honesty by design** — every output includes `evidence_notes`, `unconfirmed`
  flags, and `[INSERT: ...]` placeholders. The system states what it doesn't know.
- **Speech hygiene** — URL/API error blobs are filtered so signature phrases never
  become junk like `https` / `quota` / `ibm` from failed requests.
- **Production-deployed** — live on IBM Cloud Code Engine with auto-scaling, rate
  limiting, and CI/CD via GitHub Actions → Docker Hub → Code Engine.
- **Any creator, any language** — Whisper Large v3 handles 99+ languages; Granite 4
  extracts universal style patterns from native-language transcriptions.
- **Product-first UI** — clean wizard + call-sheet report; IBM credit as
  *Powered by IBM Granite* in the footer (not plastered on every screen).

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

The demo ships with **3 pre-analyzed creators** — no uploads needed:

1. Open **[bit.ly/viral-studio](https://bit.ly/viral-studio)**
2. Click a seed card (**Bryan**, **jeffnippard**, or **kallaway**) — or type the name
3. Topic is prefilled (edit freely), e.g. **`carnivore diet`**
4. Click **"Decode formula"** → cached profile (metrics + style + editing)
5. **"Generate 10 hooks"** → pick one
6. **"Generate script"** → call-sheet report (~170–200 spoken words, ~60–90s short)

> 💡 **New Topic** reuses the same creator with zero re-analysis.  
> 💡 Custom links: paste **one or more** public YouTube Shorts in **any** URL row (empty rows are fine).  
> 💡 Prefer Shorts with real speech; captions or `GROQ_API_KEY` (Whisper) required for new creators.

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
│                      │     │ ⑤ Llama Vision reads thumbnail   │     │ Retention psychology │
│                      │     │ ⑥ Tavily fact-checks topic       │     │ Thumbnail analysis   │
│                      │     │ ⑦ Granite 4 writes final copy    │     │                      │
└──────────────────────┘     └─────────────────────────────────┘     └──────────────────────┘
```

**Example flow:** Creator → Profile → Topic → 10 Hooks → Pick Hook → Copy → Report

**Transcription pipeline:**

```
Raw captions → regex cleanup (HTML entities, contractions) → Granite 4 coherence fix
```

### Multi-Agent Orchestration

The system does not rely on a single monolithic prompt. Instead, it employs an **orchestrated multi-agent architecture** where specialized personas work in sequence or parallel, each with a narrow, well-defined scope:

1. **The Textual Analyst (Agent 4.1):** Reads transcriptions and metrics to extract the creator's copywriting fingerprint, tone, and hook patterns.
2. **The Visual Editor (Agent 4.2):** Analyzes video frames to decode the creator's editing grammar, cut cadence, and visual retention tricks.
3. **The Thumbnail Analyst (Agent 4.5):** Evaluates the first frame for composition, color palette, and click-through effectiveness.
4. **The Fact-Checker / Scout (Agent 5.1):** Acts as an independent researcher, browsing the web to find verified facts about the user's chosen topic.
5. **The Content Strategist / Commentator (Agent 5.2):** The final orchestrator. It receives the outputs from all previous agents (text profile, visual profile, thumbnail data, and verified facts) and synthesizes the final actionable playbook.

This separation of concerns ensures that the final script is based on *real evidence* and verified facts rather than a single LLM hallucinating both the style and the content simultaneously.

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

IBM Bob acted as a core development partner throughout the project, accelerating the build process while ensuring architectural consistency. Instead of just generating code, Bob was used as a spec-driven assistant for system design, debugging, and infrastructure planning.

**Key Contributions:**

- **Architecture Restructuring:** Transitioned the legacy flat codebase into a modular, decoupled engine (`studio/` package) with clear boundaries for configuration, parsing, and state management.
- **Resilience & Fallbacks:** Designed the provider-switch pattern for seamless IBM watsonx integration and implemented the automatic fallback mechanism to handle rate limits and outages.
- **Debugging Complex LLM Issues:** Diagnosed and fixed edge cases like the `max_tokens` truncation issue that broke structured JSON outputs, implementing a robust recovery parser.
- **Deployment Optimization:** Assisted with the IBM Cloud Code Engine deployment, optimizing container configurations to stay within the serverless free tier while managing cross-origin environments.
- **Testing & Quality Assurance:** Expanded the test suite significantly to ensure deterministic measurements and schema validations worked perfectly without requiring API keys.

Bob's role was strictly collaborative: all final code decisions and business logic were defined by the human developer, while Bob executed the implementation details and proposed structural best practices.

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
| Testing | pytest, ruff |
| Responsive | Mobile-first — phones, tablets, desktop |

### Script length (product default)

| Setting | Value |
|---|---|
| Spoken words | **~170–200** (target ~185, hard cap 200) |
| Intended duration | **~60–90 seconds** (Shorts / Reels) |
| Timeline blocks | **6–9** |

---

## Running Locally

```bash
git clone https://github.com/CostaJr007/viral-formula-studio.git
cd viral-formula-studio
uv sync
```

Create `.env` from `.env.example` (never commit secrets):

```bash
MODEL_PROVIDER=watsonx
IBM_WATSONX_API_KEY=your_key
IBM_WATSONX_PROJECT_ID=your_project
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-4-h-small
WATSONX_VISION_MODEL_ID=meta-llama/llama-3-2-11b-vision-instruct
OPENAI_API_KEY=your_key             # automatic fallback only
GROQ_API_KEY=your_key               # Whisper when captions fail
TAVILY_API_KEY=your_key             # fact-checking
```

```bash
uv run python api.py                      # Backend → http://localhost:8000
cd frontend && npm install && npm run dev # Frontend → http://localhost:3000
```

Smoke-check API:

```bash
curl -s http://localhost:8000/api/health
# {"status":"ok","provider":"watsonx","build":"..."}
```

## Project Structure

```
studio/
├── config.py            # pydantic-settings: keys, paths, provider switch
├── factory.py           # ONLY place that knows the LLM provider + fallback
├── schemas.py           # Pydantic contracts (CreatorStyle, EditingProfile, etc.)
├── limits.py            # IP rate limiter
├── parse.py             # Resilient structured-output recovery
├── store.py             # JSON persistence (+ heals legacy empty fingerprints)
├── text_quality.py      # Speech vs URL/API-error filters (n-grams / ingest)
├── script_format.py     # Normalize pipe scripts → spoken_copy + blocks
├── ingest.py            # yt-dlp, captions-first, Whisper fallback
├── transcribe.py        # Transcription helpers
├── frames.py            # ffmpeg frame sampling
├── metrics.py           # Deterministic cuts/min, WPM, n-grams
├── analyze_text.py      # Transcripts + metrics → CreatorStyle
├── analyze_visual.py    # Frames → EditingProfile
├── analyze_thumbnail.py # First frame → ThumbnailAnalysis
├── research.py          # Fast Tavily HTTP fact-check
├── dossier.py           # Viralization playbook
├── create.py            # Hooks + shooting script (length targets)
└── pipeline.py          # Per-creator orchestration
api.py                   # FastAPI backend (production)
app.py                   # Gradio UI (local demos)
main.py                  # Terminal CLI
frontend/                # React 19 + Vite + TanStack Start wizard
tests/                   # pytest suite (no live API keys required)
data/                    # Seed transcripts + creator profiles
```

## Testing

```bash
uv run pytest          # unit/integration tests (no API keys needed)
uv run ruff check .    # lint
```

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health + provider + `build` stamp (verify deploys) |
| `GET /api/creators` | List analyzed creators |
| `POST /api/ingest` | Start analysis (1–5 URLs → job; any slot OK) |
| `GET /api/jobs/{id}` | Poll analysis progress / errors |
| `GET /api/profile/{creator}` | Cached creator profile |
| `POST /api/hooks` | Generate 10 hooks in creator's technique |
| `POST /api/copy` | Shooting script (~170–200 spoken words + blocks) |
| `POST /api/dossier` | Export viralization playbook |
| `GET /api/usage` | Rate limit status |

### Production env (Code Engine `vfs-api`)

Set the same keys as `.env` on the **API** app only. Frontend needs `VITE_API_URL` at **build** time. After deploy, confirm:

```bash
curl -s https://<vfs-api-url>/api/health
# must include "build" and "provider":"watsonx"
```

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

## Cross-Platform Video Support

The ingestion engine is natively platform-agnostic and supports videos from **YouTube Shorts**, **TikTok**, **Instagram Reels**, and **X/Twitter**.

*   **Cloud Deployment Note:** When deploying to public cloud services (like IBM Cloud Code Engine), platforms with aggressive anti-bot protections (TikTok/Instagram) may block datacenter IPs. For these platforms, it is recommended to run the engine locally, pass a local browser `cookies.txt` file, or manually download the `.mp4` files and place them directly into the `/videos` directory for processing. YouTube Shorts are generally accessible without restrictions in the cloud.

---

## License

© 2026 Costa Jr. All rights reserved. Shared publicly for review as part of the
IBM AI Builders Challenge (July 2026).
