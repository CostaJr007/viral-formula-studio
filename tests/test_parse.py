"""Unit tests for resilient structured-output recovery."""

import pytest
from pydantic import BaseModel, Field

from studio.parse import coerce_structured


class Sample(BaseModel):
    tone: str
    hooks: list[str] = Field(default_factory=list)


def test_already_parsed_instance():
    obj = Sample(tone="direct", hooks=["a"])
    assert coerce_structured(obj, Sample, stage="test") is obj


def test_dict_payload():
    out = coerce_structured({"tone": "calm", "hooks": ["x"]}, Sample, stage="test")
    assert out.tone == "calm"
    assert out.hooks == ["x"]


def test_raw_json_string():
    out = coerce_structured('{"tone": "provocative", "hooks": ["h1"]}', Sample, stage="test")
    assert out.tone == "provocative"
    assert out.hooks == ["h1"]


def test_fenced_json_string():
    text = 'Here you go:\n```json\n{"tone": "mentor", "hooks": []}\n```'
    out = coerce_structured(text, Sample, stage="test")
    assert out.tone == "mentor"


def test_truncated_json_raises_clear_error():
    broken = '{ "tone": "provocative", "sentence_rhythm": "fast", "hook_patterns" .'
    with pytest.raises(RuntimeError, match="truncated|non-JSON"):
        coerce_structured(broken, Sample, stage="Textual analysis")
