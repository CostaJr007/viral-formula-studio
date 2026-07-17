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
You are a fact researcher (fact-checker) for a content studio.

Your task: given a theme, search the web for the most relevant and RECENT facts about it,
always with the source of each fact. The report will be used as the SINGLE source of truth
for the following writing stage — so precision matters more than quantity.

Honesty rules (CRITICAL):
- Include in `facts` only what was actually found in the searches, with the source URL.
- Numbers, rankings, dates and versions only go in if they appear explicitly in the source.
- Everything relevant that could not be confirmed goes to `unconfirmed`.
- If the theme is very recent and there is little information, say so in the summary.
- Respond in English (the sources may be in any language).
"""


def research_theme(theme: str) -> ResearchReport | None:
    """Search verified facts about the theme. Returns None on any failure (graceful degradation)."""
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY missing — dossier will proceed in structural mode (no fact-check).")
        return None

    try:
        from agno.tools.tavily import TavilyTools

        agent = create_agent(
            name="fact_checker",
            description="Fact researcher with sources — the pipeline's scout stage.",
            instructions=INSTRUCTIONS,
            output_schema=ResearchReport,
            tools=[TavilyTools()],
        )
        logger.info("Fact-check: researching '%s'...", theme)
        response = agent.run(f"Research and verify the facts about: {theme}")

        if not isinstance(response.content, ResearchReport):
            raise RuntimeError(f"unexpected fact-check return: {str(response.content)[:200]}")
        logger.info("Fact-check: %d facts verified, %d unconfirmed.",
                    len(response.content.facts), len(response.content.unconfirmed))
        return response.content

    except Exception:
        logger.exception("Fact-check failed — dossier will proceed without it (graceful degradation).")
        return None
