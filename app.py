"""Viral Formula Studio — web UI (Gradio).

Tabs:
1. Criador — add a creator via up to 5 links (YouTube Shorts/TikTok) and run the analysis
2. Ganchos — theme -> 10 hooks from the creator's measured formula
3. Copy — pick a hook -> orchestrated <=200-word copy with editing directions

Run: uv run python app.py  ->  http://localhost:7860
"""

import logging

import gradio as gr

from studio import store
from studio.create import generate_copy, generate_hooks
from studio.ingest import ingest_urls
from studio.pipeline import analyze_creator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


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
            f"**{len(report['ok'])} ingerido(s)** · {len(report['skipped'])} pulado(s) · {len(report['failed'])} falha(s)"
        ]
        for fail in report["failed"]:
            lines.append(f"- ⚠️ {fail['url']}: {fail['reason']}")

        if report["ok"]:
            lines.append("\n⏳ Analisando (métricas → estilo → edição)...")
            profile = analyze_creator(name)
            metrics = profile.metrics or {}
            editing, speech = metrics.get("editing", {}), metrics.get("speech", {})
            lines.append(
                f"\n✅ **Perfil de '{name}' pronto** — {profile.videos_analyzed} vídeo(s) analisados"
            )
            lines.append(
                f"- ✂️ Cortes: **{editing.get('avg_cuts_per_min', '—')}/min** · take médio **{editing.get('avg_shot_length_s', '—')}s**"
            )
            lines.append(f"- 🗣️ Fala: **{speech.get('avg_wpm', '—')} palavras/min**")
        return "\n".join(lines), _creator_choices(), _creator_choices()
    except Exception as e:
        return f"❌ Erro: {e}", _creator_choices(), _creator_choices()


def ui_profile(creator):
    if not creator:
        return "Selecione um criador."
    profile = store.load_profile(creator)
    if profile is None:
        return f"⚠️ '{creator}' ainda não tem perfil — ingira e analise na aba **Criador**."

    lines = [f"## Perfil de {profile.creator}", f"**{profile.videos_analyzed} vídeo(s) analisados**\n"]
    metrics = profile.metrics or {}
    editing_m, speech_m = metrics.get("editing", {}), metrics.get("speech", {})
    if editing_m:
        lines.append(
            f"### 📐 Métricas medidas\n- Cortes: **{editing_m.get('avg_cuts_per_min')}/min** · take médio **{editing_m.get('avg_shot_length_s')}s**"
        )
    if speech_m:
        lines.append(f"- Fala: **{speech_m.get('avg_wpm')} palavras/min**")
    if metrics.get("signature_ngrams"):
        grams = ", ".join(f"“{g['ngram']}” ({g['count']}x)" for g in metrics["signature_ngrams"][:5])
        lines.append(f"- Expressões de assinatura: {grams}")
    if profile.style:
        s = profile.style
        lines.append(
            f"\n### ✍️ Estilo\n- **Tom:** {s.tone}\n- **Ritmo:** {s.sentence_rhythm}\n- **Estrutura:** {s.copy_structure}"
        )
        lines.append("- **Padrões de gancho:** " + "; ".join(h.pattern for h in s.hook_patterns))
    if profile.editing:
        e = profile.editing
        lines.append(
            f"\n### 🎬 Edição\n- **Cadência:** {e.cut_cadence}\n- **Texto na tela:** {e.text_overlay_style}\n- **Retenção:** {', '.join(e.retention_tricks)}"
        )
    return "\n".join(lines)


def ui_hooks(creator, theme):
    if not creator or not theme or not theme.strip():
        return gr.update(choices=[], value=None), [], "⚠️ Informe o criador e o tema."
    try:
        hook_list = generate_hooks(creator, theme.strip())
        choices = [f"{i + 1}. {h.text} _({h.pattern})_" for i, h in enumerate(hook_list.hooks)]
        status = f"✅ {len(hook_list.hooks)} ganchos gerados — escolha um e vá para a aba **Copy**."
        return gr.update(choices=choices, value=None), [h.text for h in hook_list.hooks], status
    except Exception as e:
        return gr.update(choices=[], value=None), [], f"❌ Erro: {e}"


def ui_copy(creator, theme, selected, hook_texts):
    if not creator or not theme or not theme.strip():
        return "⚠️ Informe o criador e o tema na aba **Ganchos**."
    if not selected or not hook_texts:
        return "⚠️ Gere os ganchos e escolha um na aba **Ganchos**."
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
            f"### 📝 Copy ({words} palavras)\n{copy.script}\n\n"
            f"### 🎞️ Direções de edição\n{directions}\n\n"
            f"### 🔍 Notas de dados\n{copy.data_notes}"
        )
    except Exception as e:
        return f"❌ Erro: {e}"


with gr.Blocks(title="Viral Formula Studio") as demo:
    gr.Markdown(
        "# 🎬 Viral Formula Studio\n"
        "Engenharia reversa da fórmula de viralização de um criador — medida, não adivinhada. "
        "**Inspiração, não imitação.**"
    )
    hook_texts = gr.State([])

    with gr.Tab("1 · Criador"):
        creator_name = gr.Textbox(label="Nome do criador", placeholder="ex: jeffnippard")
        link_fields = [
            gr.Textbox(label=f"Link {i + 1}" + (" (obrigatório)" if i == 0 else " (opcional)"))
            for i in range(5)
        ]
        ingest_btn = gr.Button("Ingerir e analisar", variant="primary")
        ingest_out = gr.Markdown()
        gr.Markdown("---\n### Perfil de um criador já analisado")
        profile_select = gr.Dropdown(label="Criador", choices=store.list_creators())
        profile_out = gr.Markdown()

    with gr.Tab("2 · Ganchos"):
        hooks_creator = gr.Dropdown(label="Criador", choices=store.list_creators())
        theme_input = gr.Textbox(label="Seu tema", placeholder="ex: o lançamento do Kimi 3")
        hooks_btn = gr.Button("Gerar 10 ganchos", variant="primary")
        hooks_status = gr.Markdown()
        hooks_radio = gr.Radio(label="Escolha o gancho", choices=[])

    with gr.Tab("3 · Copy"):
        copy_btn = gr.Button("Gerar copy orquestrada", variant="primary")
        copy_out = gr.Markdown()

    ingest_btn.click(ui_ingest, [creator_name, *link_fields], [ingest_out, profile_select, hooks_creator])
    profile_select.change(ui_profile, profile_select, profile_out)
    hooks_btn.click(ui_hooks, [hooks_creator, theme_input], [hooks_radio, hook_texts, hooks_status])
    copy_btn.click(ui_copy, [hooks_creator, theme_input, hooks_radio, hook_texts], copy_out)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
