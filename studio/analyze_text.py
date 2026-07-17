"""Textual analysis — reverse-engineers a creator's copy and hook fingerprint.

Consumes real transcriptions and returns a structured CreatorStyle. Runs once
per creator; the result is cached in the creator profile.
"""

import json
import logging

from . import store
from .config import get_settings
from .factory import create_agent
from .schemas import CreatorStyle

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Você é um especialista em engenharia reversa de copywriting e retenção de audiência.

Sua tarefa é extrair a "impressão digital" textual de um criador de conteúdo a partir
das transcrições reais dos vídeos dele. Você NÃO resume o conteúdo — você decodifica
a TÉCNICA: como ele escreve, como ele ganha atenção, como estrutura e como persuade.

Regras de honestidade (CRÍTICO):
- Baseie cada conclusão APENAS nas transcrições e nas MEDIÇÕES fornecidas. Nunca
  use "conhecimento" prévio sobre o criador ou sobre o nicho dele.
- Todo padrão de gancho precisa de um exemplo real extraído do texto fornecido.
- As MEDIÇÕES (palavras/minuto, expressões repetidas com contagem) são verdades
  medidas nos arquivos: use os números exatos nos campos correspondentes —
  nunca estime o que já foi medido.
- Se a evidência for insuficiente para alguma dimensão, declare isso explicitamente
  no campo evidence_notes em vez de preencher com suposições.
- Responda em português.
"""


def analyze_style(creator: str, max_videos: int | None = None, metrics: dict | None = None) -> CreatorStyle:
    settings = get_settings()
    items = store.get_creator_transcriptions(creator)
    if not items:
        raise ValueError(f"Nenhuma transcrição encontrada para '{creator}'. Rode a transcrição primeiro.")

    sample = items[: max_videos or settings.max_videos_per_creator]
    text = "\n\n---\n\n".join(f"[{item['video']}]\n{item['transcription']}" for item in sample)

    metrics_block = ""
    if metrics:
        measured = {
            "speech": metrics.get("speech"),
            "signature_ngrams": metrics.get("signature_ngrams"),
        }
        metrics_block = (
            "\n\nMEDIÇÕES determinísticas computadas dos arquivos (use os números exatos):\n"
            f"{json.dumps(measured, ensure_ascii=False, indent=2)}"
        )

    agent = create_agent(
        name=f"style_analyst_{creator}",
        description="Especialista em engenharia reversa de copywriting e análise de estilo.",
        instructions=INSTRUCTIONS,
        output_schema=CreatorStyle,
    )
    logger.info("Analisando estilo textual de %s (%d vídeos)...", creator, len(sample))
    response = agent.run(
        f"Analise as transcrições reais do criador '{creator}' abaixo e extraia a "
        f"impressão digital de copywriting dele:\n\n{text}{metrics_block}"
    )
    if not isinstance(response.content, CreatorStyle):
        # Agno returns the provider's error text as content instead of raising
        raise RuntimeError(f"Análise textual falhou — resposta do modelo: {str(response.content)[:200]}")
    return response.content
