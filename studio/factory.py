"""Model factory — the ONLY place in the codebase that knows the LLM provider.

Prototyping: MODEL_PROVIDER=openai (gpt-4o, multimodal).
IBM submission: MODEL_PROVIDER=watsonx — Granite as the product's voice, with a
supporting vision model for the frame analysis (watsonx has no Granite vision).

Fallback: whenever the primary provider is NOT OpenAI and an OPENAI_API_KEY is
present, the OpenAI model is attached as an automatic fallback — if watsonx
fails (frozen account, Lite-plan 429s, outage), the agent retries on OpenAI
instead of dying. Prototypes keep running either way.
"""

from agno.agent import Agent
from agno.models.base import Model
from agno.models.openai import OpenAIChat

from .config import get_settings


def _build_model(model_id: str, vision: bool, *, temperature: float = 0.2) -> Model:
    settings = get_settings()

    if settings.model_provider == "watsonx":
        from agno.models.ibm import WatsonX  # requires the ibm-watsonx-ai SDK

        resolved = settings.watsonx_vision_model_id if vision else settings.watsonx_model_id
        # granite-4-h-small defaults to max_tokens=1024 when unspecified, which
        # truncates CreatorStyle / HookList JSON mid-object and crashes the
        # pipeline with "Textual analysis failed — model response: { ...".
        return WatsonX(
            id=resolved,
            api_key=settings.ibm_watsonx_api_key,
            project_id=settings.ibm_watsonx_project_id,
            url=settings.ibm_watsonx_url,
            max_tokens=settings.watsonx_max_tokens,
            temperature=temperature,
        )

    if settings.model_provider == "gemini":
        from agno.models.google import Gemini

        return Gemini(
            id=settings.gemini_model_id,
            api_key=settings.google_api_key,
            temperature=temperature,
        )

    return OpenAIChat(id=model_id, temperature=temperature)


def _openai_fallback(vision: bool, *, temperature: float = 0.2) -> Model | None:
    """OpenAI as the safety net whenever the primary provider is something else."""
    settings = get_settings()
    if settings.model_provider == "openai" or not settings.openai_api_key:
        return None
    mid = settings.openai_vision_model_id if vision else settings.openai_model_id
    return OpenAIChat(id=mid, temperature=temperature)


def get_model(*, temperature: float = 0.2) -> Model:
    """The product's voice: text analysis and the final dossier."""
    return _build_model(get_settings().openai_model_id, vision=False, temperature=temperature)


def get_vision_model(*, temperature: float = 0.15) -> Model:
    """The frame-analysis model (multimodal stage only)."""
    return _build_model(get_settings().openai_vision_model_id, vision=True, temperature=temperature)


def create_agent(
    *,
    name: str,
    description: str,
    instructions: str,
    output_schema: type | None = None,
    tools: list | None = None,
    vision: bool = False,
    temperature: float = 0.2,
) -> Agent:
    """Build an agent on the active provider with the project's defaults.

    Temperature is role-specific: lower for analysis (0.15), mid for hooks (0.4),
    controlled for copy (0.25). Defaults keep prior behaviour (~0.2).
    """
    settings = get_settings()
    model_id = settings.openai_vision_model_id if vision else settings.openai_model_id
    model = _build_model(model_id, vision, temperature=temperature)
    fallback = _openai_fallback(vision, temperature=temperature)
    return Agent(
        model=model,
        name=name,
        description=description,
        instructions=instructions,
        output_schema=output_schema,
        tools=tools or [],
        markdown=True,
        fallback_models=[fallback] if fallback is not None else None,
        retries=3,
        delay_between_retries=2,
    )
