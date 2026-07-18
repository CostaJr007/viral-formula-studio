import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  ArrowRight,
  Brain,
  Camera,
  Check,
  Copy as CopyIcon,
  Download,
  Eye,
  FileText,
  Globe,
  Loader2,
  Film,
  Gauge,
  Link as LinkIcon,
  Mic,
  Music,
  Play,
  RotateCcw,
  Scissors,
  Sparkle,
  Target,
  Trash2,
  Wand2,
  Waves,
  Youtube,
  Zap,
} from "lucide-react";

import logoUrl from "../assets/logo.png";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: Studio,
});

/* ---------------- API client ---------------- */

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    if (res.status === 429) {
      throw new Error(`Rate limit reached: ${detail.slice(0, 200)}`);
    }
    throw new Error(detail.slice(0, 300) || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

type Profile = {
  creator: string;
  videos_analyzed: number;
  metrics?: {
    editing?: {
      avg_cuts_per_min?: number;
      avg_shot_length_s?: number;
      videos_measured?: number;
      total_duration_s?: number;
    };
    speech?: { avg_wpm?: number };
    signature_ngrams?: { ngram: string; count: number }[];
  };
  style?: {
    tone: string;
    sentence_rhythm: string;
    persona: string;
    copy_structure: string;
    signature_expressions: string[];
    hook_patterns: { pattern: string; why_it_works: string; example: string }[];
    persuasion_tactics: string[];
    evidence_notes: string;
  };
  editing?: {
    cut_cadence: string;
    shot_types: string;
    text_overlay_style: string;
    b_roll_usage: string;
    visual_identity: string;
    retention_tricks: string[];
    evidence_notes: string;
  };
};

type Hook = { text: string; pattern: string };

type CopyResult = {
  script: string;
  editing_directions: string[];
  data_notes: string;
  word_count: number;
};

type StepId = "creator" | "profile" | "hooks" | "copy";

const STEPS: { id: StepId; label: string; hint: string; icon: typeof LinkIcon }[] = [
  { id: "creator", label: "Creator", hint: "5 Shorts / TikTok links", icon: LinkIcon },
  { id: "profile", label: "Profile", hint: "measured formula", icon: Gauge },
  { id: "hooks", label: "Hooks", hint: "10 derived hooks", icon: Target },
  { id: "copy", label: "Copy", hint: "script ≤200 words", icon: Wand2 },
];

function Studio() {
  const [step, setStep] = useState<StepId>("creator");
  const [creatorName, setCreatorName] = useState("");
  const [links, setLinks] = useState<string[]>(["", "", "", "", ""]);
  const [topic, setTopic] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [hooksLoading, setHooksLoading] = useState(false);
  const [pickedHook, setPickedHook] = useState<number | null>(null);
  const [copyResult, setCopyResult] = useState<CopyResult | null>(null);
  const [generatingCopy, setGeneratingCopy] = useState(false);

  const validLinks = links.filter((l) => l.trim().startsWith("http"));
  const canAnalyze = creatorName.trim().length >= 2 && validLinks.length >= 1 && topic.trim().length >= 3;

  const stepIndex = STEPS.findIndex((s) => s.id === step);
  const progress = ((stepIndex + 1) / STEPS.length) * 100;

  async function runAnalysis() {
    setAnalyzing(true);
    setError(null);
    setJobStatus("Queuing ingestion…");
    try {
      const { job_id } = await apiPost<{ job_id: string; remaining?: number }>("/api/ingest", {
        creator: creatorName.trim(),
        urls: validLinks,
      });

      for (;;) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await (await fetch(`${API}/api/jobs/${job_id}`)).json();
        if (job.status === "done") break;
        if (job.status === "failed") throw new Error(job.error ?? "Analysis failed");
        setJobStatus(
          job.status === "ingesting"
            ? "Downloading & transcribing videos…"
            : job.status === "analyzing"
              ? "Measuring cuts + analyzing style & editing…"
              : "Queued…",
        );
      }

      const prof = await (await fetch(`${API}/api/profile/${encodeURIComponent(creatorName.trim())}`)).json();
      setProfile(prof);
      setStep("profile");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
      setJobStatus(null);
    }
  }

  async function goHooks(newTopic?: string) {
    const theme = (newTopic ?? topic).trim();
    if (newTopic) setTopic(newTopic);
    setStep("hooks");
    setHooksLoading(true);
    setError(null);
    setPickedHook(null);
    try {
      const data = await apiPost<{ hooks: Hook[] }>("/api/hooks", {
        creator: creatorName.trim(),
        topic: theme,
        profile: profile ?? undefined,  // pass cached profile to survive container restarts
      });
      setHooks(data.hooks);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setHooksLoading(false);
    }
  }

  async function generateCopy() {
    if (pickedHook === null || !hooks[pickedHook]) return;
    setGeneratingCopy(true);
    setError(null);
    try {
      const result = await apiPost<CopyResult>("/api/copy", {
        creator: creatorName.trim(),
        topic: topic.trim(),
        hook: hooks[pickedHook].text,
        profile: profile ?? undefined,
      });
      setCopyResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGeneratingCopy(false);
    }
  }

  async function exportDossier() {
    try {
      const data = await apiPost<{ markdown: string }>("/api/dossier", {
        creator: creatorName.trim(),
        topic: topic.trim(),
        profile: profile ?? undefined,
      });
      const blob = new Blob([data.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dossier_${creatorName.trim()}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function exportPdfReport() {
    setError(null);
    try {
      const data = await apiPost<{ markdown: string }>("/api/dossier", {
        creator: creatorName.trim(),
        topic: topic.trim(),
        profile: profile ?? undefined,
      });
      // Convert basic markdown to print-friendly HTML
      const safeTitle = `Viral Formula Studio — ${creatorName.trim()} × ${topic.trim()}`;
      const html = markdownToPrintHtml(data.markdown, safeTitle);
      const w = window.open("", "_blank");
      if (!w) { setError("Popup blocked — allow popups for PDF export."); return; }
      w.document.write(html);
      w.document.close();
      w.onload = () => w.print();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function restart() {
    setStep("creator");
    setProfile(null);
    setHooks([]);
    setPickedHook(null);
    setCopyResult(null);
    setError(null);
  }

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Sidebar */}
      <aside className="hidden md:flex w-72 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground relative">
        <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
        <div className="relative p-6 flex items-center gap-3">
          <div className="relative">
            <div className="absolute -inset-1 rounded-xl bg-primary/30 blur-md" />
            <img src={logoUrl} alt="" className="relative h-9 w-9" />
          </div>
          <div className="leading-tight">
            <div className="font-display font-semibold text-[15px]">Viral Formula</div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Studio
            </div>
          </div>
        </div>

        <Separator className="bg-sidebar-border relative" />

        <nav className="relative p-4">
          <div className="px-2 pb-3 text-[10px] uppercase tracking-[0.24em] text-muted-foreground flex items-center gap-2">
            <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
            Workflow
            <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
          </div>
          <div className="relative">
            <span className="absolute left-[26px] top-4 bottom-4 w-px bg-gradient-to-b from-border via-border to-transparent" />
            <div className="space-y-1 relative">
          {STEPS.map((s, i) => {
            const active = s.id === step;
            const done = i < stepIndex || (s.id === "creator" && profile !== null);
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => (s.id === "creator" || profile !== null ? setStep(s.id) : null)}
                disabled={s.id !== "creator" && profile === null}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-lg flex items-start gap-3 transition-all group relative",
                  active && "bg-sidebar-accent shadow-glow ring-1 ring-primary/40",
                  !active &&
                    "hover:bg-sidebar-accent/60 disabled:opacity-40 disabled:cursor-not-allowed",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-7 w-7 items-center justify-center rounded-lg border text-[11px] font-mono font-medium shrink-0 transition-all",
                    active
                      ? "border-primary bg-primary text-primary-foreground shadow-glow"
                      : done
                        ? "border-success/60 bg-success/20 text-success"
                        : "border-border bg-background text-muted-foreground",
                  )}
                >
                  {done && !active ? <Check className="h-3.5 w-3.5" /> : String(i + 1).padStart(2, "0")}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Icon className="h-3.5 w-3.5 opacity-80" />
                    {s.label}
                  </span>
                  <span className="block text-xs text-muted-foreground mt-0.5">{s.hint}</span>
                </span>
                {active && (
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                )}
              </button>
            );
          })}
            </div>
          </div>
        </nav>

        <div className="relative mt-auto p-4 space-y-3">
          <Card className="bg-sidebar-accent/40 border-sidebar-border p-4 relative overflow-hidden">
            <div className="absolute -top-8 -right-8 h-24 w-24 rounded-full bg-primary/20 blur-2xl" />
            <div className="relative flex items-center gap-2 text-xs font-medium">
              <Sparkle className="h-3.5 w-3.5 text-primary" />
              Powered by IBM Granite
            </div>
            <p className="relative text-[11px] text-muted-foreground mt-2 leading-relaxed">
              Multimodal analysis with watsonx.ai. Whisper for transcription, Tavily for
              fact checking.
            </p>
          </Card>
          <div className="text-[10px] text-muted-foreground px-2 font-mono uppercase tracking-widest">
            IBM AI Builders · 2026
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 relative">
        <div className="absolute inset-0 bg-hero pointer-events-none" />
        <div className="absolute inset-0 bg-grid pointer-events-none opacity-60 hidden sm:block" />

        <div className="relative">
          {/* Top bar */}
          <div className="border-b border-border/60 backdrop-blur-md bg-background/70 sticky top-0 z-10">
            <div className="max-w-5xl mx-auto px-4 md:px-10 py-3 md:py-4 flex items-center gap-3 md:gap-4">
              <div className="md:hidden flex items-center gap-2 shrink-0">
                <img src={logoUrl} alt="" className="h-6 w-6" />
              </div>
              <div className="flex-1 flex items-center gap-2 md:gap-3">
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground tabular-nums shrink-0">
                  {String(stepIndex + 1).padStart(2, "0")}/{String(STEPS.length).padStart(2, "0")}
                </span>
                <Progress value={progress} className="h-1 flex-1" />
                <span className="hidden sm:inline text-[10px] font-mono uppercase tracking-[0.2em] text-primary tabular-nums">
                  {Math.round(progress)}%
                </span>
              </div>
              <Badge variant="outline" className="shrink-0 gap-1.5 border-success/40 bg-success/5 text-[10px] px-2 py-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse hidden sm:inline" />
                Granite
              </Badge>
              {profile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={restart}
                  className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">New</span>
                </Button>
              )}
            </div>
          </div>

          <div className="max-w-5xl mx-auto px-4 md:px-10 py-6 md:py-14">
            {error && (
              <Card className="mb-6 p-4 border-destructive/50 bg-destructive/10 text-sm text-destructive-foreground">
                {error}
              </Card>
            )}

            {step === "creator" && (
              <CreatorStep
                creatorName={creatorName}
                setCreatorName={setCreatorName}
                links={links}
                setLinks={setLinks}
                topic={topic}
                setTopic={setTopic}
                canAnalyze={canAnalyze}
                analyzing={analyzing}
                jobStatus={jobStatus}
                runAnalysis={runAnalysis}
              />
            )}

            {step === "profile" && <ProfileStep profile={profile} onNext={goHooks} />}

            {step === "hooks" && (
              <HooksStep
                topic={topic || "your topic"}
                setTopic={setTopic}
                hooks={hooks}
                loading={hooksLoading}
                pickedHook={pickedHook}
                setPickedHook={setPickedHook}
                onRegenerate={goHooks}
                onNext={() => setStep("copy")}
              />
            )}

            {step === "copy" && (
              <CopyStep
                hook={pickedHook !== null && hooks[pickedHook] ? hooks[pickedHook].text : ""}
                generating={generatingCopy}
                result={copyResult}
                onGenerate={generateCopy}
                onExport={exportDossier}
                onExportPdf={exportPdfReport}
                onRestart={restart}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

/* ---------------- Step 1: Creator ---------------- */

function CreatorStep({
  creatorName,
  setCreatorName,
  links,
  setLinks,
  topic,
  setTopic,
  canAnalyze,
  analyzing,
  jobStatus,
  runAnalysis,
}: {
  creatorName: string;
  setCreatorName: (v: string) => void;
  links: string[];
  setLinks: (v: string[]) => void;
  topic: string;
  setTopic: (v: string) => void;
  canAnalyze: boolean;
  analyzing: boolean;
  jobStatus: string | null;
  runAnalysis: () => void;
}) {
  const filled = links.filter((l) => l.trim().startsWith("http")).length;

  return (
    <div className="space-y-10">
      <header className="space-y-4 max-w-3xl">
        <Badge variant="outline" className="gap-1.5">
          <Waves className="h-3 w-3" /> Step 1 of 4
        </Badge>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          Paste up to 5 videos <span className="text-gradient">from the creator</span>{" "}
          you want to study.
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          The AI watches the creator's Shorts, learns their editing rhythm, hook
          patterns and narrative cadence — then transposes that formula onto your topic.
          <strong className="text-foreground"> No templates. No guessing.</strong>
        </p>

        {/* Supported platforms */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground mr-1">Accepts</span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-3 py-1 text-xs">
            <Youtube className="h-3.5 w-3.5 text-red-400" />
            YouTube Shorts
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-3 py-1 text-xs">
            <Music className="h-3.5 w-3.5 text-pink-400" />
            TikTok
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-3 py-1 text-xs">
            <Camera className="h-3.5 w-3.5 text-purple-400" />
            Instagram Reels
          </span>
        </div>
      </header>

      {/* How AI learns — 3 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: Eye, label: "Watch", text: "AI ingests up to 5 Shorts from any public creator profile — downloads, extracts frames and transcribes captions.", color: "text-blue-400" },
          { icon: Brain, label: "Learn", text: "Reverse-engineers the creator's formula: cuts/min, WPM, hook patterns, tone, editing grammar — measured, not guessed.", color: "text-primary" },
          { icon: Wand2, label: "Create", text: "Generates your script (≤200 words) with hooks and editing directions transposed from the creator's proven style.", color: "text-green-400" },
        ].map(({ icon: Icon, label, text, color }) => (
          <Card key={label} className="p-5 bg-card/60 backdrop-blur-sm border-border/50 space-y-3 relative overflow-hidden">
            <div className="absolute -top-6 -right-6 h-16 w-16 rounded-full bg-primary/10 blur-xl" />
            <div className="relative flex items-center gap-3">
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/60", color)}>
                <Icon className="h-5 w-5" />
              </span>
              <span className="font-display font-semibold text-sm">{label}</span>
            </div>
            <p className="relative text-xs text-muted-foreground leading-relaxed">{text}</p>
          </Card>
        ))}
      </div>

      {analyzing ? (
        <AnalysisProgress jobStatus={jobStatus} />
      ) : (
        <>
      <div className="grid lg:grid-cols-5 gap-6">
        <Card className="lg:col-span-3 p-4 md:p-7 space-y-4 md:space-y-5 bg-card/70 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-display font-medium text-sm">Reference creator links</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Public YouTube Shorts, TikTok or Reels.
              </div>
            </div>
            <span className="font-mono text-xs text-muted-foreground tabular-nums shrink-0 ml-2">
              {filled} / 5
            </span>
          </div>

          <div>
            <Label htmlFor="creator-name" className="font-display font-medium text-sm">
              Creator name
            </Label>
            <Input
              id="creator-name"
              value={creatorName}
              onChange={(e) => setCreatorName(e.target.value)}
              placeholder="e.g. jeffnippard"
              className="mt-2 bg-background/60 h-10"
            />
          </div>

          <div className="space-y-2 md:space-y-2.5">
            {links.map((link, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <span className="font-mono text-[11px] text-muted-foreground w-5 md:w-6 text-right shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="relative flex-1 min-w-0">
                  <LinkIcon className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={link}
                    onChange={(e) => {
                      const next = [...links];
                      next[i] = e.target.value;
                      setLinks(next);
                    }}
                    placeholder="https://www.youtube.com/shorts/..."
                    className="pl-9 bg-background/60 font-mono text-xs h-10"
                  />
                </div>
                {link && (
                  <button
                    onClick={() => {
                      const next = [...links];
                      next[i] = "";
                      setLinks(next);
                    }}
                    className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 transition shrink-0"
                    aria-label="Clear"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2 p-4 md:p-7 space-y-4 md:space-y-5 bg-card/70 backdrop-blur-sm">
          <div>
            <Label htmlFor="topic" className="font-display font-medium text-sm">
              Your topic
            </Label>
            <p className="text-xs text-muted-foreground mt-1">
              What YOUR video will be about — the creator's formula gets transposed onto
              it.
            </p>
          </div>
          <Textarea
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. how small businesses can use AI without coding."
            rows={5}
            className="bg-background/60 resize-none"
          />
          <div className="rounded-lg border border-border/60 bg-secondary/40 p-3 text-[11px] text-muted-foreground leading-relaxed">
            <span className="text-foreground font-medium">Scout enabled:</span> we verify
            checkable facts about your topic (via Tavily) and cite the sources.
          </div>
        </Card>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2">
        <div className="text-xs text-muted-foreground flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5">
            <Scissors className="h-3.5 w-3.5" /> cuts/min
          </span>
          <span className="flex items-center gap-1.5">
            <Film className="h-3.5 w-3.5" /> shot length
          </span>
          <span className="flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5" /> signature n-grams
          </span>
        </div>
        <Button
          size="lg"
          disabled={!canAnalyze || analyzing}
          onClick={runAnalysis}
          className="min-w-[220px] shadow-glow"
        >
          Decode formula
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
        </>
      )}
    </div>
  );
}

/* ---------------- Analysis progress (phased) ---------------- */

const ANALYSIS_PHASES = [
  { key: "download", label: "Downloading videos", sub: "Pulling public Shorts / TikTok data", icon: Globe },
  { key: "transcribe", label: "Transcribing", sub: "Captions first, Whisper as fallback", icon: Mic },
  { key: "analyze", label: "Analyzing style & editing", sub: "Measuring cuts/min, WPM, and running LLM analysis", icon: Sparkle },
] as const;

type PhaseKey = (typeof ANALYSIS_PHASES)[number]["key"];

function AnalysisProgress({ jobStatus }: { jobStatus: string | null }) {
  const phase: PhaseKey = jobStatus === "analyzing" ? "analyze" : jobStatus === "ingesting" ? "transcribe" : "download";

  return (
    <Card className="p-6 md:p-10 bg-card/70 backdrop-blur-sm text-center space-y-6 md:space-y-8 max-w-2xl mx-auto">
      <div className="space-y-2">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary">
          <Loader2 className="h-7 w-7 animate-spin" />
        </div>
        <h2 className="font-display text-xl font-semibold mt-4">Decoding the formula</h2>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          This takes ~30–90 seconds depending on video count. The engine pulls, transcribes, measures and analyzes each one.
        </p>
      </div>

      <div className="space-y-3">
        {ANALYSIS_PHASES.map((p, i) => {
          const idx = ANALYSIS_PHASES.findIndex((x) => x.key === phase);
          const done = i < idx;
          const active = i === idx;
          const pending = i > idx;
          const Icon = p.icon;

          return (
            <div
              key={p.key}
              className={cn(
                "flex items-center gap-4 p-4 rounded-xl border transition-all",
                active && "border-primary/50 bg-primary/5 shadow-glow",
                done && "border-success/30 bg-success/5",
                pending && "border-border/40 bg-secondary/20 opacity-50",
              )}
            >
              <span
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-lg shrink-0 transition-all",
                  active && "bg-primary text-primary-foreground",
                  done && "bg-success/20 text-success",
                  pending && "bg-secondary text-muted-foreground",
                )}
              >
                {done ? <Check className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
              </span>
              <div className="text-left flex-1 min-w-0">
                <div className={cn("text-sm font-medium", active && "text-foreground", done && "text-foreground", pending && "text-muted-foreground")}>
                  {p.label}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">{p.sub}</div>
              </div>
              {done && <Check className="h-4 w-4 text-success shrink-0" />}
            </div>
          );
        })}
      </div>

      <p className="text-[11px] text-muted-foreground font-mono">
        {jobStatus === "analyzing" ? "LLM interpreting measurements — this is the longest step" : "Processing…"}
      </p>
    </Card>
  );
}

/* ---------------- Step 2: Profile ---------------- */

function ProfileStep({ profile, onNext }: { profile: Profile | null; onNext: () => void }) {
  if (!profile) return null;

  const editingM = profile.metrics?.editing;
  const speechM = profile.metrics?.speech;
  const ngrams = profile.metrics?.signature_ngrams ?? [];

  const metricCards = [
    { label: "Cuts / min", value: editingM?.avg_cuts_per_min ?? "—", unit: "" },
    { label: "Avg shot length", value: editingM?.avg_shot_length_s ?? "—", unit: "s" },
    { label: "Words / min", value: speechM?.avg_wpm ?? "—", unit: "" },
    { label: "Videos analyzed", value: profile.videos_analyzed, unit: "" },
  ];

  return (
    <div className="space-y-10">
      <header className="space-y-4 max-w-3xl">
        <Badge variant="outline" className="gap-1.5">
          <Gauge className="h-3 w-3" /> Step 2 of 4
        </Badge>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          Formula <span className="text-gradient">measured</span>, not guessed.
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          This is what the evidence shows — numbers from ffmpeg plus stylistic reading
          from the vision model. Each line here becomes an instruction in the final
          script.
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricCards.map((m) => (
          <Card key={m.label} className="p-5 bg-card/70 relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-primary" />
            <div className="text-xs text-muted-foreground uppercase tracking-wider">{m.label}</div>
            <div className="mt-3 font-display text-3xl font-semibold tabular-nums">
              {m.value}
              <span className="text-base text-muted-foreground ml-1">{m.unit}</span>
            </div>
            <div className="mt-2 text-[10px] font-mono text-muted-foreground">
              measured · deterministic
            </div>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-6 md:p-7 bg-card/70 space-y-4">
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary" />
            <h3 className="font-display font-medium">Copy fingerprint</h3>
          </div>
          {profile.style ? (
            <>
              <p className="text-sm text-muted-foreground leading-relaxed">
                <strong className="text-foreground">{profile.style.tone}</strong> —{" "}
                {profile.style.persona}. {profile.style.sentence_rhythm}
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {profile.style.copy_structure}
              </p>
              <Separator />
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Signature phrases (measured)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(ngrams.length > 0
                    ? ngrams.slice(0, 6).map((g) => `${g.ngram} (${g.count}x)`)
                    : profile.style.signature_expressions
                  ).map((n) => (
                    <Badge key={n} variant="secondary" className="font-mono text-[11px]">
                      {n}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Hook patterns
                </div>
                <ul className="space-y-2 text-sm">
                  {profile.style.hook_patterns.map((h) => (
                    <li key={h.pattern} className="text-muted-foreground">
                      <span className="text-foreground font-medium">{h.pattern}</span> —{" "}
                      {h.why_it_works}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No textual analysis available.</p>
          )}
        </Card>

        <Card className="p-6 md:p-7 bg-card/70 space-y-4">
          <div className="flex items-center gap-2">
            <Film className="h-4 w-4 text-primary" />
            <h3 className="font-display font-medium">Editing grammar</h3>
          </div>
          {profile.editing ? (
            <ul className="space-y-3 text-sm">
              {[
                profile.editing.cut_cadence,
                profile.editing.shot_types,
                profile.editing.text_overlay_style,
                profile.editing.b_roll_usage,
                profile.editing.visual_identity,
                ...profile.editing.retention_tricks,
              ].map((line) => (
                <li key={line} className="flex gap-3">
                  <Check className="h-4 w-4 text-success shrink-0 mt-0.5" />
                  <span className="text-muted-foreground">{line}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No visual analysis available.</p>
          )}
        </Card>
      </div>

      {(profile.style?.evidence_notes || profile.editing?.evidence_notes) && (
        <Card className="p-5 bg-secondary/30 border-dashed">
          <div className="text-sm">
            <span className="text-foreground font-medium">Evidence notes.</span>{" "}
            <span className="text-muted-foreground">
              {profile.style?.evidence_notes} {profile.editing?.evidence_notes}
            </span>
          </div>
        </Card>
      )}

      <div className="flex justify-end">
        <Button size="lg" onClick={onNext} className="min-w-[200px] shadow-glow">
          Generate 10 hooks
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/* ---------------- Step 3: Hooks ---------------- */

function HooksStep({
  topic,
  setTopic,
  hooks,
  loading,
  pickedHook,
  setPickedHook,
  onRegenerate,
  onNext,
}: {
  topic: string;
  setTopic: (v: string) => void;
  hooks: Hook[];
  loading: boolean;
  pickedHook: number | null;
  setPickedHook: (i: number) => void;
  onRegenerate: (topic: string) => void;
  onNext: () => void;
}) {
  const [editingTopic, setEditingTopic] = useState(false);

  return (
    <div className="space-y-10">
      <header className="space-y-4 max-w-3xl">
        <Badge variant="outline" className="gap-1.5">
          <Target className="h-3 w-3" /> Step 3 of 4
        </Badge>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          10 hooks <span className="text-gradient">in the creator's technique</span>, on
          your topic.
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          Every hook follows a measured pattern from the creator's fingerprint. Pick one
          — it becomes the seed of the script.
        </p>

        {/* Change topic inline */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {editingTopic ? (
            <div className="flex items-center gap-2">
              <Input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="New topic..."
                className="h-9 w-56 bg-background/60 text-sm"
              />
              <Button
                size="sm"
                disabled={topic.trim().length < 3 || loading}
                onClick={() => { setEditingTopic(false); onRegenerate(topic); }}
              >
                Regenerate
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setEditingTopic(false); setTopic(topic); }}>
                Cancel
              </Button>
            </div>
          ) : (
            <button
              onClick={() => setEditingTopic(true)}
              className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Wand2 className="h-3 w-3" />
              Change topic: <span className="text-foreground font-medium">{topic}</span>
            </button>
          )}
        </div>
      </header>

      {loading && (
        <Card className="p-10 bg-card/70 text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <div className="font-display">Deriving hooks from the measured formula…</div>
          <p className="text-sm text-muted-foreground">
            Fact-checking "{topic}" and injecting verified facts.
          </p>
        </Card>
      )}

      {!loading && hooks.length > 0 && (
        <div className="grid md:grid-cols-2 gap-3">
          {hooks.map((h, i) => {
            const active = pickedHook === i;
            return (
              <button
                key={i}
                onClick={() => setPickedHook(i)}
                className={cn(
                  "text-left p-5 rounded-xl border transition-all group relative",
                  active
                    ? "border-primary bg-primary/10 shadow-glow"
                    : "border-border bg-card/60 hover:border-primary/40 hover:bg-card",
                )}
              >
                <div className="flex items-start gap-3">
                  <span
                    className={cn(
                      "font-mono text-[11px] font-medium h-6 w-6 rounded-md flex items-center justify-center shrink-0 mt-0.5",
                      active ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground",
                    )}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="flex-1">
                    <p className="text-sm leading-relaxed">{h.text}</p>
                    <p className="text-[11px] text-muted-foreground mt-2 font-mono">{h.pattern}</p>
                  </span>
                  {active && <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />}
                </div>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2">
        <p className="text-xs text-muted-foreground">
          {pickedHook !== null
            ? `Hook ${String(pickedHook + 1).padStart(2, "0")} selected.`
            : "Pick a hook to generate the full script."}
        </p>
        <Button size="lg" disabled={pickedHook === null} onClick={onNext} className="min-w-[220px] shadow-glow">
          Write script
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/* ---------------- Step 4: Copy ---------------- */

function markdownToPrintHtml(md: string, title: string): string {
  // Simple markdown-to-HTML for print-friendly PDF export
  let html = md
    .replace(/### (.+)/g, "<h3>$1</h3>")
    .replace(/## (.+)/g, "<h2>$1</h2>")
    .replace(/# (.+)/g, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n- (.+)/g, "\n<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
    .replace(/\|(.+)\|/g, (m) => m.replace(/\|/g, " "))  // rough table → text
    .replace(/<br>/g, "")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");

  html = `<p>${html}</p>`;

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
<style>
  @page { margin: 2cm; size: A4; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; font-size: 11pt; line-height: 1.6; color: #1a1a1a; max-width: 700px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 20pt; color: #0d0f1f; border-bottom: 3px solid #0f62fe; padding-bottom: 8px; }
  h2 { font-size: 14pt; color: #0f62fe; margin-top: 28px; }
  h3 { font-size: 12pt; color: #333; }
  strong { color: #0d0f1f; }
  code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 10pt; }
  ul { padding-left: 20px; }
  li { margin-bottom: 4px; }
  p { margin: 8px 0; }
  @media print { body { padding: 0; } }
</style></head><body>${html}</body></html>`;
}

function CopyStep({
  hook,
  generating,
  result,
  onGenerate,
  onExport,
  onExportPdf,
  onRestart,
}: {
  hook: string;
  generating: boolean;
  result: CopyResult | null;
  onGenerate: () => void;
  onExport: () => void;
  onExportPdf: () => void;
  onRestart: () => void;
}) {
  return (
    <div className="space-y-10">
      <header className="space-y-4 max-w-3xl">
        <Badge variant="outline" className="gap-1.5">
          <Wand2 className="h-3 w-3" /> Step 4 of 4
        </Badge>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          Your script, <span className="text-gradient">ready to shoot</span>.
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          Up to 200 words, in the creator's cadence, with editing directions aligned to
          the metrics. Nothing here is a guess — it's evidence transposed.
        </p>
      </header>

      {!result && !generating && (
        <Card className="p-10 bg-card/70 text-center space-y-5 border-dashed">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-glow">
            <Play className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-display text-xl">Orchestrate final copy</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              The commentator writes grounded ONLY in collected evidence. No
              hallucination, no fluff.
            </p>
            {hook && (
              <p className="text-sm text-foreground max-w-md mx-auto pt-2">
                Hook: “{hook}”
              </p>
            )}
          </div>
          <Button size="lg" onClick={onGenerate} className="shadow-glow" disabled={!hook}>
            Generate script <ArrowRight className="h-4 w-4" />
          </Button>
        </Card>
      )}

      {generating && (
        <Card className="p-10 bg-card/70 text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <div className="font-display">Writing the script…</div>
          <p className="text-sm text-muted-foreground">
            Injecting profile + verified facts into the prompt.
          </p>
        </Card>
      )}

      {result && (
        <div className="grid lg:grid-cols-5 gap-6">
          <Card className="lg:col-span-3 p-6 md:p-8 bg-card/70 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  script · {result.word_count} words
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => navigator.clipboard?.writeText(result.script)}
              >
                <CopyIcon className="h-3.5 w-3.5" /> Copy
              </Button>
            </div>
            <Separator />
            <div className="whitespace-pre-wrap text-[15px] leading-[1.75] font-sans">
              {result.script}
            </div>
          </Card>

          <Card className="lg:col-span-2 p-6 md:p-7 bg-card/70 space-y-5">
            <div className="flex items-center gap-2">
              <Scissors className="h-4 w-4 text-primary" />
              <h3 className="font-display font-medium">Editing directions</h3>
            </div>
            <ol className="space-y-4">
              {result.editing_directions.map((d, i) => (
                <li key={i} className="flex gap-3">
                  <span className="font-mono text-[11px] text-primary shrink-0 pt-0.5">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-sm text-muted-foreground leading-relaxed">{d}</span>
                </li>
              ))}
            </ol>
            <Separator />
            <div className="text-[11px] text-muted-foreground leading-relaxed">
              <span className="text-foreground font-medium">Data notes:</span>{" "}
              {result.data_notes}
            </div>
          </Card>

          <div className="lg:col-span-5 flex flex-wrap gap-3 justify-end pt-2">
            <Button variant="outline" onClick={onRestart}>
              Study another creator
            </Button>
            <Button variant="outline" className="shadow-glow" onClick={onExportPdf}>
              PDF <FileText className="h-4 w-4 ml-1.5" />
            </Button>
            <Button className="shadow-glow" onClick={onExport}>
              Export .md <Download className="h-4 w-4 ml-1.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
