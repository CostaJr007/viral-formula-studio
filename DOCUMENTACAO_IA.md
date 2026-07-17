# 🧠 VIRAL FORMULA STUDIO — PROJECT DOCUMENTATION AND MEMORY 🧠

This document guides you — or **any future AI** — through the system architecture, the reasoning behind the decisions, and the current state of the project.

## 🎯 Project Goal (IBM AI Builders Challenge — July/2026)

**Theme:** "Reimagine Creative Industries with AI". **Deadline:** 07/31, 11:59 PM ET.

The product is a **reverse-engineering engine for a creator's viralization formula**:

- **Input:** a creator + a user theme.
- **Output:** a complete dossier (playbook) of *that creator's* formula — copy, hooks (with why they work), editing grammar (cuts, frames, on-screen text, pacing) and persuasion — transposed to the user's theme.
- **Positioning:** INSPIRATION, NOT IMITATION. The formula migrates; the content is the user's. It is the same as a musician transcribing a solo to learn the technique. We never deliver content to copy.
- **Ads:** NOT a product. Only a mention in the pitch (validated organic formula = pre-tested ad creative).

## 🏗 Architecture (v0.2 — complete redesign)

```
videos/<creator>/*.mp4
   ├─ audio → studio/transcribe.py (Groq Whisper, tenacity retry, incremental save) → data/transcriptions.json
   └─ studio/frames.py (ffmpeg, 480p, uniform sampling) → data/frames/
        ↓
STAGE 1 (1x per creator, cached in data/profiles/<creator>.json):
   studio/analyze_text.py   → CreatorStyle (Pydantic, real evidence)
   studio/analyze_visual.py → EditingProfile (multimodal: GPT-4o today, Granite vision at submission)
        ↓
STAGE 2 — SCOUT (on demand): studio/research.py
   Web fact-check of the theme via Tavily → ResearchReport (facts WITH sources + "unconfirmed" list).
   Unavailable (no key/outage/429) → returns None and the dossier degrades to structural mode.
        ↓
STAGE 3 — COMMENTATOR (on demand): studio/dossier.py
   Profiles + verified facts + theme → final dossier (6 sections), single voice of the active provider.
   Facts cite sources; what was not confirmed is stated; nothing comes from the model's memory.
```

Key modules:
- `studio/config.py` — pydantic-settings: keys, paths, tuning. Everything anchored to `Path(__file__)` (goodbye CWD bugs).
- `studio/factory.py` — **the ONLY place that knows the LLM provider**. Switching OpenAI → Granite/watsonx = `MODEL_PROVIDER=watsonx` in .env.
- `studio/schemas.py` — Pydantic contracts; `evidence_notes` fields implement the honesty rule.
- `studio/pipeline.py` — orchestrates the per-creator analysis (transcribe → frames → text + vision → save profile).
- `main.py` — CLI (1: analyze creator · 2: generate dossier). `agent.py` — optional web UI (AgentOS :8000).

## 🔌 Switching to IBM (submission strategy)

1. Fill in `.env`: `MODEL_PROVIDER=watsonx`, `IBM_WATSONX_API_KEY`, `IBM_WATSONX_PROJECT_ID`, `IBM_WATSONX_URL`, `WATSONX_MODEL_ID` (default `ibm/granite-3-8b-instruct`).
2. The `ibm-watsonx-ai` SDK is already a dependency. Agno 2.7.3 has `agno.models.ibm.WatsonX`.
3. No agent changes — they all receive the model via `factory.get_model()` / `factory.get_vision_model()`.
4. **Automatic fallback (implemented and tested):** with any provider ≠ openai and an `OPENAI_API_KEY` present, agno attaches GPT-4o as a fallback (`fallback_models`). If watsonx fails (frozen account, Lite-plan 429s, outage), the agent continues on OpenAI. Tested on 07/17: `MODEL_PROVIDER=watsonx` with a frozen account → the response came via `gpt-4o` automatically.
5. **Real models on watsonx (verified via API on 07/17/2026):** there is NO Granite with vision in the us-south/au-syd/eu-de regions. Voice = `ibm/granite-3-8b-instruct` (us-south); frame analysis = `meta-llama/llama-3-2-11b-vision-instruct` (supporting role — same hybrid pattern as the winner: a non-IBM model supports, Granite is the voice). The id `ibm/granite-vision-4-1-4b` is a HALLUCINATION — do not use.
6. Attention: watsonx Lite has a per-minute concurrency limit (429 errors) — retry with backoff is mandatory on calls.
7. **CURRENT BLOCKER:** IBM Cloud account frozen (`frozen: true` in the IAM token, verified on two keys). Expected errors while frozen: "Failed to verify user profile existence" and "Failed to find the IBMid member in project". Resolve at cloud.ibm.com (Pay-As-You-Go upgrade / verification / support) and re-test.

## ✅ Submission checklist (verified rules)

- [ ] IBM Bob as the main dev tool (already the developer's environment) + "How IBM Bob Was Used" section in the README.
- [ ] Complete the mandatory learning activity on skillsbuild.org.
- [ ] Public repo with README following the rubric standard (done — README.md).
- [ ] Public demo video up to 3 minutes (use local mode — do not depend on the network in the demo).
- [ ] Submit on the BeMyApp platform by 07/31 11:59 PM ET.

## 💾 Decision and change log (v0.5)

- **Link-based ingestion (`studio/ingest.py`):** the user pastes URLs (YouTube Shorts/TikTok) in menu option 3 — yt-dlp downloads at low resolution into `videos/<creator>/`, tries free captions first (own VTT parser) and falls back to Groq Whisper when there are no captions. Feeds the existing structure: frames, metrics and analyses unchanged. **Instagram:** no official link access — best effort; on failure it instructs manual upload (platform honesty documented in the README).
- **Interactive creation flow (simulated and approved by the user):** 10 hooks from the creator's formula → user picks 1 → orchestrated copy ≤200 words (~60s at a measured 179 wpm) with measured editing directions (cut every ~3.1s) and an honesty placeholder for unverified data. To be coded as a post-dossier stage.

## 💾 Decision and change log (v0.4)

- **Deterministic metrics layer (`studio/metrics.py`):** the creator's stylistics are now MEASURED, not estimated — cuts/min and average shot length (ffmpeg scene detection), words/min (transcription ÷ duration), repeated n-grams with counts. Runs BEFORE the agents (pipeline.py), feeds the analysis prompts and the dossier, which cites the numbers ("measured: X cuts/min"). It is the direct answer to the requirement: "output based on data and learning, not AI that only writes copy".
- **UI decision (future frontend):** 5 fixed link fields (one per video, mirroring the 5-per-creator limit). The user pastes one link per field and done — NO "smart paste" of multiple links (decided by the developer). Sources can be mixed (Shorts/TikTok/IG) under the same creator.
- **Recorded decision — no fine-tuning:** small dataset (5-10 videos/creator), it would teach voice imitation (against the positioning) and does not cover editing. Measurement + interpretation wins: white-box, provable and cheap.
- 14 tests (new: real cut_metrics, n-grams with counts, WPM).

## 💾 Decision and change log (v0.3)

- **Winner's pattern (kickoff-buddy) adopted:** scout→commentator pipeline. `studio/research.py` fact-checks the theme via Tavily (facts with sources + "unconfirmed"); `dossier.py` only states what is in that block and cites the sources. No key/failure → degrades to structural mode ("the feature degrades, it never dies").
- **Model resilience:** `retries=3` native to agno on all agents + `fallback_models` (OpenAI covers watsonx failure — tested with the frozen account: the response came via gpt-4o automatically).
- **Security/hygiene:** keys only in `.env` (gitignored), `.env` beats machine variables (the 401 bug), agno telemetry off (`AGNO_TELEMETRY=false`), corrupted profiles self-regenerate, guards against API-error-returned-as-text.
- **Real test (07/17):** kallaway × "Kimi 3" dossier WITH fact-check — 3 verified facts with sources cited inline (llm-stats.com, YouTube, technotrenz.com) vs. structural version without sources. Approved.

## 💾 Decision and change log (v0.2)

- **Removed** (leftovers from the old "imitate the creator's voice" model): `agents/` (base_agent, reels/pas/ideation builders, style_extractor), `prompts/copywriter.md`, `transcripter.py`, `transcription_reader.py`.
- **Bugs fixed from v0.1:** `creators_styles.json` path mismatch (saved in the CWD, read in agents/), `style_extractor` without `load_dotenv`, doc promising a nonexistent `visual_methodology` field, `agent.py` with `show_tool_calls` (nonexistent parameter in agno 2.7.3 — broke on import), emojis breaking the Windows console (cp1252).
- **Migrated data:** `transcriptions.json` → `data/transcriptions.json`.
- **Dossier:** fixed 6-section structure (voice / hook / copy / editing / persuasion / action plan) with honesty rules ("[limited evidence]").
- **Tests:** 9 pytest tests, including real frame extraction via ffmpeg (no API keys needed).

## 🔮 Post-submission roadmap

- Link-based ingestion (yt-dlp): user pastes a YouTube/TikTok URL instead of uploading videos (captions first, Whisper as fallback). Designed, not implemented — check if it makes sense after the submission.
- Public deploy with rate limiting (June winner's pattern).
