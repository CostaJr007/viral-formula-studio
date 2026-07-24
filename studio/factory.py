"""Model factory — the ONLY place in the codebase that knows the LLM provider.

Prototyping: MODEL_PROVIDER=openai (gpt-4o, multimodal).
IBM submission: MODEL_PROVIDER=watsonx — Granite as the product's voice, with a
supporting vision model for the frame analysis (watsonx has no Granite vision).

Fallback chain (text, when MODEL_PROVIDER=watsonx):
  1) Second watsonx model id (same project/key) — e.g. Llama 3.3 70B
  2) Groq LLM (same GROQ_API_KEY as Whisper) — demo safety net on token_quota 403
  3) OpenAI only if OPENAI_FALLBACK=true

Vision stages do not use Groq (text-only). Seeds already cache editing profiles.
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.base import Model
from agno.models.openai import OpenAIChat

from .config import get_settings


def _build_watsonx(model_id: str, *, temperature: float) -> Model:
    """Single watsonx client shape — only the model id changes for primary vs fallback."""
    from agno.models.ibm import WatsonX  # requires the ibm-watsonx-ai SDK

    settings = get_settings()
    return WatsonX(
        id=model_id,
        api_key=settings.ibm_watsonx_api_key,
        project_id=settings.ibm_watsonx_project_id,
        url=settings.ibm_watsonx_url,
        max_tokens=settings.watsonx_max_tokens,
        temperature=temperature,
    )


def _build_groq(*, temperature: float = 0.2, max_tokens: int | None = None) -> Model | None:
    """Groq chat LLM — emergency text path when watsonx is out of quota.

    Headroom matters for full shooting scripts (~170–200 spoken words + pipe metadata).
    """
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    from agno.models.groq import Groq

    # Do NOT set supports_json_schema_outputs=True — Groq rejects response_format
    # for several models and returns 400 (breaks hooks/copy for judges).
    # We parse structured JSON from the model text via coerce_structured instead.
    return Groq(
        id=settings.groq_llm_model_id or "llama-3.1-8b-instant",
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens or 8192,
    )


def _build_model(model_id: str, vision: bool, *, temperature: float = 0.2) -> Model:
    settings = get_settings()

    if settings.model_provider == "watsonx":
        resolved = settings.watsonx_vision_model_id if vision else settings.watsonx_model_id
        return _build_watsonx(resolved, temperature=temperature)

    if settings.model_provider == "gemini":
        from agno.models.google import Gemini

        return Gemini(
            id=settings.gemini_model_id,
            api_key=settings.google_api_key,
            temperature=temperature,
        )

    return OpenAIChat(id=model_id, temperature=temperature)


def _fallback_chain(vision: bool, *, temperature: float = 0.2) -> list[Model]:
    """Ordered fallbacks. Text: IBM secondary model → Groq → optional OpenAI."""
    settings = get_settings()
    chain: list[Model] = []

    if settings.model_provider == "watsonx":
        primary = (settings.watsonx_vision_model_id if vision else settings.watsonx_model_id) or ""
        if vision:
            fb = (settings.watsonx_fallback_vision_model_id or "").strip()
        else:
            fb = (settings.watsonx_fallback_model_id or "").strip()
        if fb and fb != primary:
            chain.append(_build_watsonx(fb, temperature=temperature))

        # Groq is text-only — skip for vision agents
        if not vision and settings.groq_llm_fallback:
            groq_model = _build_groq(temperature=temperature)
            if groq_model is not None:
                chain.append(groq_model)

    if settings.openai_fallback and settings.openai_api_key and settings.model_provider != "openai":
        mid = settings.openai_vision_model_id if vision else settings.openai_model_id
        chain.append(OpenAIChat(id=mid, temperature=temperature))

    return chain


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
    force_model_id: str | None = None,
    force_provider: str | None = None,
    use_provider_fallbacks: bool = True,
) -> Agent:
    """Build an agent on the active provider with the project's defaults.

    force_provider: "groq" | "watsonx" pin (used for explicit emergency retry).
    force_model_id: when provider is watsonx, pin this model id.
    """
    settings = get_settings()
    model_id = settings.openai_vision_model_id if vision else settings.openai_model_id
    fallbacks: list[Model] = []

    if force_provider == "groq":
        model = _build_groq(temperature=temperature)
        if model is None:
            raise RuntimeError("GROQ_API_KEY not configured — cannot use Groq LLM fallback")
    elif force_model_id and (force_provider in (None, "watsonx")) and settings.model_provider == "watsonx":
        model = _build_watsonx(force_model_id, temperature=temperature)
    else:
        model = _build_model(model_id, vision, temperature=temperature)
        if use_provider_fallbacks:
            fallbacks = _fallback_chain(vision, temperature=temperature)

    return Agent(
        model=model,
        name=name,
        description=description,
        instructions=instructions,
        output_schema=output_schema,
        tools=tools or [],
        markdown=True,
        fallback_models=fallbacks or None,
        retries=3,
        delay_between_retries=2,
    )


def looks_like_provider_error(content: object) -> bool:
    """True when the model client returned an API error payload instead of schema JSON."""
    if isinstance(content, dict):
        if "errors" in content or content.get("status_code") in (401, 403, 429, 500, 502, 503):
            return True
        err = content.get("error")
        if isinstance(err, dict) and (err.get("code") or err.get("message")):
            return True
        # Groq/OpenAI style: {"error": {"message": "...", "code": "invalid_api_key"}}
        if "error" in content and "script" not in content and "hooks" not in content:
            return True
    if isinstance(content, str):
        low = content.lower()
        if "status_code" in low and any(c in low for c in ("403", "401", "429", "token")):
            return True
        if "token_quota" in low or "exceeded_limit" in low:
            return True
        if "failure during chat" in low:
            return True
        if "response_format" in low and "error" in low:
            return True
        if "invalid_api_key" in low or "invalid api key" in low:
            return True
        if '"error"' in low and "hooks" not in low and "script" not in low:
            # JSON error blob returned as string content
            if any(k in low for k in ("invalid", "unauthorized", "quota", "rate_limit", "forbidden")):
                return True
    return False


def watsonx_text_fallback_id() -> str | None:
    settings = get_settings()
    if settings.model_provider != "watsonx":
        return None
    fb = (settings.watsonx_fallback_model_id or "").strip()
    primary = (settings.watsonx_model_id or "").strip()
    if fb and fb != primary:
        return fb
    return None


def groq_llm_available() -> bool:
    settings = get_settings()
    return bool(settings.groq_llm_fallback and settings.groq_api_key)
