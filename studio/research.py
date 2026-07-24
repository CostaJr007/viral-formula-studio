"""Fact-check stage — the "scout" in the winner's two-stage pattern.

Before any dossier is written, this stage searches the web for verified facts
about the user's theme (with sources). The dossier stage (the "commentator")
may then use ONLY those facts. If the search is unavailable (no key, outage,
rate limit), it returns None and the dossier degrades gracefully to structural
mode — the feature degrades, it never dies.

Performance note: we call the Tavily HTTP API directly (fast, bounded) instead
of an agent+tools loop that can hang for minutes on watsonx cold starts.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

from .config import get_settings
from .schemas import Fact, ResearchReport

logger = logging.getLogger(__name__)

# Hard caps so hook generation never freezes the UI for 2+ minutes
TAVILY_HTTP_TIMEOUT_S = 12
RESEARCH_BUDGET_S = 18

# In-process cache: hooks + copy share the same theme research (one Tavily hit)
_RESEARCH_CACHE: dict[str, ResearchReport | None] = {}


def clear_research_cache() -> None:
    """Test helper / manual reset."""
    _RESEARCH_CACHE.clear()


def _tavily_search(theme: str, api_key: str) -> dict[str, Any]:
    import json

    payload = json.dumps(
        {
            "api_key": api_key,
            "query": theme,
            "max_results": 5,
            "search_depth": "basic",
            "include_answer": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TAVILY_HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _report_from_tavily(theme: str, data: dict[str, Any]) -> ResearchReport:
    facts: list[Fact] = []
    for row in data.get("results") or []:
        content = (row.get("content") or row.get("snippet") or "").strip()
        url = (row.get("url") or "").strip()
        title = (row.get("title") or "").strip()
        if not content or not url:
            continue
        claim = content
        if title and title not in content:
            claim = f"{title}: {content}"
        # Keep claims short for prompt budget
        if len(claim) > 280:
            claim = claim[:277] + "..."
        facts.append(Fact(claim=claim, source=url))
        if len(facts) >= 5:
            break

    answer = (data.get("answer") or "").strip()
    summary = answer or (
        f"Found {len(facts)} source-backed snippets about '{theme}' via Tavily."
        if facts
        else f"Limited web evidence found for '{theme}'."
    )
    if len(summary) > 400:
        summary = summary[:397] + "..."

    unconfirmed: list[str] = []
    if not facts:
        unconfirmed.append(
            f"No high-confidence sources returned for '{theme}' — avoid inventing numbers."
        )

    return ResearchReport(summary=summary, facts=facts, unconfirmed=unconfirmed)


def research_theme(theme: str) -> ResearchReport | None:
    """Search verified facts about the theme. Returns None on any failure (graceful degradation).

    Cached per normalized theme so hooks + copy do not double-hit Tavily.
    """
    theme = (theme or "").strip()
    if not theme:
        return None

    cache_key = " ".join(theme.lower().split())
    if cache_key in _RESEARCH_CACHE:
        logger.info("Fact-check cache hit for '%s'", theme)
        return _RESEARCH_CACHE[cache_key]

    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY missing — dossier will proceed in structural mode (no fact-check).")
        _RESEARCH_CACHE[cache_key] = None
        return None

    def _run() -> ResearchReport:
        logger.info("Fact-check (Tavily HTTP): researching '%s'...", theme)
        data = _tavily_search(theme, settings.tavily_api_key or "")
        report = _report_from_tavily(theme, data)
        logger.info(
            "Fact-check: %d facts verified, %d unconfirmed.",
            len(report.facts),
            len(report.unconfirmed),
        )
        return report

    result: ResearchReport | None
    try:
        # Bound wall-clock time so /api/hooks never waits forever on scout stage
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run)
            result = fut.result(timeout=RESEARCH_BUDGET_S)
    except FuturesTimeout:
        logger.warning(
            "Fact-check timed out after %ss for '%s' — continuing without facts.",
            RESEARCH_BUDGET_S,
            theme,
        )
        result = None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        logger.warning("Fact-check HTTP failed for '%s': %s", theme, e)
        result = None
    except Exception:
        logger.exception("Fact-check failed — proceeding without it (graceful degradation).")
        result = None

    _RESEARCH_CACHE[cache_key] = result
    return result
