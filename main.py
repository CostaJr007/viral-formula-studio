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
  Reverse engineering of a creator's viralization formula —
  copy, hooks and editing grammar, transposed to your theme.
  Inspiration, not imitation.
"""
    + "=" * 64
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "theme"


def pick_creator(creators: list[str]) -> str | None:
    print(f"\nAvailable creators: {', '.join(creators)}")
    creator = input("Creator name: ").strip()
    if creator not in creators:
        print(f"[ERROR] '{creator}' not found. Check the list above.")
        return None
    return creator


def run_analysis() -> None:
    creators = store.list_creators()
    if not creators:
        print("\n[!] No creators found. Add videos to videos/<creator>/ first.")
        return
    creator = pick_creator(creators)
    if not creator:
        return

    print(f"\nAnalyzing '{creator}' (transcription -> frames -> style + editing)...\n")
    try:
        profile = analyze_creator(creator)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        return

    print("\n" + "=" * 64)
    print(f"[OK] Profile for '{creator}' updated ({profile.videos_analyzed} videos analyzed)")
    print(f"  Textual analysis: {'ok' if profile.style else '--'}")
    print(f"  Visual analysis:  {'ok' if profile.editing else '--'}")
    print(f"  Saved to: {store.profile_path(creator)}")
    print("=" * 64)


def run_dossier() -> None:
    creators = store.list_creators()
    if not creators:
        print("\n[!] No creators found. Analyze a creator first (option 1).")
        return
    creator = pick_creator(creators)
    if not creator:
        return

    if store.load_profile(creator) is None:
        answer = (
            input(f"\n'{creator}' has not been analyzed yet. Run the analysis now? (y/n): ").strip().lower()
        )
        if answer != "y":
            return
        try:
            analyze_creator(creator)
        except Exception as e:
            print(f"\n[ERROR] Analysis failed: {e}")
            return

    theme = input("\nWhat is your THEME, PRODUCT or SUBJECT? ").strip()
    if not theme:
        print("[ERROR] Empty theme.")
        return

    print("\nGenerating the dossier... (real evidence + active provider synthesis)\n")
    try:
        dossier = generate_dossier(creator, theme)
    except Exception as e:
        print(f"\n[ERROR] Failed to generate the dossier: {e}")
        return

    print(dossier)

    out_file = get_settings().output_dir / f"dossier_{creator}_{slugify(theme)}.md"
    out_file.write_text(dossier, encoding="utf-8")
    print("\n" + "=" * 64)
    print(f"[OK] Dossier saved to: {out_file}")
    print("=" * 64)


def run_ingest() -> None:
    settings = get_settings()
    limit = settings.max_videos_per_creator
    print("\nPaste UP TO 5 short-video links (YouTube Shorts, TikTok). Instagram: best effort —")
    print("if it fails, download the Reels manually into videos/<creator>/.")
    creator = input("\nCreator name (e.g.: jeffnippard): ").strip()
    if not creator:
        print("[ERROR] Empty name.")
        return

    raw = input(f"Links (max. {limit}, separated by comma or space): ").strip()
    urls = [u for u in re.split(r"[,\s]+", raw) if u.startswith("http")]
    if not urls:
        print("[ERROR] No valid links provided.")
        return
    if len(urls) > limit:
        print(f"[!] You sent {len(urls)} links — only the first {limit} will be used.")
        urls = urls[:limit]

    print(f"\nIngesting {len(urls)} video(s) for '{creator}'...\n")
    try:
        report = ingest_urls(creator, urls)
    except Exception as e:
        print(f"\n[ERROR] Ingestion failed: {e}")
        return

    print("\n" + "=" * 64)
    print(
        f"[OK] {len(report['ok'])} ingested | {len(report['skipped'])} skipped | {len(report['failed'])} failed"
    )
    for fail in report["failed"]:
        print(f"  - {fail['url']}: {fail['reason']}")
    print("=" * 64)

    if report["ok"]:
        answer = input(f"\nRun the analysis for '{creator}' now? (y/n): ").strip().lower()
        if answer == "y":
            print(f"\nAnalyzing '{creator}'...\n")
            try:
                profile = analyze_creator(creator)
                print(f"\n[OK] Profile for '{creator}' updated ({profile.videos_analyzed} videos).")
            except Exception as e:
                print(f"\n[ERROR] Analysis failed: {e}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    get_settings()

    print(BANNER)
    print("\n[1] Analyze/update a creator (runs once per creator)")
    print("[2] Generate viralization dossier (creator + your theme)")
    print("[3] Add creator via links (YouTube Shorts / TikTok)")

    choice = input("\nChoose an option (1, 2 or 3): ").strip()
    if choice == "1":
        run_analysis()
    elif choice == "2":
        run_dossier()
    elif choice == "3":
        run_ingest()
    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()
