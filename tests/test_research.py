"""Research stage — schema and graceful degradation (no API keys needed)."""

from studio.research import research_theme
from studio.schemas import Fact, ResearchReport


def test_research_report_schema():
    report = ResearchReport(
        summary="Resumo do tema.",
        facts=[Fact(claim="A trending topic leads industry rankings.", source="https://exemplo.com/a")],
        unconfirmed=["Data exata de lançamento."],
    )
    assert report.facts[0].source.startswith("https://")
    restored = ResearchReport.model_validate_json(report.model_dump_json())
    assert restored.unconfirmed == ["Data exata de lançamento."]


def test_research_returns_none_without_key(monkeypatch):
    from studio.config import get_settings
    from studio.research import clear_research_cache

    clear_research_cache()
    monkeypatch.setattr(get_settings(), "tavily_api_key", None)
    assert research_theme("qualquer tema") is None


def test_research_cache_hits_same_theme(monkeypatch):
    from studio import research as research_mod
    from studio.config import get_settings

    research_mod.clear_research_cache()
    monkeypatch.setattr(get_settings(), "tavily_api_key", "fake-key")
    calls = {"n": 0}

    def fake_search(theme: str, api_key: str):
        calls["n"] += 1
        return {
            "answer": "summary",
            "results": [{"content": "A useful claim about sleep.", "url": "https://ex.com/a", "title": "T"}],
        }

    monkeypatch.setattr(research_mod, "_tavily_search", fake_search)
    a = research_mod.research_theme("Better Sleep Habits")
    b = research_mod.research_theme("better   sleep habits")
    assert a is not None and b is not None
    assert calls["n"] == 1
    assert a.facts[0].source.startswith("https://")
