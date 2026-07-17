"""Viral Formula Studio — web UI (Gradio).

Wizard flow in 4 steps, one per tab:
1. Creator — add a creator via up to 5 links (YouTube Shorts/TikTok) and analyze
2. Profile — the measured/learned profile of any analyzed creator
3. Hooks   — theme -> 10 hooks from the creator's formula
4. Copy    — pick a hook -> orchestrated <=200-word copy + editing directions

Run: uv run python app.py  ->  http://localhost:7860
"""

import logging

import gradio as gr

from studio import store
from studio.create import generate_copy, generate_hooks
from studio.ingest import ingest_urls
from studio.pipeline import analyze_creator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Backend wrappers (UI <-> studio engine)
# ---------------------------------------------------------------------------


def _creator_choices():
    return gr.update(choices=store.list_creators())


def ui_ingest(name, *links):
    name = (name or "").strip()
    if not name:
        return "❌ Enter the creator's name.", _creator_choices(), _creator_choices()
    urls = [u.strip() for u in links if u and u.strip().startswith("http")]
    if not urls:
        return (
            "❌ Paste at least 1 valid link (YouTube Shorts or TikTok).",
            _creator_choices(),
            _creator_choices(),
        )

    try:
        report = ingest_urls(name, urls)
        lines = [
            f"### Ingestion result\n**{len(report['ok'])} ingested** · {len(report['skipped'])} skipped · {len(report['failed'])} failed"
        ]
        for fail in report["failed"]:
            lines.append(f"- ⚠️ {fail['url']}: {fail['reason']}")

        if report["ok"]:
            lines.append("\n⏳ **Analyzing** (measurement → style → editing)...")
            profile = analyze_creator(name)
            metrics = profile.metrics or {}
            editing, speech = metrics.get("editing", {}), metrics.get("speech", {})
            lines.append(f"\n### ✅ Profile for '{name}' ready")
            lines.append(
                f"**{profile.videos_analyzed} video(s) analyzed** · "
                f"✂️ {editing.get('avg_cuts_per_min', '—')} cuts/min · "
                f"🗣️ {speech.get('avg_wpm', '—')} words/min\n\n"
                "➡️ Go to the **2 · Profile** tab to see the full formula."
            )
        return "\n".join(lines), _creator_choices(), _creator_choices()
    except Exception as e:
        return f"❌ Error: {e}", _creator_choices(), _creator_choices()


def ui_profile(creator):
    if not creator:
        return "Select a creator above."
    profile = store.load_profile(creator)
    if profile is None:
        return f"⚠️ **'{creator}'** has no profile yet — ingest and analyze in the **1 · Creator** tab."

    lines = [
        f"## {profile.creator}'s formula\n**{profile.videos_analyzed} video(s) analyzed** — measured, not estimated.\n"
    ]
    metrics = profile.metrics or {}
    editing_m, speech_m = metrics.get("editing", {}), metrics.get("speech", {})
    if editing_m or speech_m:
        lines.append("### 📐 Measured numbers")
        if editing_m:
            lines.append(
                f"- ✂️ **{editing_m.get('avg_cuts_per_min')} cuts/min** · average shot of **{editing_m.get('avg_shot_length_s')}s**"
            )
        if speech_m:
            lines.append(f"- 🗣️ **{speech_m.get('avg_wpm')} words/min**")
        if metrics.get("signature_ngrams"):
            grams = ", ".join(f"“{g['ngram']}” ({g['count']}x)" for g in metrics["signature_ngrams"][:5])
            lines.append(f"- 💬 Signature expressions: {grams}")
    if profile.style:
        s = profile.style
        lines.append(
            f"\n### ✍️ Style\n- **Tone:** {s.tone}\n- **Rhythm:** {s.sentence_rhythm}\n"
            f"- **Copy structure:** {s.copy_structure}\n"
            "- **Hook patterns:** " + "; ".join(h.pattern for h in s.hook_patterns)
        )
    if profile.editing:
        e = profile.editing
        lines.append(
            f"\n### 🎬 Editing grammar\n- **Cadence:** {e.cut_cadence}\n"
            f"- **On-screen text:** {e.text_overlay_style}\n"
            f"- **B-roll:** {e.b_roll_usage}\n- **Retention:** {', '.join(e.retention_tricks)}"
        )
    return "\n".join(lines)


def ui_hooks(creator, theme):
    if not creator or not theme or not theme.strip():
        return gr.update(choices=[], value=None), [], "⚠️ Enter the creator and the theme."
    try:
        hook_list = generate_hooks(creator, theme.strip())
        choices = [f"{i + 1}. {h.text}  _({h.pattern})_" for i, h in enumerate(hook_list.hooks)]
        return (
            gr.update(choices=choices, value=None),
            [h.text for h in hook_list.hooks],
            f"✅ **{len(hook_list.hooks)} hooks** generated — pick one and go to the **4 · Copy** tab.",
        )
    except Exception as e:
        return gr.update(choices=[], value=None), [], f"❌ Error: {e}"


def ui_copy(creator, theme, selected, hook_texts):
    if not creator or not theme or not theme.strip():
        return "⚠️ Enter the creator and the theme in the **3 · Hooks** tab."
    if not selected or not hook_texts:
        return "⚠️ Generate the hooks and pick one in the **3 · Hooks** tab."
    try:
        index = int(selected.split(".")[0]) - 1
        chosen = hook_texts[index]
    except (ValueError, IndexError):
        return "⚠️ Could not identify the chosen hook — generate the hooks again."

    try:
        copy = generate_copy(creator, theme.strip(), chosen)
        words = len(copy.script.split())
        directions = "\n".join(f"- {d}" for d in copy.editing_directions)
        return (
            f"### 🎬 Chosen hook\n> {chosen}\n\n"
            f"### 📝 Copy · {words} words\n{copy.script}\n\n"
            f"### 🎞️ Editing directions\n{directions}\n\n"
            f"### 🔍 Data notes\n{copy.data_notes}"
        )
    except Exception as e:
        return f"❌ Error: {e}"


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

HERO = """
<div class="hero">
  <div class="hero-title">🎬 Viral Formula Studio</div>
  <div class="hero-sub">Reverse engineering of a creator's viralization formula —
  <b>measured, not guessed</b>. Inspiration, not imitation.</div>
</div>
"""

CSS = """
.gradio-container {max-width: 980px !important; font-family: 'Segoe UI', system-ui, sans-serif;}
.hero {background: linear-gradient(120deg, #3b0764 0%, #7c3aed 60%, #a855f7 100%);
  color: white; border-radius: 16px; padding: 28px 32px; margin-bottom: 18px;}
.hero-title {font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px;}
.hero-sub {opacity: .92; margin-top: 6px; font-size: 1.02rem;}
.step-card {border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px 20px;
  background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,.06);}
.step-title {font-weight: 700; color: #4c1d95; margin-bottom: 4px;}
button.primary {background: #7c3aed !important;}
"""

with gr.Blocks(title="Viral Formula Studio") as demo:
    gr.HTML(HERO)
    hook_texts = gr.State([])

    with gr.Tab("1 · Creator"):
        with gr.Row():
            with gr.Column(scale=1, elem_classes="step-card"):
                gr.Markdown(
                    '<div class="step-title">How it works</div>'
                    "1. Paste up to **5 links** of the creator's short videos (Shorts/TikTok)\n"
                    "2. We download and **measure** cuts, speech rate and expressions\n"
                    "3. AI analyzes style + editing and saves the formula\n\n"
                    "⏱️ Takes ~1 min per video. Runs **once per creator**."
                )
            with gr.Column(scale=2, elem_classes="step-card"):
                gr.Markdown('<div class="step-title">Add creator</div>')
                creator_name = gr.Textbox(label="Creator name", placeholder="e.g.: jeffnippard")
                link_fields = [
                    gr.Textbox(label=f"Link {i + 1}" + (" (required)" if i == 0 else "")) for i in range(5)
                ]
                ingest_btn = gr.Button("Ingest and analyze", variant="primary", elem_classes="primary")
        ingest_out = gr.Markdown()

    with gr.Tab("2 · Profile"):
        with gr.Column(elem_classes="step-card"):
            gr.Markdown('<div class="step-title">The creator\'s learned formula</div>')
            with gr.Row():
                profile_select = gr.Dropdown(label="Creator", choices=store.list_creators(), scale=3)
                refresh_btn = gr.Button("↻ Refresh list", scale=1)
        profile_out = gr.Markdown()

    with gr.Tab("3 · Hooks"), gr.Column(elem_classes="step-card"):
        gr.Markdown('<div class="step-title">10 hooks in the creator\'s formula</div>')
        with gr.Row():
            hooks_creator = gr.Dropdown(label="Creator", choices=store.list_creators(), scale=1)
            theme_input = gr.Textbox(label="Your theme", placeholder="e.g.: the Kimi 3 launch", scale=2)
        hooks_btn = gr.Button("Generate 10 hooks", variant="primary", elem_classes="primary")
        hooks_status = gr.Markdown()
        hooks_radio = gr.Radio(label="Pick the winning hook", choices=[])

    with gr.Tab("4 · Copy"), gr.Column(elem_classes="step-card"):
        gr.Markdown('<div class="step-title">Orchestrated copy (≤200 words) + editing directions</div>')
        copy_btn = gr.Button("Generate orchestrated copy", variant="primary", elem_classes="primary")
        copy_out = gr.Markdown()

    ingest_btn.click(ui_ingest, [creator_name, *link_fields], [ingest_out, profile_select, hooks_creator])
    refresh_btn.click(lambda: (_creator_choices(), _creator_choices()), None, [profile_select, hooks_creator])
    profile_select.change(ui_profile, profile_select, profile_out)
    hooks_btn.click(ui_hooks, [hooks_creator, theme_input], [hooks_radio, hook_texts, hooks_status])
    copy_btn.click(ui_copy, [hooks_creator, theme_input, hooks_radio, hook_texts], copy_out)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Base(primary_hue="violet", neutral_hue="slate"), css=CSS)
