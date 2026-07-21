import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import {
  ArrowRight,
  Brain,
  Camera,
  Check,
  Copy as CopyIcon,
  Eye,
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
  thumbnail?: {
    composition: string;
    dominant_colors: string[];
    contrast_level: string;
    facial_expression: string | null;
    text_readability: string | null;
    score: number;
    suggestions: string[];
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

type StepId = "creator" | "profile" | "topic-select" | "hooks" | "copy";

const STEPS: { id: StepId; label: string; hint: string; icon: typeof LinkIcon }[] = [
  { id: "creator", label: "Creator", hint: "5 Shorts / TikTok links", icon: LinkIcon },
  { id: "profile", label: "Profile", hint: "measured formula", icon: Gauge },
  { id: "topic-select", label: "Topic", hint: "your theme", icon: Target },
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

  // Warm up API in background — don't block initial render
  useEffect(() => {
    const t = setTimeout(() => fetch(`${API}/api/health`).catch(() => {}), 500);
    return () => clearTimeout(t);
  }, []);

  const validLinks = links.filter((l) => l.trim().startsWith("http"));
  const isSeedCreator = ["bryan", "jeffnippard", "kallaway"].includes(creatorName.trim().toLowerCase());
  const canAnalyze = creatorName.trim().length >= 2 && (validLinks.length >= 1 || isSeedCreator) && topic.trim().length >= 3;

  const stepIndex = STEPS.findIndex((s) => s.id === step);
  const progress = ((stepIndex + 1) / STEPS.length) * 100;

  async function runAnalysis() {
    setAnalyzing(true);
    setError(null);

    // Seed creator without links — skip ingestion, load cached profile directly
    if (isSeedCreator && validLinks.length === 0) {
      try {
        setJobStatus("Loading pre-analyzed profile...");
        const prof = await (await fetch(`${API}/api/profile/${encodeURIComponent(creatorName.trim())}`)).json();
        setProfile(prof);
        setStep("profile");
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setAnalyzing(false);
        setJobStatus(null);
      }
      return;
    }

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
    console.log("[goHooks] called, topic:", topic, "profile:", !!profile, "creatorName:", creatorName);
    const theme = (newTopic ?? topic).trim();
    if (newTopic) setTopic(newTopic);
    setError(null);
    setHooksLoading(true);
    setPickedHook(null);
    setStep("hooks");
    console.log("[goHooks] advancing to hooks step");
    try {
      const data = await apiPost<{ hooks: Hook[] }>("/api/hooks", {
        creator: creatorName.trim(),
        topic: theme,
        profile: profile ?? undefined,
      });
      console.log("[goHooks] received", data.hooks?.length, "hooks");
      setHooks(data.hooks);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStep("profile");  // go back on error
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

  function newTopic() {
    setPickedHook(null);
    setCopyResult(null);
    setHooks([]);
    setStep("topic-select");
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
            <button onClick={restart} className="relative cursor-pointer" title="Home">
              <img src={logoUrl} alt="Viral Formula Studio" className="relative h-9 w-9" />
            </button>
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
                <button onClick={restart} className="cursor-pointer" title="Home">
                  <img src={logoUrl} alt="Viral Formula Studio" className="h-6 w-6" />
                </button>
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

            {step === "topic-select" && (
              <TopicSelectStep
                topic={topic || "your topic"}
                setTopic={setTopic}
                onGenerate={(t) => goHooks(t)}
              />
            )}

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
                onNewTopic={newTopic}
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
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground mr-0.5">Accepts</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-secondary/40 px-2.5 py-1 text-[11px]">
            <Youtube className="h-3 w-3 text-red-400" />
            Shorts
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-secondary/40 px-2.5 py-1 text-[11px]">
            <Music className="h-3 w-3 text-pink-400" />
            TikTok
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-secondary/40 px-2.5 py-1 text-[11px]">
            <Camera className="h-3 w-3 text-purple-400" />
            Reels
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

      {/* Demo presets — instant access to pre-analyzed creators */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
          <span className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">Try a Demo</span>
          <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { name: "Bryan", topic: "optimal morning routine for longevity", emoji: "🧬", desc: "Biohacking & longevity creator — slow cuts, data-driven tone" },
            { name: "jeffnippard", topic: "science-based hypertrophy training", emoji: "💪", desc: "Fitness science creator — fast cuts, technical authority" },
            { name: "kallaway", topic: "building consistent coding habits", emoji: "💻", desc: "Tech/productivity creator — motivational, story-driven" },
          ].map((demo) => (
            <button
              key={demo.name}
              onClick={() => {
                setCreatorName(demo.name);
                setTopic(demo.topic);
              }}
              className="text-left p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm hover:border-primary/40 hover:bg-card transition-all group relative overflow-hidden"
            >
              <div className="absolute -top-4 -right-4 h-12 w-12 rounded-full bg-primary/10 blur-xl group-hover:bg-primary/20 transition" />
              <div className="relative">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{demo.emoji}</span>
                  <span className="font-display font-semibold text-sm">{demo.name}</span>
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0 ml-auto">DEMO</Badge>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">{demo.desc}</p>
                <div className="mt-2 flex items-center gap-1 text-[10px] text-primary font-mono">
                  <Zap className="h-3 w-3" />
                  Instant · No upload needed
                </div>
              </div>
            </button>
          ))}
        </div>
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
          id="decode-btn"
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
  { id: "Agent 0", name: "ffmpeg + yt-dlp", desc: "Data ingestion & deterministic metrics", delay: 0, duration: 6 },
  { id: "Agent 4.1", name: "Textual Analyst", desc: "Extracting copy fingerprint & tone", delay: 6, duration: 25 },
  { id: "Agent 4.2", name: "Visual Editor", desc: "Decoding editing grammar from frames", delay: 6, duration: 30 },
  { id: "Agent 4.5", name: "Thumbnail Analyst", desc: "Scoring click-through & composition", delay: 6, duration: 18 },
] as const;

function SpinnerWithTimer({ label, sub }: { label: string; sub: string }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="flex items-center gap-4">
      <Loader2 className="h-4 w-4 animate-spin text-primary" />
      <div>
        <div className="text-sm font-medium">{label} ({elapsed}s)</div>
        <div className="text-xs text-muted-foreground">{sub}</div>
      </div>
    </div>
  );
}

function AnalysisProgress({ jobStatus }: { jobStatus: string | null }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(i);
  }, []);

  return (
    <Card className="p-6 md:p-10 bg-card/70 backdrop-blur-sm text-center space-y-6 md:space-y-8 max-w-3xl mx-auto border-primary/20 shadow-glow">
      <div className="space-y-2">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary relative">
          <Loader2 className="h-7 w-7 animate-spin" />
          <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-primary/30 animate-pulse" />
        </div>
        <h2 className="font-display text-xl md:text-2xl font-semibold mt-4 text-gradient">Multi-Agent Orchestration Active</h2>
        <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
          Orchestrating specialized AI personas in parallel. This takes ~30–90 seconds depending on video count.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3 text-left">
        {ANALYSIS_PHASES.map((agent) => {
          const isWaiting = elapsed < agent.delay;
          const isDone = elapsed >= (agent.delay + agent.duration);
          const isActive = !isWaiting && !isDone;

          return (
            <div
              key={agent.id}
              className={cn(
                "flex items-start gap-3 p-4 rounded-xl border transition-all duration-500 relative overflow-hidden",
                isActive && "border-primary/50 bg-primary/5 shadow-glow scale-[1.02]",
                isDone && "border-success/30 bg-success/5",
                isWaiting && "border-border/40 bg-secondary/20 opacity-50",
              )}
            >
              {isActive && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
              )}
              <span
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-lg shrink-0 transition-all duration-500",
                  isActive && "bg-primary text-primary-foreground shadow-[0_0_15px_rgba(var(--primary),0.5)]",
                  isDone && "bg-success/20 text-success",
                  isWaiting && "bg-secondary text-muted-foreground",
                )}
              >
                {isDone ? <Check className="h-4 w-4" /> : isActive ? <Loader2 className="h-4.5 w-4.5 animate-spin" /> : <Sparkle className="h-4 w-4" />}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-0.5">
                  <div className={cn("text-[11px] font-mono font-medium", isActive && "text-primary", isDone && "text-success", isWaiting && "text-muted-foreground")}>
                    {agent.id}
                  </div>
                  <div className="text-[9px] uppercase tracking-[0.1em] text-muted-foreground">
                    {isDone ? "Complete" : isActive ? "Working" : "Waiting"}
                  </div>
                </div>
                <div className={cn("text-sm font-medium", (isActive || isDone) ? "text-foreground" : "text-muted-foreground")}>
                  {agent.name}
                </div>
                <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{agent.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-2">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/50 text-[11px] text-muted-foreground font-mono">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          Engine running: {elapsed}s elapsed
        </div>
      </div>
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

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {metricCards.map((m) => (
          <Card key={m.label} className="p-4 md:p-5 bg-card/70 relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-primary" />
            <div className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">{m.label}</div>
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

      {profile.thumbnail && (
        <Card className="p-6 md:p-7 bg-card/70 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Camera className="h-4 w-4 text-primary" />
              <h3 className="font-display font-medium">Thumbnail analysis</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Score</span>
              <span className={cn(
                "font-display text-2xl font-bold tabular-nums",
                profile.thumbnail.score >= 7 ? "text-success" :
                profile.thumbnail.score >= 4 ? "text-yellow-400" : "text-destructive"
              )}>
                {profile.thumbnail.score}
              </span>
              <span className="text-xs text-muted-foreground">/10</span>
            </div>
          </div>
          <Separator />
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Composition</div>
                <p className="text-sm text-muted-foreground">{profile.thumbnail.composition}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Contrast</div>
                <p className="text-sm text-muted-foreground">{profile.thumbnail.contrast_level}</p>
              </div>
              {profile.thumbnail.facial_expression && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Expression</div>
                  <p className="text-sm text-muted-foreground">{profile.thumbnail.facial_expression}</p>
                </div>
              )}
            </div>
            <div className="space-y-3">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Dominant colors</div>
                <div className="flex flex-wrap gap-1.5">
                  {profile.thumbnail.dominant_colors.map((c) => (
                    <Badge key={c} variant="secondary" className="text-[11px]">{c}</Badge>
                  ))}
                </div>
              </div>
              {profile.thumbnail.text_readability && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Text readability</div>
                  <p className="text-sm text-muted-foreground">{profile.thumbnail.text_readability}</p>
                </div>
              )}
            </div>
          </div>
          {profile.thumbnail.suggestions.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Suggestions</div>
              <div className="space-y-1.5">
                {profile.thumbnail.suggestions.map((s, i) => (
                  <div key={i} className="flex gap-2 text-xs text-muted-foreground bg-secondary/40 rounded-lg p-3">
                    <Sparkle className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{s}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

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
        <button
          type="button"
          onClick={(e) => { 
            e.preventDefault(); 
            e.stopPropagation(); 
            console.log("[Button] clicked, calling onNext");
            onNext(); 
          }}
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium cursor-pointer bg-primary text-primary-foreground shadow hover:bg-primary/90 h-10 rounded-md px-8 min-w-[220px] shadow-glow"
          style={{ zIndex: 50, position: "relative", cursor: "pointer" }}
        >
          Generate 10 hooks
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/* ---------------- Step 2.5: Topic Select ---------------- */

function TopicSelectStep({
  topic,
  setTopic,
  onGenerate,
}: {
  topic: string;
  setTopic: (v: string) => void;
  onGenerate: (t: string) => void;
}) {
  const [localTopic, setLocalTopic] = useState(topic);

  return (
    <div className="space-y-10 max-w-2xl mx-auto">
      <header className="space-y-4 text-center">
        <Badge variant="outline" className="gap-1.5 mx-auto">
          <Target className="h-3 w-3" /> New Topic
        </Badge>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          What's your <span className="text-gradient">new topic</span>?
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          Same creator, new theme. The AI already knows the creator's formula — just
          tell it what to write about this time.
        </p>
      </header>

      <Card className="p-8 bg-card/70 backdrop-blur-sm space-y-6 text-center">
        <Textarea
          value={localTopic}
          onChange={(e) => { setLocalTopic(e.target.value); setTopic(e.target.value); }}
          placeholder="e.g. intermittent fasting benefits"
          rows={3}
          className="bg-background/60 text-lg text-center resize-none"
        />
        <Button
          size="lg"
          disabled={localTopic.trim().length < 3}
          onClick={() => onGenerate(localTopic)}
          className="min-w-[220px] shadow-glow"
        >
          Generate 10 hooks <ArrowRight className="h-4 w-4" />
        </Button>
      </Card>
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

      {loading && <SpinnerWithTimer label="Deriving hooks from the measured formula…" sub={`Fact-checking "${topic}" and injecting verified facts.`} />}

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

function CopyStep({
  hook,
  generating,
  result,
  onGenerate,
  onNewTopic,
  onRestart,
}: {
  hook: string;
  generating: boolean;
  result: CopyResult | null;
  onGenerate: () => void;
  onNewTopic: () => void;
  onRestart: () => void;
}) {
  // Parse shooting script lines into blocks
  let blocks = result?.script
    ? result.script.split("\n").filter((l) => l.includes("|"))
    : [];
  let isFallback = false;
  if (result?.script && blocks.length === 0) {
    isFallback = true;
    blocks = result.script.split("\n").filter(l => l.trim().length > 0);
  }

  if (!result) {
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
      {!generating && (
        <Card className="p-10 bg-card/70 text-center space-y-5 border-dashed">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-glow">
            <Play className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-display text-xl">Orchestrate final copy</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              The commentator writes grounded ONLY in collected evidence. No hallucination, no fluff.
            </p>
            {hook && (
              <p className="text-sm text-foreground max-w-md mx-auto pt-2">
                Hook: &ldquo;{hook}&rdquo;
              </p>
            )}
          </div>
          <Button size="lg" onClick={onGenerate} className="shadow-glow" disabled={!hook}>
            Generate script <ArrowRight className="h-4 w-4" />
          </Button>
        </Card>
      )}
      {generating && <SpinnerWithTimer label="Writing the shooting script..." sub="Injecting creator profile + verified facts into Granite 4." />}
    </div>
    );
  }

  // Result ready — styled report
  // Format clean copy as a proper script — narration on separate lines, audio cues styled
  const scriptLines = blocks.map((line) => {
    if (isFallback) {
      const text = line.trim();
      const isAudioOnly = text.toLowerCase().includes("no speech") || text.toLowerCase().includes("music only") || text.startsWith("(");
      return { text, isAudioOnly };
    }
    const parts = line.split("|").map((p) => p.trim());
    const text = parts.length >= 3 ? parts[2] : parts[parts.length - 1];
    const isAudioOnly = text.toLowerCase().includes("no speech") || text.toLowerCase().includes("music only") || text.startsWith("(");
    return { text, isAudioOnly };
  });

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Badge variant="outline" className="gap-1.5">
          <Wand2 className="h-3 w-3" /> Final Report · {result.word_count} words
        </Badge>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onRestart}>
            <RotateCcw className="h-3.5 w-3.5 mr-1" /> New creator
          </Button>
          <Button variant="outline" size="sm" onClick={onNewTopic}>
            <Wand2 className="h-3.5 w-3.5 mr-1" /> New topic
          </Button>
        </div>
      </div>

      {/* Hook banner */}
      <Card className="p-6 bg-primary/10 border-primary/30 space-y-2">
        <div className="text-xs uppercase tracking-widest text-primary font-mono">Your Hook</div>
        <p className="text-lg font-display font-semibold text-foreground leading-snug">{hook}</p>
      </Card>

      {/* Clean copy — properly formatted script */}
      <Card className="p-6 md:p-8 bg-card/70 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-display font-semibold text-lg">Complete Copy</h2>
            <span className="text-xs font-mono text-muted-foreground">{result.word_count} words</span>
          </div>
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => navigator.clipboard?.writeText(scriptLines.map(s => s.text).filter(Boolean).join("\n\n"))}>
            <CopyIcon className="h-3.5 w-3.5 mr-1" /> Copy
          </Button>
        </div>
        <Separator />
        <div className="space-y-3">
          {scriptLines.map((s, i) =>
            s.text ? (
              s.isAudioOnly ? (
                <p key={i} className="text-sm text-muted-foreground italic pl-4 border-l-2 border-primary/30">
                  {s.text.replace(/^\(|\)$/g, "")}
                </p>
              ) : (
                <p key={i} className="text-[15px] leading-[1.8] text-foreground/90">
                  {s.text}
                </p>
              )
            ) : null
          )}
        </div>
      </Card>

      {/* Shooting script blocks — with timestamps and editing */}
      <Card className="p-6 md:p-8 bg-card/70 space-y-4">
        <h2 className="font-display font-semibold text-lg flex items-center gap-2">
          <Film className="h-4 w-4 text-primary" /> Shooting Script with Directions
        </h2>
        <Separator />
        <div className="space-y-3">
        {blocks.map((line, i) => {
          if (isFallback) {
            return (
              <Card key={i} className="p-4 md:p-5 bg-card/80 border-border/40 hover:border-primary/30 transition-colors">
                <p className="text-sm leading-relaxed text-foreground/90">{line}</p>
              </Card>
            );
          }
          const parts = line.split("|").map((p) => p.trim());
          const [timestamp, shot, text, editing, why] = parts.length >= 5 ? parts : ["", line, "", "", ""];
          return (
            <Card key={i} className="p-4 md:p-5 bg-card/80 border-border/40 hover:border-primary/30 transition-colors">
              <div className="flex items-start gap-3 md:gap-4">
                {/* Left: timestamp + shot type badge */}
                <div className="shrink-0 w-16 md:w-20 text-center">
                  <div className="font-mono text-[10px] md:text-xs text-primary font-semibold">{timestamp || `#${i + 1}`}</div>
                  <div className="mt-1">
                    <span className="inline-block text-[9px] md:text-[10px] font-mono uppercase tracking-wider bg-secondary/60 text-muted-foreground rounded-full px-1.5 md:px-2 py-0.5">
                      {shot || "SHOT"}
                    </span>
                  </div>
                </div>
                {/* Center: spoken text and mobile editing directions */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm leading-relaxed text-foreground/90">{text || line}</p>
                  
                  {/* Mobile only: editing + psychology below text */}
                  {(editing || why) && (
                    <div className="md:hidden mt-3 space-y-2 border-t border-border/40 pt-3">
                      {editing && (
                        <div className="flex items-start gap-1.5">
                          <Scissors className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                          <span className="text-xs text-muted-foreground leading-tight">{editing}</span>
                        </div>
                      )}
                      {why && (
                        <div className="flex items-start gap-1.5">
                          <Zap className="h-3.5 w-3.5 text-yellow-400 mt-0.5 shrink-0" />
                          <span className="text-xs text-muted-foreground leading-tight">{why}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {/* Right: editing + psychology (Desktop) */}
                <div className="shrink-0 w-40 hidden md:block space-y-1">
                  {editing && (
                    <div className="flex items-start gap-1">
                      <Scissors className="h-3 w-3 text-primary mt-0.5 shrink-0" />
                      <span className="text-[11px] text-muted-foreground leading-tight">{editing}</span>
                    </div>
                  )}
                  {why && (
                    <div className="flex items-start gap-1">
                      <Zap className="h-3 w-3 text-yellow-400 mt-0.5 shrink-0" />
                      <span className="text-[11px] text-muted-foreground leading-tight">{why}</span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
      </Card>

      {/* Editing directions summary */}
      {result.editing_directions.length > 0 && (
        <Card className="p-6 bg-card/70 space-y-4">
          <h3 className="font-display font-semibold text-sm flex items-center gap-2">
            <Film className="h-4 w-4 text-primary" /> Editing Quick Reference
          </h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {result.editing_directions.map((d, i) => (
              <div key={i} className="flex gap-2 text-xs text-muted-foreground bg-secondary/40 rounded-lg p-3">
                <span className="font-mono text-primary shrink-0">{String(i + 1).padStart(2, "0")}</span>
                <span className="leading-relaxed">{d}</span>
              </div>
            ))}
          </div>
          {result.data_notes && (
            <div className="text-[11px] text-muted-foreground/70 italic border-t border-border/40 pt-3">
              {result.data_notes}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
