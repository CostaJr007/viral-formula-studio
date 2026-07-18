"""Resilient structured-output recovery for LLM responses.

WatsonX/Granite sometimes returns valid JSON as a plain string (or truncates
when max_tokens is too low) instead of a parsed Pydantic instance. Agno then
exposes that string as `response.content`. This helper:

1. Accepts an already-parsed schema instance.
2. Parses JSON (raw or fenced) into the schema.
3. Raises a clear RuntimeError with a short preview otherwise.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_json_payload(text: str) -> str:
    """Pull a JSON object/array out of free text or markdown fences."""
    stripped = text.strip()
    if not stripped:
        return stripped

    fenced = _FENCE_RE.search(stripped)
    if fenced:
        return fenced.group(1).strip()

    # First {…} or […] block (handles leading prose)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end > start:
            return stripped[start : end + 1]
    return stripped


def coerce_structured[T: BaseModel](content: object, schema: type[T], *, stage: str) -> T:
    """Coerce agent response content into `schema` or raise RuntimeError."""
    if isinstance(content, schema):
        return content

    if isinstance(content, dict):
        try:
            return schema.model_validate(content)
        except ValidationError as e:
            raise RuntimeError(f"{stage} failed — invalid structured fields: {e}") from e

    if isinstance(content, str):
        payload = _extract_json_payload(content)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            preview = content[:200].replace("\n", " ")
            # Truncation is the usual culprit when max_tokens is too low
            truncated = not payload.rstrip().endswith(("}", "]"))
            hint = " (response looks truncated — raise max_tokens)" if truncated else ""
            raise RuntimeError(
                f"{stage} failed — model returned non-JSON{hint}: {preview}"
            ) from e
        try:
            return schema.model_validate(data)
        except ValidationError as e:
            raise RuntimeError(f"{stage} failed — JSON did not match schema: {e}") from e

    preview = str(content)[:200]
    raise RuntimeError(f"{stage} failed — unexpected model response type: {preview}")
