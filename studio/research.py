"""Fact-check stage — the "scout" in the winner's two-stage pattern.

Before any dossier is written, this stage searches the web for verified facts
about the user's theme (with sources). The dossier stage (the "commentator")
may then use ONLY those facts. If the search is unavailable (no key, outage,
rate limit), it returns None and the dossier degrades gracefully to structural
mode — the feature degrades, it never dies.
"""

import logging

from .config import get_settings
from .factory import create_agent
from .schemas import ResearchReport

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Você é um pesquisador de fatos (fact-checker) para um estúdio de conteúdo.

Sua tarefa: dado um tema, buscar na web os fatos mais relevantes e RECENTES sobre ele,
sempre com a fonte de cada fato. O relatório será usado como ÚNICA fonte de verdade
para a etapa seguinte de escrita — então precisão vale mais que quantidade.

Regras de honestidade (CRÍTICO):
- Inclua em `facts` apenas o que foi de fato encontrado nas buscas, com a URL da fonte.
- Números, rankings, datas e versões só entram se aparecerem explicitamente na fonte.
- Tudo que for relevante mas não pôde ser confirmado vai para `unconfirmed`.
- Se o tema for muito recente e houver pouca informação, diga isso no summary.
- Responda em português (as fontes podem ser em qualquer idioma).
"""


def research_theme(theme: str) -> ResearchReport | None:
    """Search verified facts about the theme. Returns None on any failure (graceful degradation)."""
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY ausente — dossiê seguirá no modo estrutural (sem fact-check).")
        return None

    try:
        from agno.tools.tavily import TavilyTools

        agent = create_agent(
            name="fact_checker",
            description="Pesquisador de fatos com fontes — o estágio scout do pipeline.",
            instructions=INSTRUCTIONS,
            output_schema=ResearchReport,
            tools=[TavilyTools()],
        )
        logger.info("Fact-check: pesquisando '%s'...", theme)
        response = agent.run(f"Pesquise e verifique os fatos sobre: {theme}")

        if not isinstance(response.content, ResearchReport):
            raise RuntimeError(f"retorno inesperado do fact-check: {str(response.content)[:200]}")
        logger.info("Fact-check: %d fatos verificados, %d não confirmados.",
                    len(response.content.facts), len(response.content.unconfirmed))
        return response.content

    except Exception:
        logger.exception("Fact-check falhou — dossiê seguirá sem ele (degradação graciosa).")
        return None
