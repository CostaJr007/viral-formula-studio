"""Guided creation flow — schemas, quality filters, profile guard (no API keys needed)."""

import pytest

from studio import store
from studio.create import (
    Hook,
    HookList,
    VideoCopy,
    _hook_aligned,
    _pad_hooks_to_ten,
    _truncate_copy_words,
    filter_hooks,
    generate_hooks,
    slim_profile_for_prompt,
)
from studio.schemas import CreatorProfile, CreatorStyle, HookPattern


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
    with pytest.raises(ValueError, match="not found"):
        generate_hooks("fantasma", "qualquer tema")


def test_generate_hooks_rejects_empty_profile(monkeypatch):
    monkeypatch.setattr(store, "load_profile", lambda creator: CreatorProfile(creator="x", videos_analyzed=0))
    with pytest.raises(ValueError):
        generate_hooks("x", "qualquer tema")


def test_filter_hooks_drops_garbage_and_dedupes():
    raw = [
        Hook(text="gt gt broken", pattern="bad"),
        Hook(text="Short", pattern="bad"),
        Hook(text="Here is the truth about carnivore diet results", pattern="A"),
        Hook(text="Here is the truth about carnivore diet hacks", pattern="A"),  # near-dupe key
        Hook(text="Stop scrolling — carnivore diet myths end here today", pattern="B"),
        Hook(text="https://spam.com/viral tip about diet", pattern="C"),
    ]
    cleaned = filter_hooks(raw, "carnivore diet")
    assert all("gt" not in h.text.lower() or "got" in h.text.lower() for h in cleaned)
    assert all(not h.text.lower().startswith("http") for h in cleaned)
    assert len(cleaned) >= 1
    assert all(len(h.text.split()) >= 5 for h in cleaned)


def test_pad_hooks_to_ten():
    profile = CreatorProfile(
        creator="x",
        videos_analyzed=1,
        style=CreatorStyle(
            tone="direct",
            sentence_rhythm="fast",
            persona="coach",
            hook_patterns=[HookPattern(pattern="Promise", why_it_works="w", example="e")],
            copy_structure="hook body close",
            signature_expressions=["you"],
            persuasion_tactics=["direct"],
            evidence_notes="ok",
        ),
    )
    padded = _pad_hooks_to_ten([Hook(text="Real solid hook about sleep quality now", pattern="A")], "sleep", profile)
    assert len(padded) == 10


def test_hook_aligned():
    assert _hook_aligned('Stop guessing.', '"Stop guessing."')
    assert _hook_aligned("Hello world this is long enough", "Hello world this is long enough!")
    assert not _hook_aligned("Alpha beta gamma delta", "Something completely different here")


def test_slim_profile_keeps_metrics():
    profile = CreatorProfile(
        creator="jeff",
        videos_analyzed=3,
        metrics={
            "editing": {"avg_cuts_per_min": 22.1, "avg_shot_length_s": 1.2, "per_video": [{"waste": True}]},
            "speech": {"avg_wpm": 160},
            "signature_ngrams": [{"ngram": "you need", "count": 4}],
        },
        style=CreatorStyle(
            tone="technical",
            sentence_rhythm="fast",
            persona="scientist",
            hook_patterns=[HookPattern(pattern="Proof first", why_it_works="w", example="e")],
            copy_structure="open develop close",
            signature_expressions=["you need"],
            persuasion_tactics=["authority"],
            evidence_notes="measured",
        ),
    )
    slim = slim_profile_for_prompt(profile)
    assert slim["metrics"]["editing"]["avg_cuts_per_min"] == 22.1
    assert "per_video" not in slim["metrics"]["editing"]
    assert slim["style"]["tone"] == "technical"


def test_truncate_copy_words():
    # Build a long pipe script (~250+ spoken words)
    words = " ".join(["word"] * 40)
    blocks = [
        f"0:{i:02d}-0:{i+5:02d} | MEDIUM | \"{words}\" | cut | why"
        for i in range(0, 50, 5)
    ]
    copy = VideoCopy(script="\n".join(blocks), editing_directions=["a"], data_notes="n")
    trimmed = _truncate_copy_words(copy)
    from studio.create import _spoken_word_count

    # Should not grow; ideally under or near max after truncate
    assert _spoken_word_count(trimmed) <= _spoken_word_count(copy)
    assert "auto-trimmed" in trimmed.data_notes.lower() or _spoken_word_count(trimmed) <= 200
