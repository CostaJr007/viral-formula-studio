# Deploy Guide — Viral Formula Studio

Architecture: two Railway services — the **API** (FastAPI + ffmpeg, Docker) and the
**web frontend** (React/TanStack Start, Node). They connect through two env vars:
`VITE_API_URL` (frontend → API) and `ALLOWED_ORIGINS` (API ← frontend).

## 1. API service (backend)

1. Railway → New Project → Deploy from GitHub → pick `viral-formula-studio`.
2. Service settings:
   - **Dockerfile path:** `Dockerfile` (repo root)
   - **Variables:**
     ```
     MODEL_PROVIDER=openai            # switch to watsonx for the submission
     OPENAI_API_KEY=...
     GROQ_API_KEY=...
     TAVILY_API_KEY=...
     ALLOWED_ORIGINS=https://<your-web-service>.up.railway.app
     # IBM (submission):
     IBM_WATSONX_API_KEY=...
     IBM_WATSONX_PROJECT_ID=...
     IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
     ```
   - Generate a public domain → note the URL (e.g. `https://api-production-xxxx.up.railway.app`).

> The image installs ffmpeg, syncs Python deps from `uv.lock` and runs uvicorn on `$PORT`.
> `data/` starts empty — creators are ingested through the UI at runtime.

## 2. Web service (frontend)

1. Same project → New Service → Deploy from the same repo.
2. Service settings:
   - **Root directory:** `frontend`
   - **Dockerfile path:** `frontend/Dockerfile`
   - **Variables:**
     ```
     VITE_API_URL=https://<your-api-service>.up.railway.app
     ```
   - Generate a public domain — this is the URL you share (judges, demo video).

> `VITE_API_URL` is inlined at build time; changing it requires a rebuild (Railway does it
> automatically on variable change → redeploy).

## 3. Smoke test after deploy

1. `https://<api>/api/health` → `{"status":"ok",...}`
2. Open the web URL → Step 1, ingest 1–2 Shorts links of a test creator → Step 2 profile shows
   measured metrics → Step 3 hooks → Step 4 copy.

## Notes

- **Vercel:** postponed. The clean Vercel path needs the nitro `vercel` preset (SSR
  output adapter); the frontend currently runs as a Node server (`vite preview`), which
  Railway hosts with zero extra config. Same public-URL outcome.
- **Cold starts:** on free tiers the first request after idle may take ~30–60s.
- **Demo video fallback:** record the demo locally (`uv run python api.py` + `npm run dev`)
  if the network is unreliable on presentation day.
