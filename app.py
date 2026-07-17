"""Viral Formula Studio — web UI (Gradio).

Wizard flow in 4 steps, one per tab:
1. Criador  — add a creator via up to 5 links (YouTube Shorts/TikTok) and analyze
2. Perfil   — the measured/learned profile of any analyzed creator
3. Ganchos  — theme -> 10 hooks from the creator's formula
4. Copy     — pick a hook -> orchestrated <=200-word copy + editing directions

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
        return "❌ Informe o nome do criador.", _creator_choices(), _creator_choices()
    urls = [u.strip() for u in links if u and u.strip().startswith("http")]
    if not urls:
        return (
            "❌ Cole pelo menos 1 link válido (YouTube Shorts ou TikTok).",
            _creator_choices(),
            _creator_choices(),
        )

    try:
        report = ingest_urls(name, urls)
        lines = [
            f"### Resultado da ingestão\n**{len(report['ok'])} ingerido(s)** · {len(report['skipped'])} pulado(s) · {len(report['failed'])} falha(s)"
        ]
        for fail in report["failed"]:
            lines.append(f"- ⚠️ {fail['url']}: {fail['reason']}")

        if report["ok"]:
            lines.append("\n⏳ **Analisando** (medição → estilo → edição)...")
            profile = analyze_creator(name)
            metrics = profile.metrics or {}
            editing, speech = metrics.get("editing", {}), metrics.get("speech", {})
            lines.append(f"\n### ✅ Perfil de '{name}' pronto")
            lines.append(
                f"**{profile.videos_analyzed} vídeo(s) analisados** · "
                f"✂️ {editing.get('avg_cuts_per_min', '—')} cortes/min · "
                f"🗣️ {speech.get('avg_wpm', '—')} palavras/min\n\n"
                "➡️ Vá para a aba **2 · Perfil** para ver a fórmula completa."
            )
        return "\n".join(lines), _creator_choices(), _creator_choices()
    except Exception as e:
        return f"❌ Erro: {e}", _creator_choices(), _creator_choices()


def ui_profile(creator):
    if not creator:
        return "Selecione um criador acima."
    profile = store.load_profile(creator)
    if profile is None:
        return f"⚠️ **'{creator}'** ainda não tem perfil — ingira e analise na aba **1 · Criador**."

    lines = [
        f"## Fórmula de {profile.creator}\n**{profile.videos_analyzed} vídeo(s) analisados** — medidos, não estimados.\n"
    ]
    metrics = profile.metrics or {}
    editing_m, speech_m = metrics.get("editing", {}), metrics.get("speech", {})
    if editing_m or speech_m:
        lines.append("### 📐 Números medidos")
        if editing_m:
            lines.append(
                f"- ✂️ **{editing_m.get('avg_cuts_per_min')} cortes/min** · take médio de **{editing_m.get('avg_shot_length_s')}s**"
            )
        if speech_m:
            lines.append(f"- 🗣️ **{speech_m.get('avg_wpm')} palavras/min**")
        if metrics.get("signature_ngrams"):
            grams = ", ".join(f"“{g['ngram']}” ({g['count']}x)" for g in metrics["signature_ngrams"][:5])
            lines.append(f"- 💬 Expressões de assinatura: {grams}")
    if profile.style:
        s = profile.style
        lines.append(
            f"\n### ✍️ Estilo\n- **Tom:** {s.tone}\n- **Ritmo:** {s.sentence_rhythm}\n"
            f"- **Estrutura de copy:** {s.copy_structure}\n"
            "- **Padrões de gancho:** " + "; ".join(h.pattern for h in s.hook_patterns)
        )
    if profile.editing:
        e = profile.editing
        lines.append(
            f"\n### 🎬 Gramática de edição\n- **Cadência:** {e.cut_cadence}\n"
            f"- **Texto na tela:** {e.text_overlay_style}\n"
            f"- **B-roll:** {e.b_roll_usage}\n- **Retenção:** {', '.join(e.retention_tricks)}"
        )
    return "\n".join(lines)


def ui_hooks(creator, theme):
    if not creator or not theme or not theme.strip():
        return gr.update(choices=[], value=None), [], "⚠️ Informe o criador e o tema."
    try:
        hook_list = generate_hooks(creator, theme.strip())
        choices = [f"{i + 1}. {h.text}  _({h.pattern})_" for i, h in enumerate(hook_list.hooks)]
        return (
            gr.update(choices=choices, value=None),
            [h.text for h in hook_list.hooks],
            f"✅ **{len(hook_list.hooks)} ganchos** gerados — escolha um e vá para a aba **4 · Copy**.",
        )
    except Exception as e:
        return gr.update(choices=[], value=None), [], f"❌ Erro: {e}"


def ui_copy(creator, theme, selected, hook_texts):
    if not creator or not theme or not theme.strip():
        return "⚠️ Informe o criador e o tema na aba **3 · Ganchos**."
    if not selected or not hook_texts:
        return "⚠️ Gere os ganchos e escolha um na aba **3 · Ganchos**."
    try:
        index = int(selected.split(".")[0]) - 1
        chosen = hook_texts[index]
    except (ValueError, IndexError):
        return "⚠️ Não consegui identificar o gancho escolhido — gere os ganchos novamente."

    try:
        copy = generate_copy(creator, theme.strip(), chosen)
        words = len(copy.script.split())
        directions = "\n".join(f"- {d}" for d in copy.editing_directions)
        return (
            f"### 🎬 Gancho escolhido\n> {chosen}\n\n"
            f"### 📝 Copy · {words} palavras\n{copy.script}\n\n"
            f"### 🎞️ Direções de edição\n{directions}\n\n"
            f"### 🔍 Notas de dados\n{copy.data_notes}"
        )
    except Exception as e:
        return f"❌ Erro: {e}"


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

HERO = """
<div class="hero">
  <div class="hero-title">🎬 Viral Formula Studio</div>
  <div class="hero-sub">Engenharia reversa da fórmula de viralização de um criador —
  <b>medida, não adivinhada</b>. Inspiração, não imitação.</div>
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

    with gr.Tab("1 · Criador"):
        with gr.Row():
            with gr.Column(scale=1, elem_classes="step-card"):
                gr.Markdown(
                    '<div class="step-title">Como funciona</div>'
                    "1. Cole até **5 links** de vídeos curtos do criador (Shorts/TikTok)\n"
                    "2. Baixamos e **medimos** cortes, ritmo de fala e expressões\n"
                    "3. A IA analisa estilo + edição e salva a fórmula\n\n"
                    "⏱️ Leva ~1 min por vídeo. Roda **uma vez por criador**."
                )
            with gr.Column(scale=2, elem_classes="step-card"):
                gr.Markdown('<div class="step-title">Adicionar criador</div>')
                creator_name = gr.Textbox(label="Nome do criador", placeholder="ex: jeffnippard")
                link_fields = [
                    gr.Textbox(label=f"Link {i + 1}" + (" (obrigatório)" if i == 0 else "")) for i in range(5)
                ]
                ingest_btn = gr.Button("Ingerir e analisar", variant="primary", elem_classes="primary")
        ingest_out = gr.Markdown()

    with gr.Tab("2 · Perfil"):
        with gr.Column(elem_classes="step-card"):
            gr.Markdown('<div class="step-title">A fórmula aprendida do criador</div>')
            with gr.Row():
                profile_select = gr.Dropdown(label="Criador", choices=store.list_creators(), scale=3)
                refresh_btn = gr.Button("↻ Atualizar lista", scale=1)
        profile_out = gr.Markdown()

    with gr.Tab("3 · Ganchos"), gr.Column(elem_classes="step-card"):
        gr.Markdown('<div class="step-title">10 ganchos na fórmula do criador</div>')
        with gr.Row():
            hooks_creator = gr.Dropdown(label="Criador", choices=store.list_creators(), scale=1)
            theme_input = gr.Textbox(label="Seu tema", placeholder="ex: o lançamento do Kimi 3", scale=2)
        hooks_btn = gr.Button("Gerar 10 ganchos", variant="primary", elem_classes="primary")
        hooks_status = gr.Markdown()
        hooks_radio = gr.Radio(label="Escolha o gancho vencedor", choices=[])

    with gr.Tab("4 · Copy"), gr.Column(elem_classes="step-card"):
        gr.Markdown('<div class="step-title">Copy orquestrada (≤200 palavras) + direção de edição</div>')
        copy_btn = gr.Button("Gerar copy orquestrada", variant="primary", elem_classes="primary")
        copy_out = gr.Markdown()

    ingest_btn.click(ui_ingest, [creator_name, *link_fields], [ingest_out, profile_select, hooks_creator])
    refresh_btn.click(lambda: (_creator_choices(), _creator_choices()), None, [profile_select, hooks_creator])
    profile_select.change(ui_profile, profile_select, profile_out)
    hooks_btn.click(ui_hooks, [hooks_creator, theme_input], [hooks_radio, hook_texts, hooks_status])
    copy_btn.click(ui_copy, [hooks_creator, theme_input, hooks_radio, hook_texts], copy_out)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Base(primary_hue="violet", neutral_hue="slate"), css=CSS)
