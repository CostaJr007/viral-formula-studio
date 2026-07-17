"""Schema validation — the analysis engine's output contracts."""

from studio.schemas import CreatorProfile, CreatorStyle, EditingProfile, HookPattern


def make_style() -> CreatorStyle:
    return CreatorStyle(
        tone="Didático e direto",
        sentence_rhythm="Frases curtas e rápidas",
        persona="Mentor técnico",
        hook_patterns=[
            HookPattern(
                pattern="Dado contraintuitivo",
                why_it_works="Quebra a expectativa e cria lacuna de curiosidade",
                example="Você está treinando errado há anos.",
            )
        ],
        copy_structure="Problema -> explicação -> solução -> CTA",
        signature_expressions=["na prática", "o que acontece é"],
        persuasion_tactics=["autoridade técnica", "prova social"],
        evidence_notes="Amostra pequena de vídeos.",
    )


def test_hook_pattern_requires_example():
    hook = HookPattern(
        pattern="Pergunta de choque", why_it_works="Engaja resposta mental", example="E se eu te dissesse...?"
    )
    assert hook.example


def test_creator_style_roundtrip():
    style = make_style()
    restored = CreatorStyle.model_validate_json(style.model_dump_json())
    assert restored.hook_patterns[0].pattern == "Dado contraintuitivo"


def test_editing_profile_fields():
    editing = EditingProfile(
        cut_cadence="Jump cuts a cada 2-3s",
        shot_types="Close no rosto",
        text_overlay_style="Legendas grandes centrais",
        b_roll_usage="B-roll de gráficos",
        visual_identity="Academia, luz natural",
        retention_tricks=["zoom súbito", "pattern interrupt"],
        evidence_notes="Poucos frames de b-roll.",
    )
    assert "zoom súbito" in editing.retention_tricks


def test_creator_profile_allows_partial_evidence():
    profile = CreatorProfile(creator="jeffnippard", videos_analyzed=5, style=make_style())
    assert profile.editing is None
    dumped = profile.model_dump()
    assert dumped["creator"] == "jeffnippard"
