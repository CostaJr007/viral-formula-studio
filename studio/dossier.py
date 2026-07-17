"""Dossier synthesis — the final product (the "commentator" stage).

Composes the cached evidence profiles (style + editing), the verified facts from
the fact-check stage (scout) and the user's theme into the complete viralization
playbook. The active provider (Granite on watsonx for the submission) is the
single voice of this deliverable — grounded only in injected evidence, never in
prior "knowledge" about the creator or the theme.
"""

import logging

from . import store
from .factory import create_agent
from .research import research_theme
from .schemas import ResearchReport

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Você é um estrategista de conteúdo que transforma análise em plano de ação.

Você recebe: (1) o perfil de estilo textual e (2) o perfil de gramática de edição
de um criador — ambos extraídos de evidências reais dos vídeos dele — e (3) o tema
do usuário. Sua tarefa é montar o DOSSIÊ COMPLETO da fórmula de viralização desse
criador, transposto para o tema do usuário.

Princípio norteador: INSPIRAÇÃO, NÃO IMITAÇÃO. Todo criador aprende estudando
outros criadores — como um músico transcreve um solo para entender a técnica.
Você decodifica a FÓRMULA para que o usuário aplique com a própria voz, o próprio
tema e o próprio conteúdo. Nunca entregue frases prontas para serem copiadas
como se fossem do criador.

Regras de honestidade (CRÍTICO):
- Cada afirmação do dossiê deve vir dos perfis fornecidos (evidência real), nunca
  de suposições sobre o criador.
- Se uma dimensão tiver evidência fraca (consulte os evidence_notes dos perfis),
  sinalize com "[evidência limitada]" em vez de enfeitar.

Regra de dados (CRÍTICO — é o que prova que a produção é baseada em aprendizado):
- O perfil inclui um bloco `metrics` com MEDIÇÕES determinísticas (cortes/minuto,
  duração média de take, palavras/minuto, expressões repetidas com contagem).
- Sempre que falar de ritmo, cortes ou expressões, CITE os números medidos
  (ex.: "medido: 21,3 cortes/min", "medido: 145 palavras/min", "'no final do dia'
  aparece 7x em 5 vídeos"). Números medidos têm prioridade sobre descrições vagas.

Estrutura OBRIGATÓRIA do dossiê (markdown, em português):

# Dossiê de Viralização — {criador} × {tema}

## 1. Quem é a voz
Tom, ritmo e persona do criador — e o que isso significa para o tema do usuário.

## 2. A fórmula do gancho
Os padrões de gancho dele, POR QUE funcionam, e 5 sugestões de gancho para o tema
do usuário (escritas para a voz do usuário, seguindo a técnica — nunca copiando
frases do criador).

## 3. A estrutura da copy
O mapa início-meio-fim dele, transposto para uma estrutura de roteiro do tema do usuário.

## 4. A gramática de edição
Cadência de cortes, enquadramentos, texto na tela, b-roll, identidade visual e
truques de retenção — conforme observado nos vídeos dele, e como replicar a técnica.

## 5. Persuasão e CTA
Como ele converte atenção em ação, e que gatilhos usar no tema do usuário.

## 6. Plano de ação
Checklist prático, do gancho ao CTA, incluindo direções de edição, para o usuário
gravar e editar o próprio vídeo aplicando a fórmula.
"""


def generate_dossier(creator: str, theme: str, *, research: ResearchReport | None = None) -> str:
    profile = store.load_profile(creator)
    if profile is None:
        raise ValueError(f"Perfil de '{creator}' não encontrado. Rode a análise primeiro.")
    if profile.style is None and profile.editing is None:
        raise ValueError(f"Perfil de '{creator}' está vazio — rode a análise novamente.")

    if research is None:
        research = research_theme(theme)

    honesty_notes = []
    if profile.editing is None:
        honesty_notes.append(
            "Não há análise visual para este criador: na seção 4, declare isso explicitamente."
        )
    if profile.videos_analyzed < 3:
        honesty_notes.append(
            f"A análise se baseia em apenas {profile.videos_analyzed} vídeo(s): "
            "sinalize as seções afetadas como evidência limitada."
        )
    if research is None:
        honesty_notes.append(
            "O fact-check está indisponível: NÃO afirme nenhum fato sobre o tema; mantenha o "
            "dossiê estrutural e indique os pontos onde o usuário deve inserir seus próprios dados."
        )

    facts_block = ""
    if research is not None:
        facts_block = (
            "\n\nFATOS VERIFICADOS SOBRE O TEMA (única fonte de verdade factual — JSON):\n"
            f"{research.model_dump_json(indent=2)}\n"
            "Toda afirmação factual sobre o tema deve vir DESTE bloco. Ao usar um fato, cite a "
            "fonte entre parênteses. Se algo relevante estiver em 'unconfirmed', diga que não "
            "foi possível confirmar — nunca trate como fato."
        )

    agent = create_agent(
        name=f"dossier_strategist_{creator}",
        description="Estrategista de conteúdo que transforma análise de criadores em plano de ação.",
        instructions=INSTRUCTIONS + ("\n" + "\n".join(honesty_notes) if honesty_notes else ""),
    )

    logger.info("Gerando dossiê de '%s' para o tema '%s'...", creator, theme)
    response = agent.run(
        f"Criador analisado: {creator}\n"
        f"Tema do usuário: {theme}\n\n"
        f"Perfis extraídos de evidências reais (JSON):\n{profile.model_dump_json(indent=2)}"
        f"{facts_block}\n\n"
        "Monte o dossiê completo seguindo a estrutura obrigatória."
    )
    if not isinstance(response.content, str) or not response.content.strip():
        raise RuntimeError(f"Geração do dossiê falhou — resposta do modelo: {str(response.content)[:200]}")
    return response.content
