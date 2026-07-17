"""Visual analysis — reverse-engineers a creator's editing grammar from frames.

This is the multimodal heart of the product: real video frames go to the active
multimodal model (GPT-4o today, Granite vision on watsonx for the submission)
and come back as a structured EditingProfile. Cut cadence itself is MEASURED
deterministically (studio/metrics.py) — the vision model interprets what the
numbers cannot see (framing, text overlays, b-roll, identity).
"""

import json
import logging

from agno.media import Image

from .factory import create_agent
from .frames import extract_frames_for_creator
from .schemas import EditingProfile

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Você é um editor de vídeo profissional especializado em conteúdo curto (Reels/TikTok/Shorts)
e em psicologia da retenção.

Você receberá uma sequência de frames REAIS extraídos dos vídeos de um criador, em
ordem cronológica, e MEDIÇÕES reais da cadência de cortes (cortes/minuto e duração
média de take, computadas por detecção de cena do ffmpeg). Sua tarefa é decodificar
a GRAMÁTICA DE EDIÇÃO dele.

Regras de honestidade (CRÍTICO):
- Em cut_cadence, use os NÚMEROS MEDIDOS (exatos) — sua leitura visual complementa
  com o que os números não mostram (tipo de corte, ângulo, movimento).
- Baseie cada conclusão APENAS no que é visível nos frames + nas medições. Não
  presuma nada que não possa ser observado diretamente.
- Se algo não puder ser observado com os frames disponíveis, declare em evidence_notes.
- Responda em português.
"""


def analyze_editing(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> EditingProfile:
    frames = extract_frames_for_creator(creator, max_videos)
    if not frames:
        raise ValueError(f"Nenhum frame extraído para '{creator}' — verifique a pasta videos/{creator}/.")

    metrics_block = ""
    if metrics and metrics.get("editing"):
        metrics_block = (
            "\n\nMEDIÇÕES reais da cadência de cortes (detecção de cena do ffmpeg — use os números exatos):\n"
            f"{json.dumps(metrics['editing'], ensure_ascii=False, indent=2)}"
        )

    agent = create_agent(
        name=f"editing_analyst_{creator}",
        description="Editor de vídeo sênior especializado em retenção e gramática de edição.",
        instructions=INSTRUCTIONS,
        output_schema=EditingProfile,
        vision=True,
    )
    logger.info("Analisando gramática de edição de %s (%d frames)...", creator, len(frames))
    response = agent.run(
        f"Estes são {len(frames)} frames reais, em ordem cronológica, de vídeos do "
        f"criador '{creator}'. Decodifique a gramática de edição dele.{metrics_block}",
        images=[Image(filepath=frame) for frame in frames],
    )
    if not isinstance(response.content, EditingProfile):
        # Agno returns the provider's error text as content instead of raising
        raise RuntimeError(f"Análise visual falhou — resposta do modelo: {str(response.content)[:200]}")
    return response.content
