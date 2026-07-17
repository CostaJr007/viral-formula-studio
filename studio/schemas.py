"""Structured outputs of the analysis engine.

Every LLM analysis step returns one of these Pydantic models — never free text —
so results can be cached, validated and composed deterministically into the
final dossier. `evidence_notes` fields implement the honesty rule: the model
must state what the available evidence could NOT support.
"""

from pydantic import BaseModel, Field


class HookPattern(BaseModel):
    pattern: str = Field(
        description="O padrão de gancho recorrente (ex: pergunta de choque, dado contraintuitivo)"
    )
    why_it_works: str = Field(description="Por que esse padrão segura a atenção nos primeiros 3 segundos")
    example: str = Field(description="Exemplo real, extraído das transcrições do criador")


class CreatorStyle(BaseModel):
    """Textual fingerprint of a creator — extracted from real transcriptions."""

    tone: str = Field(description="Tom de voz predominante (ex: didático, provocativo, técnico)")
    sentence_rhythm: str = Field(description="Ritmo e tamanho médio das frases")
    persona: str = Field(description="Como o criador se posiciona (ex: mentor, cientista, amigo experiente)")
    hook_patterns: list[HookPattern] = Field(
        description="Padrões de gancho recorrentes — cada um com o porquê e um exemplo real"
    )
    copy_structure: str = Field(
        description="Mapa da estrutura do conteúdo: como ele abre, desenvolve e fecha um vídeo"
    )
    signature_expressions: list[str] = Field(
        description="Palavras e expressões características que ele usa com frequência"
    )
    persuasion_tactics: list[str] = Field(
        description="Gatilhos de persuasão e estrutura de CTA (prova social, urgência, autoridade...)"
    )
    evidence_notes: str = Field(
        description="O que NÃO foi possível concluir com as transcrições disponíveis (regra de honestidade)"
    )


class EditingProfile(BaseModel):
    """Visual editing grammar of a creator — extracted from real video frames."""

    cut_cadence: str = Field(
        description="Frequência e ritmo dos cortes/trocas de frame (ex: jump cuts a cada 2-3s)"
    )
    shot_types: str = Field(
        description="Enquadramentos predominantes (ex: close no rosto, plano médio, tela dividida)"
    )
    text_overlay_style: str = Field(
        description="Uso de texto na tela: legendas, palavras destacadas, posição, cor"
    )
    b_roll_usage: str = Field(description="Uso de b-roll, imagens de apoio, gráficos e memes")
    visual_identity: str = Field(
        description="Cenário, iluminação, paleta de cores, identidade visual recorrente"
    )
    retention_tricks: list[str] = Field(
        description="Truques visuais de retenção (zooms súbitos, pattern interrupts, transições)"
    )
    evidence_notes: str = Field(
        description="O que NÃO foi possível concluir com os frames disponíveis (regra de honestidade)"
    )


class CreatorProfile(BaseModel):
    """Complete cached profile of a creator (measurements + text + vision evidence)."""

    creator: str
    videos_analyzed: int
    metrics: dict | None = None
    style: CreatorStyle | None = None
    editing: EditingProfile | None = None


class Fact(BaseModel):
    """One verified fact about the user's theme, with its source."""

    claim: str = Field(description="O fato verificado, em uma frase")
    source: str = Field(description="URL da fonte onde o fato foi encontrado")


class ResearchReport(BaseModel):
    """Output of the fact-check stage (scout): verified facts about the theme."""

    summary: str = Field(description="Resumo executivo do tema em 2-3 frases")
    facts: list[Fact] = Field(description="Fatos verificados com fonte — só o que foi confirmado pela busca")
    unconfirmed: list[str] = Field(
        description="Afirmações relevantes que NÃO foram possíveis de confirmar (regra de honestidade)"
    )
