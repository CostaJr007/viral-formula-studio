# Viral Formula Studio

**Multimodal reverse engineering of a content creator's viral formula.** Give it a creator and your topic — it studies real evidence from the creator's videos (transcripts + frames) and delivers a complete, actionable playbook: copy structure, hook formulas, editing grammar and persuasion tactics, transposed to *your* theme, in *your* voice.

> Inspiration, not imitation. Every great creator started by studying someone. We hand you the notebook that used to take months to build.

**IBM AI Builders Challenge — July 2026 · "Reimagine Creative Industries with AI"**

---

## The Problem

Creators, marketers and small businesses all face the same question: *why does that creator's content go viral while mine doesn't?*

The answer exists — but extracting it today is manual and slow: watch dozens of videos, pause, take notes, guess at patterns in the writing, the hooks, the editing rhythm. Existing AI tools skip the study entirely: they generate generic copy that sounds like everyone and no one.

There is no tool that **decodes a specific creator's technique from real evidence** and turns it into a playbook you can apply to your own content.

## Our Solution

Viral Formula Studio is an analysis engine, not a content generator. You provide:

1. **A creator** (their videos, analyzed once), and
2. **Your topic.**

It returns the **complete viralization dossier** — the creator's formula, grounded in real evidence and transposed to your topic:

- **Who the voice is** — tone, rhythm, persona
- **The hook formula** — their recurring hook patterns, *why* each one works, and 5 hook suggestions for your topic written for *your* voice
- **The copy structure** — their beginning-middle-end map, transposed into a script skeleton for your theme
- **The editing grammar** — cut cadence, framing, on-screen text, b-roll usage, visual identity, retention tricks (extracted from real video frames)
- **Persuasion & CTA** — how they convert attention into action
- **Action plan** — a practical checklist to shoot and edit your video applying the formula

The same decoded formula also explains why a video *sells*: organic content built on a proven formula becomes a pre-tested ad creative — the organic-to-paid bridge used by top creators.

## How It Works — AI Approach & Architecture

```
videos/<creator>/*.mp4
        │
        ├─ audio ──> Groq Whisper (retry, incremental saves) ──> transcripts
        │                                                            │
        └─ ffmpeg ──> 480p frame samples ────────────────┐           │
                                                         ▼           ▼
                              STAGE 1 — EVIDENCE EXTRACTION (runs once per creator)
                              ┌─────────────────────────────────────────────┐
                              │ EditingProfile (vision model, structured)   │
                              │ CreatorStyle  (text model, structured)      │
                              │  -> cached as data/profiles/<creator>.json  │
                              └─────────────────────────────────────────────┘
                                                         │
                              STAGE 2 — SCOUT (per request): web fact-check
                              Verified facts about the topic, each with a
                              source URL (Tavily). Unavailable? The dossier
                              degrades to structural mode — it never dies.
                                                         │
                              STAGE 3 — COMMENTATOR (per request)
                                                         ▼
                    DOSSIER: creator formula x your topic, written by the
                    voice model, grounded ONLY in the injected evidence —
                    facts cite their sources, weak sections say so.
```

- **Measured, not guessed** — a deterministic layer (`studio/metrics.py`) computes real numbers from the files before any LLM runs: cuts/minute and average shot length (ffmpeg scene detection), words/minute (transcript ÷ duration), and repeated signature expressions with counts. The LLM stages *interpret* these measurements instead of estimating them, and the dossier cites them ("measured: 21.3 cuts/min") — proof the output is data-based, not improvised copy.
- **Scout → commentator pipeline** — fact-gathering (web search) is separated from explanation (the dossier), so the writing model never leans on training memory for facts about the topic.
- **Structured outputs everywhere** — every analysis step returns a validated Pydantic model (`CreatorStyle`, `EditingProfile`, `ResearchReport`), never free text. Profiles are computed once and cached, so dossiers are fast and cheap.
- **Ground truth injection** — the synthesis stage receives *only* the extracted profiles and the verified-facts report, never open-ended questions about the creator or the topic.
- **Honesty rules** — every analysis prompt instructs the model to declare what the evidence could *not* support (`evidence_notes`, `unconfirmed`); weak sections are flagged `[limited evidence]` instead of being embellished.
- **Graceful degradation** — no video files, no search key, provider down: each stage degrades explicitly (missing visual section, structural mode, OpenAI fallback) instead of failing or fabricating.
- **Resilience** — native retries on every model call (rate limits) plus an automatic cross-provider fallback.

## Core IBM Technology

**IBM Granite on watsonx.ai is the single voice of the product.** The entire codebase is provider-agnostic through one factory (`studio/factory.py`); switching from the prototyping provider to IBM is a one-line config change — no agent code changes:

```bash
# .env
MODEL_PROVIDER=watsonx
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
IBM_WATSONX_API_KEY=...
IBM_WATSONX_PROJECT_ID=...
```

Both analysis stages and the final dossier run on the configured provider. Prototyping uses OpenAI's multimodal GPT-4o. On watsonx.ai, **IBM Granite is the voice** (text analysis + dossier synthesis), while the frame-analysis stage runs on a supporting vision model (`meta-llama/llama-3-2-11b-vision-instruct`) — watsonx currently offers no Granite vision model. Same hybrid pattern as proven submissions: a non-IBM model in a supporting role, Granite as the single on-screen voice.

## How IBM Bob Was Used

This project was developed with **IBM Bob** as the AI development partner, following the spec-driven workflow from the challenge labs: the product was specified up front (scope, dossier contract, honesty rules), and Bob was used in Ask/Plan modes to explore the legacy codebase, design the new architecture and implement it module by module, with the human owner reviewing every accept/reject decision.

## Responsible AI — Inspiration, Not Imitation

- **Technique, not content.** The dossier decodes *why* something works and how to apply it in your own voice — it never hands over ready-made lines to copy from the creator. Studying a master's technique is how every artist learns; we automate the study, not the plagiarism.
- **Evidence or silence.** The system states plainly when evidence is insufficient rather than fabricating patterns about a real person.
- **Consent-aware demos.** Demos run on creators' content used with permission or our own; the tool analyzes technique and never redistributes source content.

## Running Locally

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), ffmpeg on PATH.

```bash
uv sync
cp .env.example .env   # fill in your keys (see .env.example)
```

1. Add a creator — either way:
   - **By link (recommended):** `python main.py` → option **3** → paste YouTube Shorts / TikTok video URLs (captions-first transcription, Whisper fallback; downloads are low-res on purpose — frames/metrics only).
   - **Manually:** drop mp4 files into `videos/<creator_name>/`, then run option **1**.
2. Generate a dossier: `python main.py` → option **2** → type your topic

> **Platform honesty:** YouTube (incl. Shorts) and TikTok work via public links. Instagram has **no official link access** — ingestion is best-effort and may require login cookies; if it fails, the app tells you to drop the Reels manually into `videos/<creator>/` (one-time per creator).

Optional web UI (Agno AgentOS): `python agent.py` → http://localhost:8000

Dossiers are saved to `output/`.

## Project Structure

```
studio/
├── config.py          # pydantic-settings: keys, paths, provider switch (single source of truth)
├── factory.py         # the ONLY place that knows the LLM provider (OpenAI | watsonx)
├── schemas.py         # CreatorStyle / EditingProfile / CreatorProfile (Pydantic contracts)
├── store.py           # JSON persistence (transcripts, cached profiles)
├── transcribe.py      # Groq Whisper pipeline (retry + incremental saves)
├── frames.py          # ffmpeg frame sampling (480p, uniform)
├── metrics.py         # deterministic measurements: cuts/min, words/min, n-grams (no LLM)
├── analyze_text.py    # agent: transcripts + metrics -> CreatorStyle
├── analyze_visual.py  # agent: frames -> EditingProfile (multimodal)
├── research.py        # agent: web fact-check on the topic -> ResearchReport (scout)
├── dossier.py         # agent: profiles + facts + topic -> final playbook (commentator)
└── pipeline.py        # per-creator orchestration (runs once, cached)
main.py                # CLI
agent.py               # optional AgentOS web UI
tests/                 # pytest (schemas, store, real ffmpeg extraction)
data/                  # transcripts, profiles, frame cache
```

## Testing

```bash
uv run pytest      # 9 tests, incl. real ffmpeg frame extraction (no API keys needed)
uv run ruff check .
```

## Roadmap

- **Granite vision** for the frame-analysis stage, once a Granite multimodal model lands on watsonx.
- **Deploy** + 3-minute demo video for the submission.
- ~~Link-based ingestion (yt-dlp)~~ — **shipped**: option 3 in the CLI (YouTube Shorts / TikTok; Instagram best-effort with manual-upload fallback).
