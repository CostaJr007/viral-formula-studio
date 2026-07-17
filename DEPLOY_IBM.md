# Deploy Guide (IBM Cloud) — Viral Formula Studio

**Full IBM stack:** IBM Bob (dev) + Granite 4 on watsonx.ai (voice) + **IBM Cloud Code Engine (hosting)**.
Verified working on 07/17/2026: Code Engine API accessible and resource group `Default` is ACTIVE.

## Architecture

Two Code Engine applications in one project (region: **Dallas / us-south**, same as the watsonx project):

| App | Source | Dockerfile | Port | Notes |
|-----|--------|-----------|------|-------|
| `vfs-api` | repo root | `Dockerfile` | 8000 | FastAPI + ffmpeg |
| `vfs-web` | `frontend/` | `frontend/Dockerfile` | 4173 | React UI (vite preview) |

## Step 0 — One-time prerequisites

1. IBM Cloud console → **Container Registry** → create a free namespace (e.g. `vfs`) — Code Engine stores the built images there.
2. Have the repo public: `https://github.com/CostaJr007/viral-formula-studio` (already is).

## Step 1 — Create the Code Engine project

Console → **Code Engine** → **Projects** → **Create**:
- Name: `viral-formula-studio` · Resource group: `Default` · Region: `us-south`

## Step 2 — Deploy `vfs-api`

Inside the project → **Applications** → **Create**:
- Name: `vfs-api`
- **Build from source code**: Code repository = the GitHub URL · Branch: `main`
- Build strategy: **Dockerfile** · Dockerfile path: `Dockerfile` · Context: `/`
- Output: your Container Registry namespace
- Runtime: port **8000** · min instances **0** (scales to zero, saves free quota; ~30s cold start) · max **2**
- **Environment variables** (from `.env.example`):
  ```
  MODEL_PROVIDER=watsonx
  IBM_WATSONX_API_KEY=...
  IBM_WATSONX_PROJECT_ID=983863c7-...   (your us-south project)
  IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
  WATSONX_MODEL_ID=ibm/granite-4-h-small
  OPENAI_API_KEY=...                    (automatic fallback)
  GROQ_API_KEY=...
  TAVILY_API_KEY=...
  ALLOWED_ORIGINS=https://<vfs-web-url>  (fill after Step 3)
  ```
- Create → wait for the build + deploy → copy the **application URL** (e.g. `https://vfs-api.xxxx.us-south.codeengine.appdomain.cloud`).
- Smoke test: `GET <url>/api/health` → `{"status":"ok","provider":"watsonx"}`

## Step 3 — Deploy `vfs-web`

Same flow, with:
- Name: `vfs-web` · Dockerfile path: `frontend/Dockerfile` · Context: `frontend/`
- **Build argument:** `VITE_API_URL=https://<vfs-api-url>` (the URL from Step 2 — it is inlined at build time; if the console does not offer build args, edit `frontend/Dockerfile`'s `ARG VITE_API_URL=` default before pushing)
- Runtime port: **4173** · min 0 · max 2
- Copy the web application URL — **this is the public link for judges/demo**.

## Step 4 — Close the loop

Set `ALLOWED_ORIGINS=https://<vfs-web-url>` on `vfs-api` (update env var → new revision), then run the full flow on the public URL: ingest 2 Shorts links → profile with measured metrics → 10 hooks → copy.

## CLI alternative (once `ibmcloud` CLI is installed)

```bash
ibmcloud login --apikey <API_KEY> -r us-south -g Default
ibmcloud plugin install code-engine
ibmcloud ce project create --name viral-formula-studio
ibmcloud ce project select --name viral-formula-studio
# then create build configs + applications mirroring the console values above
ibmcloud ce application create --name vfs-api --build-source https://github.com/CostaJr007/viral-formula-studio \
  --strategy dockerfile --dockerfile Dockerfile --port 8000 --min-scale 0 --max-scale 2
```

## Notes

- **Free tier** covers demo scale; min-scale 0 avoids idle burn (accept ~30s cold starts) — set min-scale 1 on presentation day for instant responses.
- `data/` starts empty in the containers: ingest creators through the UI at runtime.
- If the account hits any provisioning limit (it shows `frozen` in IAM but Code Engine + watsonx are responding), Railway remains the fallback — see `DEPLOY.md`.
