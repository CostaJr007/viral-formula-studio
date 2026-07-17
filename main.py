"""Viral Formula Studio — CLI entry point.

Flow: pick a creator -> run the analysis once (text + vision) -> ask for a theme
-> receive the complete viralization dossier, grounded in real evidence.
"""

import logging
import re

from studio import store
from studio.config import get_settings
from studio.dossier import generate_dossier
from studio.ingest import ingest_urls
from studio.pipeline import analyze_creator

BANNER = (
    "=" * 64
    + """
  VIRAL FORMULA STUDIO
  Engenharia reversa da fórmula de viralização de um criador —
  copy, ganchos e gramática de edição, transpostos para o seu tema.
  Inspiração, não imitação.
"""
    + "=" * 64
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "tema"


def pick_creator(creators: list[str]) -> str | None:
    print(f"\nCriadores disponíveis: {', '.join(creators)}")
    creator = input("Nome do criador: ").strip()
    if creator not in creators:
        print(f"[ERRO] '{creator}' não encontrado. Confira a lista acima.")
        return None
    return creator


def run_analysis() -> None:
    creators = store.list_creators()
    if not creators:
        print("\n[!] Nenhum criador encontrado. Adicione vídeos em videos/<criador>/ primeiro.")
        return
    creator = pick_creator(creators)
    if not creator:
        return

    print(f"\nAnalisando '{creator}' (transcricao -> frames -> estilo + edicao)...\n")
    try:
        profile = analyze_creator(creator)
    except Exception as e:
        print(f"\n[ERRO] Falha na análise: {e}")
        return

    print("\n" + "=" * 64)
    print(f"[OK] Perfil de '{creator}' atualizado ({profile.videos_analyzed} vídeos analisados)")
    print(f"  Análise textual: {'ok' if profile.style else '--'}")
    print(f"  Análise visual:  {'ok' if profile.editing else '--'}")
    print(f"  Salvo em: {store.profile_path(creator)}")
    print("=" * 64)


def run_dossier() -> None:
    creators = store.list_creators()
    if not creators:
        print("\n[!] Nenhum criador encontrado. Analise um criador primeiro (opção 1).")
        return
    creator = pick_creator(creators)
    if not creator:
        return

    if store.load_profile(creator) is None:
        answer = (
            input(f"\n'{creator}' ainda não foi analisado. Rodar a análise agora? (s/n): ").strip().lower()
        )
        if answer != "s":
            return
        try:
            analyze_creator(creator)
        except Exception as e:
            print(f"\n[ERRO] Falha na análise: {e}")
            return

    theme = input("\nQual é o seu TEMA, PRODUTO ou ASSUNTO? ").strip()
    if not theme:
        print("[ERRO] Tema vazio.")
        return

    print("\nGerando o dossiê... (evidência real + síntese do provedor ativo)\n")
    try:
        dossier = generate_dossier(creator, theme)
    except Exception as e:
        print(f"\n[ERRO] Falha ao gerar o dossiê: {e}")
        return

    print(dossier)

    out_file = get_settings().output_dir / f"dossier_{creator}_{slugify(theme)}.md"
    out_file.write_text(dossier, encoding="utf-8")
    print("\n" + "=" * 64)
    print(f"[OK] Dossiê salvo em: {out_file}")
    print("=" * 64)


def run_ingest() -> None:
    settings = get_settings()
    limit = settings.max_videos_per_creator
    print("\nCole ATÉ 5 links de vídeos curtos (YouTube Shorts, TikTok). Instagram: melhor esforço —")
    print("se falhar, baixe os Reels manualmente para videos/<criador>/.")
    creator = input("\nNome do criador (ex: jeffnippard): ").strip()
    if not creator:
        print("[ERRO] Nome vazio.")
        return

    raw = input(f"Links (máx. {limit}, separados por vírgula ou espaço): ").strip()
    urls = [u for u in re.split(r"[,\s]+", raw) if u.startswith("http")]
    if not urls:
        print("[ERRO] Nenhum link válido informado.")
        return
    if len(urls) > limit:
        print(f"[!] Você enviou {len(urls)} links — apenas os {limit} primeiros serão usados.")
        urls = urls[:limit]

    print(f"\nIngerindo {len(urls)} vídeo(s) para '{creator}'...\n")
    try:
        report = ingest_urls(creator, urls)
    except Exception as e:
        print(f"\n[ERRO] Falha na ingestão: {e}")
        return

    print("\n" + "=" * 64)
    print(
        f"[OK] {len(report['ok'])} ingerido(s) | {len(report['skipped'])} pulado(s) | {len(report['failed'])} falha(s)"
    )
    for fail in report["failed"]:
        print(f"  - {fail['url']}: {fail['reason']}")
    print("=" * 64)

    if report["ok"]:
        answer = input(f"\nRodar a análise de '{creator}' agora? (s/n): ").strip().lower()
        if answer == "s":
            print(f"\nAnalisando '{creator}'...\n")
            try:
                profile = analyze_creator(creator)
                print(f"\n[OK] Perfil de '{creator}' atualizado ({profile.videos_analyzed} vídeos).")
            except Exception as e:
                print(f"\n[ERRO] Falha na análise: {e}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    get_settings()

    print(BANNER)
    print("\n[1] Analisar/atualizar um criador (roda 1x por criador)")
    print("[2] Gerar dossiê de viralização (criador + seu tema)")
    print("[3] Adicionar criador por links (YouTube Shorts / TikTok)")

    choice = input("\nEscolha uma opção (1, 2 ou 3): ").strip()
    if choice == "1":
        run_analysis()
    elif choice == "2":
        run_dossier()
    elif choice == "3":
        run_ingest()
    else:
        print("Opção inválida.")


if __name__ == "__main__":
    main()
