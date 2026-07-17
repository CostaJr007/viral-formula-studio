# Viral Formula Studio

**Multimodal reverse engineering of a content creator's viral formula.** Give it a creator (5 short-video links) and your topic — it studies real evidence from the creator's videos (transcripts + frames + deterministic measurements) and delivers a complete, actionable playbook: hook formulas, copy structure, editing grammar and persuasion tactics, transposed to *your* theme, in *your* voice.

> Inspiration, not imitation. Every great creator started by studying someone. We hand you the notebook that used to take months to build.

**IBM AI Builders Challenge — July 2026 · "Reimagine Creative Industries with AI"**

---

## The Problem

Creators, marketers and small businesses all face the same question: *why does that creator's content go viral while mine doesn't?*

The answer exists — but extracting it today is manual and slow: watch dozens of videos, pause, take notes, guess at patterns in the writing, the hooks, the editing rhythm. Existing AI tools skip the study entirely: they generate generic copy that sounds like everyone and no one.

There is no tool that **decodes a specific creator's technique from real, measurable evidence** and turns it into a playbook you can apply to your own content.

## Our Solution

Viral Formula Studio is an analysis engine, not a content generator. You provide **a creator** (up to 5 short-video links, analyzed once) and **your topic**. It returns the complete viralization playbook, grounded in measured evidence:

| Feature | What it does | Engine |
| --- | --- | --- |
| Link ingestion | Downloads public short videos (YouTube Shorts/TikTok), captions-first transcription, Whisper fallback | yt-dlp + Groq Whisper |
| Deterministic metrics | **Measures** cuts/min, avg shot length, words/min, repeated signature expressions (no LLM) | ffmpeg + Python |
| Style analysis | Reverse-engineers the copy/hook fingerprint from real transcripts | LLM (structured output) |
| Editing analysis | Decodes the editing grammar from real video frames | Multimodal LLM |
| Fact-check (scout) | Gathers verified facts about your topic, each with a source URL | Tavily + LLM |
| Viralization dossier | The creator's formula transposed to your topic: voice, hooks, copy structure, editing, persuasion, action plan | Voice model |
| Guided creation | 10 hooks → you pick one → full ≤200-word video copy with editing directions | Voice model |

The same decoded formula also explains why a video *sells*: organic content built on a proven formula becomes a pre-tested ad creative — the organic-to-paid bridge used by top creators.

## AI & Technical Approach

### AI collaboration workflow

This project is developed with **IBM Bob** as the AI development partner, following the spec-driven workflow from the challenge labs: the product was specified up front (scope, dossier contract, honesty rules), and Bob was used in Ask/Plan modes to explore the legacy codebase, design the architecture and implement it module by module — with the human owner reviewing every accept/reject decision.

### Core IBM technology

**IBM Granite on watsonx.ai is the single voice of the product** for the submission. The codebase is provider-agnostic through one factory (`studio/factory.py`): switching providers is a one-line config change (`MODEL_PROVIDER=watsonx`), no agent code changes. watsonx currently offers no Granite vision model, so the frame-analysis stage runs on a supporting vision model while Granite writes everything the user reads — a hybrid pattern with a non-IBM model in a supporting role and Granite as the on-screen voice.

### Live APIs

| API | Purpose |
| --- | --- |
| IBM watsonx.ai (Granite) | Core AI — style/editing analysis and dossier synthesis (submission) |
| OpenAI (GPT-4o) | Prototyping provider + automatic fallback if watsonx fails |
| Groq Whisper | Audio transcription for videos without captions |
| Tavily | Web fact-check (scout stage) with source URLs |

### Why the output is trustworthy

```
STAGE 0 — MEASURE (no LLM): cuts/min, shot length, words/min, n-grams
STAGE 1 — EVIDENCE (cached): CreatorStyle (text) + EditingProfile (frames)
STAGE 2 — SCOUT: verified facts about the topic, with sources
STAGE 3 — COMMENTATOR: dossier/copy grounded ONLY in injected evidence
```

- **Measured, not guessed** — the LLM interprets deterministic measurements instead of estimating them; the dossier cites them ("measured: 17.9 cuts/min").
- **Ground truth injection** — synthesis receives only the extracted profiles and verified facts, never open-ended questions about the creator or topic.
- **Honesty rules** — every prompt instructs the model to declare what evidence could NOT support (`evidence_notes`, `unconfirmed`); weak sections are flagged `[limited evidence]` instead of embellished. Unverifiable data becomes an explicit `[INSERT: ...]` placeholder, never a fabrication.
- **Graceful degradation** — no captions → Whisper; no search → structural mode; provider down → cross-provider fallback with retries. The feature degrades, it never dies.
- **Security & hygiene** — keys only in `.env` (never committed), no client-side exposure, telemetry disabled, per-URL failure isolation, corrupted profiles self-heal.

## Tech Stack

- **Python 3.12** · uv (dependency management)
- **Agno 2.7.3** (agent framework) · **Gradio** (web UI)
- **ffmpeg/ffprobe** (audio extraction, frame sampling, scene-cut detection)
- **yt-dlp** + curl-cffi (link ingestion) · **Groq Whisper** (transcription)
- **Pydantic** (structured outputs everywhere) · **pytest + ruff** (20 tests, lint-clean)

## Why This Matters

The creator economy runs on a craft that today is tacit and manual: understanding *why* a video works. Viral Formula Studio turns that craft into explicit, measurable, transferable knowledge — so a small business or a new creator can learn in minutes what used to take months of study. It reimagines the creative workflow not by replacing the human creator, but by making the masters' technique learnable: the formula migrates, the voice stays yours.

## Running Locally

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), ffmpeg on PATH.

```bash
git clone https://github.com/CostaJr007/viral-formula-studio.git
cd viral-formula-studio
uv sync
```

Create a `.env` file (see `.env.example`):

```bash
MODEL_PROVIDER=openai            # or watsonx (IBM submission)
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key       # transcription fallback
TAVILY_API_KEY=your_tavily_key   # fact-check stage
# IBM watsonx.ai (Granite) — for the submission:
IBM_WATSONX_API_KEY=your_ibm_key
IBM_WATSONX_PROJECT_ID=your_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

Run:

```bash
uv run python app.py     # web UI -> http://localhost:7860
uv run python main.py    # terminal CLI (same engine)
```

Flow: **1 · Criador** (paste up to 5 links → analyze) → **2 · Perfil** (measured formula) → **3 · Ganchos** (10 hooks) → **4 · Copy** (orchestrated script).

## Project Structure

```
studio/
├── config.py          # pydantic-settings: keys, paths, provider switch (single source of truth)
├── factory.py         # the ONLY place that knows the LLM provider + fallback + retries
├── schemas.py         # CreatorStyle / EditingProfile / ResearchReport (Pydantic contracts)
├── store.py           # JSON persistence (transcripts, cached profiles)
├── ingest.py          # link ingestion: yt-dlp, captions-first, Whisper fallback
├── transcribe.py      # local-folder transcription pipeline (incremental saves)
├── frames.py          # ffmpeg frame sampling (480p, uniform)
├── metrics.py         # deterministic measurements: cuts/min, words/min, n-grams (no LLM)
├── analyze_text.py    # agent: transcripts + metrics -> CreatorStyle
├── analyze_visual.py  # agent: frames + metrics -> EditingProfile (multimodal)
├── research.py        # agent: web fact-check -> ResearchReport (scout)
├── dossier.py         # agent: profiles + facts -> viralization playbook (commentator)
├── create.py          # guided flow: 10 hooks -> pick -> orchestrated <=200-word copy
└── pipeline.py        # per-creator orchestration (runs once, cached)
app.py                 # Gradio web UI (4-step wizard)
agent.py               # optional Agno AgentOS interface
main.py                # terminal CLI
tests/                 # 20 tests (schemas, store, real ffmpeg metrics, ingestion, creation)
data/                  # transcripts + cached creator profiles
```

## Testing

```bash
uv run pytest        # 20 tests, incl. real ffmpeg cut detection (no API keys needed)
uv run ruff check .  # lint
```

## Roadmap

- Granite vision for the frame-analysis stage, once a Granite multimodal model lands on watsonx
- Public deploy + 3-minute demo video
- OCR of on-screen text and color-palette analysis (deterministic layer v2)

## License

© 2026 Costa Jr. All rights reserved.
This project is shared publicly for review as part of the IBM AI Builders Challenge (July 2026). No permission is granted to copy, modify, redistribute, or reuse the code or content without the author's explicit written consent.
