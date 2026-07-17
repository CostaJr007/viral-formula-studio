"""Structured outputs of the analysis engine.

Every LLM analysis step returns one of these Pydantic models — never free text —
so results can be cached, validated and composed deterministically into the
final dossier. `evidence_notes` fields implement the honesty rule: the model
must state what the available evidence could NOT support.
"""

from pydantic import BaseModel, Field


class HookPattern(BaseModel):
    pattern: str = Field(
        description="The recurring hook pattern (e.g. shock question, counterintuitive fact)"
    )
    why_it_works: str = Field(description="Why this pattern holds attention in the first 3 seconds")
    example: str = Field(description="Real example, extracted from the creator's transcriptions")


class CreatorStyle(BaseModel):
    """Textual fingerprint of a creator — extracted from real transcriptions."""

    tone: str = Field(description="Predominant tone of voice (e.g. didactic, provocative, technical)")
    sentence_rhythm: str = Field(description="Rhythm and average sentence length")
    persona: str = Field(
        description="How the creator positions themselves (e.g. mentor, scientist, experienced friend)"
    )
    hook_patterns: list[HookPattern] = Field(
        description="Recurring hook patterns — each with the why and a real example"
    )
    copy_structure: str = Field(
        description="Map of the content structure: how they open, develop and close a video"
    )
    signature_expressions: list[str] = Field(
        description="Characteristic words and expressions they use frequently"
    )
    persuasion_tactics: list[str] = Field(
        description="Persuasion triggers and CTA structure (social proof, urgency, authority...)"
    )
    evidence_notes: str = Field(
        description="What could NOT be concluded from the available transcriptions (honesty rule)"
    )


class EditingProfile(BaseModel):
    """Visual editing grammar of a creator — extracted from real video frames."""

    cut_cadence: str = Field(
        description="Frequency and rhythm of cuts/frame changes (e.g. jump cuts every 2-3s)"
    )
    shot_types: str = Field(
        description="Predominant framings (e.g. face close-up, medium shot, split screen)"
    )
    text_overlay_style: str = Field(
        description="On-screen text usage: captions, highlighted words, position, color"
    )
    b_roll_usage: str = Field(description="Use of b-roll, supporting images, charts and memes")
    visual_identity: str = Field(
        description="Setting, lighting, color palette, recurring visual identity"
    )
    retention_tricks: list[str] = Field(
        description="Visual retention tricks (sudden zooms, pattern interrupts, transitions)"
    )
    evidence_notes: str = Field(
        description="What could NOT be concluded from the available frames (honesty rule)"
    )


class CreatorProfile(BaseModel):
    """Complete cached profile of a creator (measurements + text + vision evidence)."""

    creator: str
    videos_analyzed: int
    metrics: dict | None = None
    style: CreatorStyle | None = None
    editing: EditingProfile | None = None


class Fact(BaseModel):
    """One verified fact about the user's theme, with its source."""

    claim: str = Field(description="The verified fact, in one sentence")
    source: str = Field(description="URL of the source where the fact was found")


class ResearchReport(BaseModel):
    """Output of the fact-check stage (scout): verified facts about the theme."""

    summary: str = Field(description="Executive summary of the theme in 2-3 sentences")
    facts: list[Fact] = Field(description="Verified facts with source — only what was confirmed by the search")
    unconfirmed: list[str] = Field(
        description="Relevant claims that could NOT be confirmed (honesty rule)"
    )
