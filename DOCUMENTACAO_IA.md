# 🧠 VIRAL FORMULA STUDIO — DOCUMENTAÇÃO E MEMÓRIA DE PROJETO 🧠

Este documento guia você ou **qualquer IA futura** sobre a arquitetura do sistema, o porquê das decisões e o estado atual do projeto.

## 🎯 Objetivo do Projeto (IBM AI Builders Challenge — Julho/2026)

**Tema:** "Reimagine Creative Industries with AI". **Deadline:** 31/07, 23:59 ET.

O produto é um **motor de engenharia reversa da fórmula de viralização de um criador**:

- **Entrada:** um criador + um tema do usuário.
- **Saída:** um dossiê completo (playbook) da fórmula *daquele criador* — copy, ganchos (com o porquê de funcionarem), gramática de edição (cortes, frames, texto na tela, pacing) e persuasão — transposto para o tema do usuário.
- **Posicionamento:** INSPIRAÇÃO, NÃO IMITAÇÃO. A fórmula migra; o conteúdo é do usuário. É a mesma coisa que um músico transcrever um solo para aprender a técnica. Nunca entregamos conteúdo para copiar.
- **Ads:** NÃO é um produto. Apenas uma menção no pitch (fórmula orgânica validada = criativo de anúncio pré-testado).

## 🏗 Arquitetura (v0.2 — remodelagem completa)

```
videos/<criador>/*.mp4
   ├─ áudio → studio/transcribe.py (Groq Whisper, retry tenacity, save incremental) → data/transcriptions.json
   └─ studio/frames.py (ffmpeg, 480p, amostragem uniforme) → data/frames/
        ↓
ESTÁGIO 1 (1x por criador, cacheado em data/profiles/<criador>.json):
   studio/analyze_text.py   → CreatorStyle (Pydantic, evidência real)
   studio/analyze_visual.py → EditingProfile (multimodal: GPT-4o hoje, Granite vision na submissão)
        ↓
ESTÁGIO 2 — SCOUT (por pedido): studio/research.py
   Fact-check web do tema via Tavily → ResearchReport (fatos COM fontes + lista "unconfirmed").
   Indisponível (sem chave/outage/429) → retorna None e o dossiê degrada para o modo estrutural.
        ↓
ESTÁGIO 3 — COMMENTATOR (por pedido): studio/dossier.py
   Perfis + fatos verificados + tema → dossiê final (6 seções), voz única do provedor ativo.
   Fatos citam fontes; o que não foi confirmado é declarado; nada vem da memória do modelo.
```

Módulos-chave:
- `studio/config.py` — pydantic-settings: chaves, paths, tuning. Tudo ancorado em `Path(__file__)` (adeus bugs de CWD).
- `studio/factory.py` — **ÚNICO lugar que conhece o provedor de LLM**. Troca OpenAI → Granite/watsonx = `MODEL_PROVIDER=watsonx` no .env.
- `studio/schemas.py` — contratos Pydantic; campos `evidence_notes` implementam a regra de honestidade.
- `studio/pipeline.py` — orquestra a análise por criador (transcreve → frames → texto + visão → salva perfil).
- `main.py` — CLI (1: analisar criador · 2: gerar dossiê). `agent.py` — UI web opcional (AgentOS :8000).

## 🔌 Troca para IBM (estratégia de submissão)

1. Preencher no `.env`: `MODEL_PROVIDER=watsonx`, `IBM_WATSONX_API_KEY`, `IBM_WATSONX_PROJECT_ID`, `IBM_WATSONX_URL`, `WATSONX_MODEL_ID` (default `ibm/granite-3-8b-instruct`).
2. O SDK `ibm-watsonx-ai` já é dependência. Agno 2.7.3 tem `agno.models.ibm.WatsonX`.
3. Nenhum agente muda — todos recebem o modelo via `factory.get_model()` / `factory.get_vision_model()`.
4. **Fallback automático (implementado e testado):** com qualquer provider ≠ openai e `OPENAI_API_KEY` presente, o agno anexa o GPT-4o como fallback (`fallback_models`). Se o watsonx falhar (conta congelada, 429 do Lite, outage), o agente continua na OpenAI. Testado em 17/07: `MODEL_PROVIDER=watsonx` com conta congelada → resposta veio via `gpt-4o` automaticamente.
5. **Modelos reais no watsonx (verificado via API em 17/07/2026):** NÃO existe Granite com visão nas regiões us-south/au-syd/eu-de. Voz = `ibm/granite-3-8b-instruct` (us-south); análise de frames = `meta-llama/llama-3-2-11b-vision-instruct` (papel de apoio — mesmo padrão híbrido do vencedor: modelo não-IBM apoia, Granite é a voz). O id `ibm/granite-vision-4-1-4b` é ALUCINAÇÃO — não usar.
6. Atenção: watsonx Lite tem limite de concorrência por minuto (erros 429) — retry com backoff é obrigatório nas chamadas.
7. **BLOQUEIO ATUAL:** conta IBM Cloud congelada (`frozen: true` no token IAM, verificado em duas chaves). Erros esperados enquanto congelada: "Failed to verify user profile existence" e "Failed to find the IBMid member in project". Resolver em cloud.ibm.com (upgrade Pay-As-You-Go / verificação / suporte) e re-testar.

## ✅ Checklist de submissão (regras verificadas)

- [ ] IBM Bob como ferramenta principal de dev (já é o ambiente do desenvolvedor) + seção "How IBM Bob Was Used" no README.
- [ ] Completar a learning activity obrigatória no skillsbuild.org.
- [ ] Repo público com README no padrão da rubrica (feito — README.md).
- [ ] Vídeo demo público de até 3 minutos (usar modo local — não depender de rede na demo).
- [ ] Submeter na plataforma BeMyApp até 31/07 23:59 ET.

## 💾 Log de decisões e alterações (v0.5)

- **Ingestão por link (`studio/ingest.py`):** usuário cola URLs (YouTube Shorts/TikTok) na opção 3 do menu — yt-dlp baixa em baixa resolução para `videos/<criador>/`, tenta legendas grátis primeiro (parser VTT próprio) e cai para Whisper da Groq quando não há legenda. Alimenta a estrutura existente: frames, métricas e análises inalterados. **Instagram:** sem acesso oficial por link — melhor esforço; falha orienta upload manual (honestidade de plataforma documentada no README).
- **Fluxo interativo de criação (simulado e aprovado pelo usuário):** 10 ganchos pela fórmula do criador → usuário escolhe 1 → copy orquestrada ≤200 palavras (~60s a 179 wpm medidos) com direções de edição medidas (corte a cada ~3,1s) e placeholder de honestidade para dados não verificados. A codificar como etapa pós-dossiê.

## 💾 Log de decisões e alterações (v0.4)

- **Camada de métricas determinísticas (`studio/metrics.py`):** a estilística do criador agora é MEDIDA, não estimada — cortes/min e duração média de take (detecção de cena ffmpeg), palavras/min (transcrição ÷ duração), n-gramas repetidos com contagem. Roda ANTES dos agentes (pipeline.py), alimenta os prompts de análise e o dossiê, que cita os números ("medido: X cortes/min"). É a resposta direta ao requisito: "produção baseada em dados e aprendizado, não IA que só escreve copy".
- **Decisão de UI (frontend futuro):** 5 campos fixos de link (um por vídeo, espelhando o limite de 5 por criador). Usuário cola um link por campo e pronto — SEM "cola inteligente" de múltiplos links (decidido pelo desenvolvedor). Fontes podem ser misturadas (Shorts/TikTok/IG) no mesmo criador.
- **Decisão registrada — sem fine-tuning:** dataset pequeno (5-10 vídeos/criador), ensinaria imitação de voz (contra o posicionamento) e não cobre edição. Medição + interpretação vence: white-box, provável e barato.
- 14 testes (novos: cut_metrics real, n-gramas com contagem, WPM).

## 💾 Log de decisões e alterações (v0.3)

- **Padrão da vencedora (kickoff-buddy) adotado:** pipeline scout→commentator. `studio/research.py` faz o fact-check do tema via Tavily (fatos com fonte + "unconfirmed"); `dossier.py` só afirma o que está nesse bloco e cita as fontes. Sem chave/falha → degrada para modo estrutural ("the feature degrades, it never dies").
- **Resiliência de modelo:** `retries=3` nativos do agno em todos os agentes + `fallback_models` (OpenAI cobre falha do watsonx — testado com a conta congelada: resposta veio via gpt-4o automaticamente).
- **Segurança/higiene:** chaves só no `.env` (gitignored), `.env` vence variáveis de máquina (bug do 401), telemetria do agno desligada (`AGNO_TELEMETRY=false`), perfis corrompidos regeneram sozinhos, guards contra erro-de-API-retornado-como-texto.
- **Teste real (17/07):** dossiê kallaway × "Kimi 3" COM fact-check — 3 fatos verificados com fontes citadas inline (llm-stats.com, YouTube, technotrenz.com) vs. versão estrutural sem fontes. Aprovado.

## 💾 Log de decisões e alterações (v0.2)

- **Removidos** (eram do modelo antigo de "imitar a voz do criador"): `agents/` (base_agent, reels/pas/ideation builders, style_extractor), `prompts/copywriter.md`, `transcripter.py`, `transcription_reader.py`.
- **Bugs corrigidos da v0.1:** path mismatch do `creators_styles.json` (salvo no CWD, lido em agents/), `style_extractor` sem `load_dotenv`, doc que prometia campo `visual_methodology` inexistente, `agent.py` com `show_tool_calls` (parâmetro inexistente no agno 2.7.3 — quebrava na importação), emojis quebrando console Windows (cp1252).
- **Dados migrados:** `transcriptions.json` → `data/transcriptions.json`.
- **Dossiê:** estrutura fixa de 6 seções (voz / gancho / copy / edição / persuasão / plano de ação) com regras de honestidade ("[evidência limitada]").
- **Testes:** 9 testes pytest, incluindo extração real de frames via ffmpeg (não precisam de chaves de API).

## 🔮 Roadmap pós-submissão

- Ingestão por link (yt-dlp): usuário cola URL do YouTube/TikTok em vez de upar vídeos (legendas primeiro, Whisper como fallback). Desenhado, não implementado — verificar se faz sentido após a submissão.
- Deploy público com rate limiting (padrão do vencedor de junho).
