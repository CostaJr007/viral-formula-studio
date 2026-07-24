"""Dossier synthesis — the final product (the "commentator" stage).

Composes the cached evidence profiles (style + editing), the verified facts from
the fact-check stage (scout) and the user's theme into the complete viralization
playbook. The active provider (Granite on watsonx for the submission) is the
single voice of this deliverable — grounded only in injected evidence, never in
prior "knowledge" about the creator or the theme.
"""

import logging

from . import store
from .factory import create_agent
from .research import research_theme
from .schemas import ResearchReport

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are a content strategist who turns analysis into an action plan.

You receive: (1) the textual style profile and (2) the editing grammar profile
of a creator — both extracted from real evidence from their videos — and (3) the
user's theme. Your task is to assemble the COMPLETE DOSSIER of that creator's
viralization formula, transposed to the user's theme.

Guiding principle: INSPIRATION, NOT IMITATION. Every creator learns by studying
other creators — like a musician transcribing a solo to understand the technique.
You decode the FORMULA so the user applies it with their own voice, their own
theme and their own content. Never deliver ready-made phrases to be copied
as if they were the creator's.

Honesty rules (CRITICAL):
- Every statement in the dossier must come from the provided profiles (real
  evidence), never from assumptions about the creator.
- If a dimension has weak evidence (check the profiles' evidence_notes),
  flag it with "[limited evidence]" instead of embellishing.

Data rule (CRITICAL — it is what proves the output is based on learning):
- The profile includes a `metrics` block with deterministic MEASUREMENTS
  (cuts/minute, average shot length, words/minute, repeated expressions with
  counts).
- Whenever you talk about rhythm, cuts or expressions, CITE the measured numbers
  (e.g. "measured: 21.3 cuts/min", "measured: 145 words/min", "'at the end of
  the day' appears 7x in 5 videos"). Measured numbers take priority over vague
  descriptions.

MANDATORY dossier structure (markdown, in English):

# Viralization Dossier — {creator} × {theme}

## 1. Who the voice is
The creator's tone, rhythm and persona — and what that means for the user's theme.

## 2. The hook formula
Their hook patterns, WHY they work, and 5 hook suggestions for the user's
theme (written for the user's voice, following the technique — never copying
the creator's phrases).

## 3. The copy structure
Their beginning-middle-end map, transposed into a script structure for the
user's theme.

## 4. The editing grammar
Cut cadence, framings, on-screen text, b-roll, visual identity and
retention tricks — as observed in their videos, and how to replicate the
technique.

## 5. Persuasion & CTA
How they convert attention into action, and which triggers to use in the
user's theme.

## 6. Action plan
Practical checklist, from hook to CTA, including editing directions, for the
user to record and edit their own video applying the formula.
"""


def generate_dossier(creator: str, theme: str, *, research: ResearchReport | None = None, profile_data: dict | None = None) -> str:
    profile = None
    if profile_data is not None:
        try:
            profile = store.CreatorProfile.model_validate(profile_data)
        except Exception as e:
            logger.warning("Client profile invalid for dossier '%s' (%s) — disk fallback", creator, e)
    if profile is None:
        profile = store.load_profile(creator)
    if profile is None:
        raise ValueError(f"Profile for '{creator}' not found. Run the analysis first.")
    if profile.style is None and profile.editing is None:
        raise ValueError(f"Profile for '{creator}' is empty — run the analysis again.")

    if research is None:
        research = research_theme(theme)

    honesty_notes = []
    if profile.editing is None:
        honesty_notes.append(
            "There is no visual analysis for this creator: in section 4, state that explicitly."
        )
    if profile.videos_analyzed < 3:
        honesty_notes.append(
            f"The analysis is based on only {profile.videos_analyzed} video(s): "
            "flag the affected sections as limited evidence."
        )
    if research is None:
        honesty_notes.append(
            "The fact-check is unavailable: do NOT state any fact about the theme; keep the "
            "dossier structural and mark the points where the user must insert their own data."
        )

    facts_block = ""
    if research is not None:
        facts_block = (
            "\n\nVERIFIED FACTS ABOUT THE THEME (single source of factual truth — JSON):\n"
            f"{research.model_dump_json(indent=2)}\n"
            "Every factual statement about the theme must come from THIS block. When using a "
            "fact, cite the source in parentheses. If something relevant is in 'unconfirmed', "
            "say it could not be confirmed — never treat it as a fact."
        )

    agent = create_agent(
        name=f"dossier_strategist_{creator}",
        description="Content strategist who turns creator analysis into an action plan.",
        instructions=INSTRUCTIONS + ("\n" + "\n".join(honesty_notes) if honesty_notes else ""),
        temperature=0.25,
    )

    logger.info("Generating dossier for '%s' on theme '%s'...", creator, theme)
    response = agent.run(
        f"Analyzed creator: {creator}\n"
        f"User's theme: {theme}\n\n"
        f"Profiles extracted from real evidence (JSON):\n{profile.model_dump_json(indent=2)}"
        f"{facts_block}\n\n"
        "Assemble the complete dossier following the mandatory structure."
    )
    if not isinstance(response.content, str) or not response.content.strip():
        raise RuntimeError(f"Dossier generation failed — model response: {str(response.content)[:200]}")
    return response.content
