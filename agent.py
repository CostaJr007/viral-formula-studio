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
    """Lista os criadores disponíveis para análise e geração de dossiê."""
    creators = store.list_creators()
    if not creators:
        return "Nenhum criador encontrado. Adicione vídeos em videos/<criador>/ e rode a análise."
    return "Criadores disponíveis: " + ", ".join(creators)


def analyze_creator_tool(creator: str) -> str:
    """Roda a análise completa (estilo textual + gramática de edição) de um criador e salva o perfil."""
    profile = analyze_creator(creator, transcribe=False)
    return (
        f"Perfil de '{profile.creator}' atualizado: {profile.videos_analyzed} vídeos, "
        f"estilo={'ok' if profile.style else 'pendente'}, edição={'ok' if profile.editing else 'pendente'}."
    )


def dossier_tool(creator: str, theme: str) -> str:
    """Gera o dossiê completo de viralização de um criador aplicado ao tema do usuário."""
    return generate_dossier(creator, theme)


INSTRUCTIONS = """
Você é o estrategista do Viral Formula Studio: um sistema de engenharia reversa
da fórmula de viralização de criadores de conteúdo.

Seu papel: ajudar o usuário a (1) analisar um criador e (2) gerar o dossiê da
fórmula dele — copy, ganchos, gramática de edição e persuasão — transposta para
o tema do usuário.

Princípios:
- INSPIRAÇÃO, NÃO IMITAÇÃO: decodificamos a técnica para o usuário aplicar com a
  própria voz. Nunca entregamos conteúdo para copiar.
- HONESTIDADE: toda afirmação vem de evidência real (transcrições e frames).
  Quando a evidência for limitada, dizemos isso.
- Se o criador ainda não tiver perfil, use a ferramenta de análise antes de gerar
  o dossiê.
"""

settings = get_settings()

studio_agent = Agent(
    model=get_model(),
    name="viral_formula_studio",
    description="Engenharia reversa da fórmula de viralização de criadores.",
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
