"""Research stage — schema and graceful degradation (no API keys needed)."""

from studio.research import research_theme
from studio.schemas import Fact, ResearchReport


def test_research_report_schema():
    report = ResearchReport(
        summary="Resumo do tema.",
        facts=[Fact(claim="Kimi 3 lidera o ranking X.", source="https://exemplo.com/a")],
        unconfirmed=["Data exata de lançamento."],
    )
    assert report.facts[0].source.startswith("https://")
    restored = ResearchReport.model_validate_json(report.model_dump_json())
    assert restored.unconfirmed == ["Data exata de lançamento."]


def test_research_returns_none_without_key(monkeypatch):
    from studio.config import get_settings

    monkeypatch.setattr(get_settings(), "tavily_api_key", None)
    assert research_theme("qualquer tema") is None
