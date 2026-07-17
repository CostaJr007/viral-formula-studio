"""Optional web interface via Agno AgentOS — exposes the dossier engine as tools.

Run: python agent.py  ->  http://localhost:8000
The same engine powers CLI and web; this file only wires the tools.
"""

from agno.agent import Agent
from agno.db.sqlite.sqlite import SqliteDb
from agno.os.app import AgentOS

from studio import store
from studio.config import get_settings
from studio.dossier import generate_dossier
from studio.factory import get_model
from studio.pipeline import analyze_creator


def list_creators_tool() -> str:
    """Lists the creators available for analysis and dossier generation."""
    creators = store.list_creators()
    if not creators:
        return "No creators found. Add videos to videos/<creator>/ and run the analysis."
    return "Available creators: " + ", ".join(creators)


def analyze_creator_tool(creator: str) -> str:
    """Runs the full analysis (textual style + editing grammar) of a creator and saves the profile."""
    profile = analyze_creator(creator, transcribe=False)
    return (
        f"Profile for '{profile.creator}' updated: {profile.videos_analyzed} videos, "
        f"style={'ok' if profile.style else 'pending'}, editing={'ok' if profile.editing else 'pending'}."
    )


def dossier_tool(creator: str, theme: str) -> str:
    """Generates a creator's complete viralization dossier applied to the user's theme."""
    return generate_dossier(creator, theme)


INSTRUCTIONS = """
You are the strategist of Viral Formula Studio: a reverse-engineering system
for content creators' viralization formulas.

Your role: help the user (1) analyze a creator and (2) generate the dossier of
their formula — copy, hooks, editing grammar and persuasion — transposed to the
user's theme.

Principles:
- INSPIRATION, NOT IMITATION: we decode the technique so the user can apply it
  with their own voice. We never deliver content to copy.
- HONESTY: every statement comes from real evidence (transcriptions and frames).
  When the evidence is limited, we say so.
- If the creator has no profile yet, use the analysis tool before generating
  the dossier.
"""

settings = get_settings()

studio_agent = Agent(
    model=get_model(),
    name="viral_formula_studio",
    description="Reverse engineering of content creators' viralization formulas.",
    instructions=INSTRUCTIONS,
    tools=[list_creators_tool, analyze_creator_tool, dossier_tool],
    add_history_to_context=True,
    num_history_runs=10,
    db=SqliteDb(db_file=str(settings.db_file)),
    markdown=True,
)

app = AgentOS(agents=[studio_agent])

if __name__ == "__main__":
    app.serve(port=8000)
