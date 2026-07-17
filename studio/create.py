"""Guided creation flow — the actionable half of the product.

Step 1 (generate_hooks): 10 hooks built from the creator's MEASURED formula
(hook patterns + metrics) and the verified facts from the research stage.
Step 2 (generate_copy): the user picks one hook; the full video copy is
orchestrated around it — <=200 words (1-2 min videos), the creator's copy
structure, measured editing directions, and explicit data-honesty notes.

Nothing here invents facts: hooks and copy may only use facts from the
ResearchReport; anything else becomes a placeholder for the user to fill.
"""

import logging

from pydantic import BaseModel, Field

from . import store
from .factory import create_agent
from .research import research_theme
from .schemas import ResearchReport

logger = logging.getLogger(__name__)

MAX_COPY_WORDS = 200


class Hook(BaseModel):
    text: str = Field(description="O gancho, pronto para os primeiros 3 segundos")
    pattern: str = Field(description="Qual padrão de gancho do criador este segue")


class HookList(BaseModel):
    hooks: list[Hook] = Field(description="Exatamente 10 ganchos")


class VideoCopy(BaseModel):
    script: str = Field(
        description="Copy completa em markdown com blocos [GANCHO] / [DESENVOLVIMENTO] / [FECHO], "
        f"máximo {MAX_COPY_WORDS} palavras no total"
    )
    editing_directions: list[str] = Field(
        description="Direções de edição por bloco, usando os NÚMEROS MEDIDOS do criador (cortes/min, take, texto na tela)"
    )
    data_notes: str = Field(
        description="O que é fato verificado (com fonte) e o que o usuário precisa confirmar/preencher antes de gravar"
    )


HOOKS_INSTRUCTIONS = """
Você é um estrategista de ganchos para vídeos curtos.

Você recebe: (1) o perfil de um criador — padrões de gancho, tom, expressões e
MÉTRICAS medidas dos vídeos dele — e (2) fatos verificados sobre o tema do usuário.

Sua tarefa: gerar EXATAMENTE 10 ganchos para os primeiros 3 segundos do vídeo do
usuário, aplicando os padrões de gancho do criador ao tema.

Regras:
- Cada gancho deve seguir visivelmente um dos padrões do criador (campo `pattern`).
- Frases curtas e faláveis — são para serem DITAS em até 3 segundos.
- Só use fatos do bloco FATOS VERIFICADOS; nunca invente números ou rankings.
- Escreva para a voz do USUÁRIO, no idioma do usuário — nunca copie frases do criador.
- Varie os padrões: não gere 10 ganchos iguais.
"""

COPY_INSTRUCTIONS = f"""
Você é um roteirista e diretor de vídeos curtos especializado em retenção.

Você recebe: (1) o perfil MEDIDO de um criador (estrutura de copy, tom, ritmo em
palavras/minuto, gramática de edição), (2) fatos verificados sobre o tema, e
(3) o gancho que o usuário escolheu.

Sua tarefa: orquestrar o vídeo completo do usuário em torno desse gancho.

Regras de estrutura:
- O script tem NO MÁXIMO {MAX_COPY_WORDS} palavras (vídeo de ~1 minuto no ritmo
  medido do criador). Blocos: [GANCHO] (o escolhido, palavra por palavra),
  [DESENVOLVIMENTO] (estrutura de copy do criador aplicada ao tema),
  [FECHO] (resultado + CTA compatível com o estilo dele).
- Estrutura dopaminérgica: cada frase precisa justificar a próxima; sem enrolação.
- Só use fatos do bloco FATOS VERIFICADOS. Onde faltar dado, deixe um placeholder
  claro [INSIRA: ...] em vez de inventar — e liste esses pontos em data_notes.
- editing_directions: use os NÚMEROS MEDIDOS (ex.: "corte a cada ~3,1s",
  "texto na tela inferior destacando o número") — nunca direção vaga.
- Responda em português.
"""


def _profile_or_raise(creator: str):
    profile = store.load_profile(creator)
    if profile is None or (profile.style is None and profile.editing is None):
        raise ValueError(f"Perfil de '{creator}' não encontrado. Rode a análise primeiro.")
    return profile


def _facts_block(research: ResearchReport | None) -> str:
    if research is None:
        return (
            "\nFATOS VERIFICADOS: indisponíveis (fact-check falhou). "
            "NÃO afirme nenhum fato sobre o tema — use placeholders [INSIRA: ...]."
        )
    return f"\nFATOS VERIFICADOS SOBRE O TEMA (única fonte factual — JSON):\n{research.model_dump_json(indent=2)}"


def generate_hooks(creator: str, theme: str, *, research: ResearchReport | None = None) -> HookList:
    """Step 1: 10 hooks from the creator's formula + verified facts."""
    profile = _profile_or_raise(creator)
    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"hook_strategist_{creator}",
        description="Estrategista de ganchos baseado na fórmula medida de criadores.",
        instructions=HOOKS_INSTRUCTIONS,
        output_schema=HookList,
    )
    logger.info("Gerando 10 ganchos de '%s' para '%s'...", creator, theme)
    response = agent.run(
        f"Perfil do criador (evidência medida — JSON):\n{profile.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\nTema do usuário: {theme}\n\nGere os 10 ganchos."
    )
    if not isinstance(response.content, HookList):
        raise RuntimeError(f"Geração de ganchos falhou — resposta do modelo: {str(response.content)[:200]}")
    return response.content


def generate_copy(
    creator: str, theme: str, chosen_hook: str, *, research: ResearchReport | None = None
) -> VideoCopy:
    """Step 2: full orchestrated copy (<=200 words) around the user's chosen hook."""
    profile = _profile_or_raise(creator)
    if research is None:
        research = research_theme(theme)

    agent = create_agent(
        name=f"copy_director_{creator}",
        description="Roteirista e diretor de vídeos curtos — copy dopaminérgica baseada em dados medidos.",
        instructions=COPY_INSTRUCTIONS,
        output_schema=VideoCopy,
    )
    logger.info("Gerando copy de '%s' x '%s' com o gancho escolhido...", creator, theme)
    response = agent.run(
        f"Perfil do criador (evidência medida — JSON):\n{profile.model_dump_json(indent=2)}\n"
        f"{_facts_block(research)}\n\n"
        f'Tema do usuário: {theme}\nGancho escolhido pelo usuário: "{chosen_hook}"\n\n'
        "Orquestre o vídeo completo."
    )
    if not isinstance(response.content, VideoCopy):
        raise RuntimeError(f"Geração da copy falhou — resposta do modelo: {str(response.content)[:200]}")
    return response.content
