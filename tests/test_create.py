"""Guided creation flow — schemas and profile guard (no API keys needed)."""

import pytest

from studio import store
from studio.create import Hook, HookList, VideoCopy, generate_hooks
from studio.schemas import CreatorProfile


def test_hook_list_schema():
    hooks = HookList(hooks=[Hook(text="Gancho de teste", pattern="Desafio pessoal") for _ in range(10)])
    assert len(hooks.hooks) == 10
    assert hooks.hooks[0].pattern


def test_video_copy_schema():
    copy = VideoCopy(
        script="[GANCHO] ... [DESENVOLVIMENTO] ... [FECHO] ...",
        editing_directions=["corte a cada ~3,1s"],
        data_notes="Fatos verificados com fonte; placeholder no ponto 3.",
    )
    assert copy.editing_directions


def test_generate_hooks_requires_profile(monkeypatch):
    monkeypatch.setattr(store, "load_profile", lambda creator: None)
    with pytest.raises(ValueError, match="não encontrado"):
        generate_hooks("fantasma", "qualquer tema")


def test_generate_hooks_rejects_empty_profile(monkeypatch):
    monkeypatch.setattr(store, "load_profile", lambda creator: CreatorProfile(creator="x", videos_analyzed=0))
    with pytest.raises(ValueError):
        generate_hooks("x", "qualquer tema")
