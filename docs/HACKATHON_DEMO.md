# Hackathon demo playbook (7-day delivery)

## Judge path (under 90 seconds)

1. Open [bit.ly/viral-studio](https://bit.ly/viral-studio)
2. On the landing, read the **IBM AI Builders** badges + output preview
3. Click **Decode formula** on **jeffnippard** (one tap — no scroll to a global CTA)
4. Profile loads from cache → **Generate 10 hooks**
5. Pick any hook → **Write script** (auto-generates the shooting report)
6. Show: spoken copy, timeline, export `.md`, honesty notes
7. Optional: **New topic** reuses the same creator formula

## Design thinking decisions

| Phase | Insight | UI decision |
|-------|---------|-------------|
| Empathize | Judges have ~2 min; cold starts hurt | Seed one-tap + phased wait + human errors |
| Define | Value = measured formula → shootable artefact | Call-sheet report is the “wow”, not chat text |
| Ideate | Custom URLs compete with demo | Advanced form collapsed by default |
| Prototype | IBM stack was footer-only | Hero badges + stack chips + sidebar credit |
| Test | Extra click before script | Auto-start generation on Script step |

## Pitch one-liners

- **Problem:** Creators guess what works; generic AI invents metrics.
- **Solution:** ffmpeg measures → Granite + Vision decode → script on *your* topic.
- **IBM:** watsonx (Granite 4 + Llama Vision) + Code Engine + Bob.
- **Honesty:** evidence notes and `[INSERT: …]` when facts are unconfirmed.

## 7-day remaining backlog (priority)

### Day 1–2 (ship UX — done in this pass)

- [x] Hero pitch + IBM challenge strip
- [x] Output preview mock
- [x] One-tap seed decode
- [x] Collapse advanced ingest
- [x] Auto-generate script
- [x] Humanized errors
- [x] Step numbering / nav polish

### Day 3–4 (demo reliability)

- [x] Warm-up ping / keep-alive for Code Engine (frontend pings `/api/health` every 4 min)
- [x] Job poll hardened (404 / 8 min timeout / no infinite hang)
- [x] CORS defaults include production web + Code Engine regex
- [x] Profile / hooks / copy coerce client profile with disk fallback
- [ ] Verify all 3 seeds load on production after deploy
- [ ] Record 60–90s screen demo GIF/MP4 for judges offline
- [ ] og:image (screenshot of shooting report)

### Day 5 (story + docs)

- [ ] Submission text: problem → measured approach → IBM services table
- [ ] Short README “Try as judge” section at top (already similar — keep tight)
- [ ] Optional: dossier button on final step if API stable

### Day 6–7 (buffer)

- [ ] Dry-run pitch 3× with timer
- [ ] Fallback path if API down: screenshots + seed JSON in `data/profiles`
- [ ] No new features after day 6 — only bugfixes

## Deploy note

Frontend changes live in `frontend/src/routes/index.tsx`, `__root.tsx`, `styles.css`.
Rebuild & push so Code Engine / CI picks up the new web image.
