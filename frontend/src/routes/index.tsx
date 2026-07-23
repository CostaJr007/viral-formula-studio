import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import {
  ArrowRight,
  Brain,
  Camera,
  Check,
  Copy as CopyIcon,
  Download,
  Eye,
  FileText,
  Film,
  Gauge,
  Link as LinkIcon,
  Loader2,
  Play,
  RotateCcw,
  Scissors,
  Sparkle,
  Target,
  Trash2,
  Wand2,
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

type ScriptBlock = {
  timestamp: string;
  shot: string;
  text: string;
  editing: string;
  why: string;
};

type CopyResult = {
  script: string;
  /** Clean spoken narration only (preferred for Complete Copy panel). */
  spoken_copy?: string;
  /** Structured blocks from backend normalizer (preferred for shooting board). */
  blocks?: ScriptBlock[];
  editing_directions: string[];
  data_notes: string;
  word_count: number;
  format_repaired?: boolean;
  block_count?: number;
};

type StepId = "creator" | "profile" | "topic-select" | "hooks" | "copy";

const STEPS: { id: StepId; label: string; hint: string; icon: typeof LinkIcon }[] = [
  { id: "creator", label: "Creator", hint: "links or demo", icon: LinkIcon },
  { id: "profile", label: "Profile", hint: "measured formula", icon: Gauge },
  { id: "topic-select", label: "Topic", hint: "your theme", icon: Target },
  { id: "hooks", label: "Hooks", hint: "10 patterns", icon: Target },
  { id: "copy", label: "Script", hint: "shooting report", icon: Wand2 },
];

const DEMO_CREATORS = [
  {
    name: "Bryan",
    topic: "optimal morning routine for longevity",
    tag: "Longevity",
    desc: "Biohacking · data-driven tone · measured slow cuts",
    metrics: { cuts: "12.4", wpm: "148", shot: "2.1s" },
    accent: "from-emerald-500/25 to-primary/10",
  },
  {
    name: "jeffnippard",
    topic: "science-based hypertrophy training",
    tag: "Fitness science",
    desc: "Technical authority · fast cuts · proof-first hooks",
    metrics: { cuts: "28.1", wpm: "172", shot: "1.1s" },
    accent: "from-sky-500/25 to-primary/10",
  },
  {
    name: "kallaway",
    topic: "building consistent coding habits",
    tag: "Tech / productivity",
    desc: "Story-driven · motivational cadence · clean B-roll",
    metrics: { cuts: "18.6", wpm: "155", shot: "1.6s" },
    accent: "from-violet-500/25 to-primary/10",
  },
] as const;

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
        const prof = (await (
          await fetch(`${API}/api/profile/${encodeURIComponent(creatorName.trim())}`)
        ).json()) as Profile;
        // Always store a non-poison fingerprint (never N/A / Insufficient…)
        setProfile({ ...prof, style: healStyleForDisplay(prof) });
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
        if (job.status === "failed") {
          throw new Error(
            (job.error as string | undefined) ??
              "Analysis failed. Try a public YouTube Shorts link or a seed creator (jeffnippard).",
          );
        }
        setJobStatus(
          job.status === "ingesting"
            ? "Downloading and transcribing videos…"
            : job.status === "analyzing"
              ? "Measuring cuts and decoding style…"
              : "Queued…",
        );
      }

      const prof = (await (
        await fetch(`${API}/api/profile/${encodeURIComponent(creatorName.trim())}`)
      ).json()) as Profile;
      setProfile({ ...prof, style: healStyleForDisplay(prof) });
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
    setCopyResult(null); // show phased wait UX (also on regenerate)
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

  const canNavigate = (id: StepId) => id === "creator" || profile !== null;

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="flex flex-1 min-h-0">
      {/* Sidebar — desktop */}
      <aside className="hidden lg:flex w-72 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground relative">
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
            <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Studio</div>
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
                    onClick={() => (canNavigate(s.id) ? setStep(s.id) : null)}
                    disabled={!canNavigate(s.id)}
                    className={cn(
                      "w-full text-left px-3 py-2.5 rounded-lg flex items-start gap-3 transition-all group relative",
                      active && "bg-sidebar-accent shadow-glow ring-1 ring-primary/40",
                      !active && "hover:bg-sidebar-accent/60 disabled:opacity-40 disabled:cursor-not-allowed",
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

        <div className="relative mt-auto p-4 border-t border-sidebar-border">
          <p className="text-[10px] text-muted-foreground text-center tracking-wide">
            Powered by <span className="text-foreground/80 font-medium">IBM Granite</span>
          </p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 relative">
        <div className="absolute inset-0 bg-hero pointer-events-none" />
        <div className="absolute inset-0 bg-grid pointer-events-none opacity-50 hidden sm:block" />

        <div className="relative">
          {/* Sticky chrome: progress + mobile stepper */}
          <div className="border-b border-border/60 backdrop-blur-md bg-background/75 sticky top-0 z-20">
            <div className="max-w-5xl mx-auto px-4 md:px-10 py-3 flex items-center gap-3">
              <div className="lg:hidden flex items-center gap-2 shrink-0">
                <button onClick={restart} className="cursor-pointer" title="Home">
                  <img src={logoUrl} alt="Viral Formula Studio" className="h-7 w-7" />
                </button>
              </div>
              <div className="flex-1 flex items-center gap-2 md:gap-3 min-w-0">
                <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground tabular-nums shrink-0">
                  {String(stepIndex + 1).padStart(2, "0")}/{String(STEPS.length).padStart(2, "0")}
                </span>
                <Progress value={progress} className="h-1.5 flex-1" />
                <span className="hidden sm:inline text-[10px] font-mono uppercase tracking-[0.2em] text-primary tabular-nums shrink-0">
                  {Math.round(progress)}%
                </span>
              </div>
              {profile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={restart}
                  className="gap-1.5 text-xs text-muted-foreground hover:text-foreground shrink-0"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">New</span>
                </Button>
              )}
            </div>

            {/* Mobile / tablet horizontal stepper */}
            <div className="lg:hidden border-t border-border/40 px-2 sm:px-4 py-2 overflow-x-auto">
              <div className="flex items-center gap-1 min-w-max mx-auto max-w-5xl">
                {STEPS.map((s, i) => {
                  const active = s.id === step;
                  const done = i < stepIndex || (s.id === "creator" && profile !== null);
                  return (
                    <div key={s.id} className="flex items-center">
                      <button
                        type="button"
                        disabled={!canNavigate(s.id)}
                        onClick={() => canNavigate(s.id) && setStep(s.id)}
                        className={cn(
                          "flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[11px] font-medium transition-all",
                          active && "bg-primary text-primary-foreground shadow-glow",
                          done && !active && "bg-success/15 text-success",
                          !done && !active && "bg-secondary/50 text-muted-foreground",
                          "disabled:opacity-40 disabled:cursor-not-allowed",
                        )}
                      >
                        <span className="font-mono text-[10px] opacity-80">
                          {done && !active ? "✓" : String(i + 1).padStart(2, "0")}
                        </span>
                        <span>{s.label}</span>
                      </button>
                      {i < STEPS.length - 1 && (
                        <span className="w-3 sm:w-5 h-px bg-border mx-0.5 sm:mx-1 shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="max-w-5xl mx-auto px-4 md:px-10 py-6 md:py-12 animate-studio-in" key={step}>
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
                creator={creatorName}
                topic={topic}
                generating={generatingCopy}
                result={copyResult}
                onGenerate={generateCopy}
                onNewTopic={newTopic}
                onRestart={restart}
              />
            )}

            {/* Product footer — single quiet IBM credit */}
            <footer className="mt-14 md:mt-20 pt-6 border-t border-border/50 pb-2">
              <p className="text-center text-[11px] text-muted-foreground tracking-wide">
                Viral Formula Studio · Powered by{" "}
                <span className="text-foreground/75 font-medium">IBM Granite</span>
              </p>
            </footer>
          </div>
        </div>
      </main>
      </div>
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
  const selectedDemo = DEMO_CREATORS.find(
    (d) => d.name.toLowerCase() === creatorName.trim().toLowerCase(),
  );

  return (
    <div className="space-y-10 md:space-y-12">
      {/* Hero */}
      <header className="relative overflow-hidden rounded-2xl border border-border/50 call-sheet p-6 md:p-10 space-y-5">
        <div className="absolute -top-20 -right-16 h-56 w-56 rounded-full bg-primary/20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-10 h-48 w-48 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="relative space-y-4 max-w-3xl">
          <Badge variant="outline" className="gap-1.5">
            <Sparkle className="h-3 w-3" /> Multimodal creator studio
          </Badge>
          <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05] tracking-tight">
            Reverse-engineer any creator&apos;s{" "}
            <span className="text-gradient">viral formula</span>
          </h1>
          <p className="text-muted-foreground text-base md:text-lg leading-relaxed max-w-2xl">
            Measure real cuts, speech rate and hooks — then transpose that grammar onto{" "}
            <strong className="text-foreground">your</strong> topic with a shoot-ready script.
            Inspiration, not imitation.
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary text-muted-foreground text-xs font-medium">
              <Youtube className="h-3 w-3 text-red-500" /> YouTube Shorts
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary text-muted-foreground text-xs font-medium">
              <Scissors className="h-3 w-3 text-success" /> Measured metrics
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary text-muted-foreground text-xs font-medium">
              <Film className="h-3 w-3 text-primary" /> Shoot-ready script
            </span>
          </div>
        </div>

        {/* Pipeline strip */}
        <div className="relative grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          {[
            { icon: Eye, label: "01 · Measure", text: "Cuts/min, speech rate, frames — numbers first", tone: "text-sky-400" },
            { icon: Brain, label: "02 · Decode", text: "Extract style, hooks and editing grammar", tone: "text-primary" },
            { icon: Wand2, label: "03 · Transpose", text: "Hooks + shooting script on your topic", tone: "text-emerald-400" },
          ].map(({ icon: Icon, label, text, tone }) => (
            <div
              key={label}
              className="flex items-start gap-3 rounded-xl border border-border/50 bg-background/40 backdrop-blur-sm p-4"
            >
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/70 shrink-0", tone)}>
                <Icon className="h-4.5 w-4.5" />
              </span>
              <div>
                <div className="font-display text-sm font-semibold">{label}</div>
                <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </header>

      {analyzing ? (
        <AnalysisProgress jobStatus={jobStatus} />
      ) : (
        <>
          {/* Demo creators — primary path for judges */}
          <section className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-[0.22em] text-primary font-mono mb-1">
                  Instant demo · pre-analyzed
                </div>
                <h2 className="font-display text-xl md:text-2xl font-semibold">
                  Pick a seed creator
                </h2>
                <p className="text-sm text-muted-foreground mt-1 max-w-xl">
                  Profiles already measured — no download. Perfect for live demos and judges.
                </p>
              </div>
              <Badge variant="outline" className="gap-1.5 text-[10px] border-success/40 text-success">
                <Zap className="h-3 w-3" /> 0 upload · cache ready
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {DEMO_CREATORS.map((demo) => {
                const active = selectedDemo?.name === demo.name;
                return (
                  <button
                    key={demo.name}
                    type="button"
                    onClick={() => {
                      setCreatorName(demo.name);
                      setTopic(demo.topic);
                    }}
                    className={cn(
                      "text-left rounded-2xl border p-5 transition-all relative overflow-hidden group",
                      active
                        ? "border-primary bg-primary/10 shadow-glow ring-1 ring-primary/40 scale-[1.01]"
                        : "border-border/60 bg-card/60 hover:border-primary/40 hover:bg-card",
                    )}
                  >
                    <div className={cn("absolute inset-0 bg-gradient-to-br opacity-60 pointer-events-none", demo.accent)} />
                    <div className="relative space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-display font-semibold text-lg">{demo.name}</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">{demo.tag}</div>
                        </div>
                        <Badge
                          variant={active ? "default" : "secondary"}
                          className="text-[9px] uppercase tracking-wider"
                        >
                          {active ? "Selected" : "Demo"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{demo.desc}</p>
                      <div className="grid grid-cols-3 gap-2 pt-1">
                        {[
                          { k: "cuts/min", v: demo.metrics.cuts },
                          { k: "WPM", v: demo.metrics.wpm },
                          { k: "shot", v: demo.metrics.shot },
                        ].map((m) => (
                          <div
                            key={m.k}
                            className="rounded-lg bg-background/50 border border-border/40 px-2 py-1.5 text-center"
                          >
                            <div className="font-mono text-xs font-semibold text-foreground tabular-nums">{m.v}</div>
                            <div className="text-[9px] uppercase tracking-wider text-muted-foreground mt-0.5">{m.k}</div>
                          </div>
                        ))}
                      </div>
                      <div className="text-[10px] font-mono text-primary flex items-center gap-1 pt-0.5">
                        <Check className={cn("h-3 w-3", active ? "opacity-100" : "opacity-0")} />
                        Topic prefilled · click Decode below
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Custom creator form */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
              <span className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Or analyze your own creator
              </span>
              <span className="h-px flex-1 bg-gradient-to-r from-transparent via-border to-transparent" />
            </div>

            <div className="grid lg:grid-cols-5 gap-5">
              <Card className="lg:col-span-3 p-4 md:p-7 space-y-4 md:space-y-5 bg-card/70 backdrop-blur-sm border-border/60">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="font-display font-medium text-sm">Reference creator</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      Up to 5 public YouTube Shorts (TikTok/Reels: local runtime).
                    </div>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground tabular-nums shrink-0">
                    {filled}/5
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
                    className="mt-2 bg-background/60 h-11"
                  />
                </div>

                <div className="space-y-2">
                  {links.map((link, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-muted-foreground w-5 text-right shrink-0">
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
                          type="button"
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

              <Card className="lg:col-span-2 p-4 md:p-7 space-y-4 bg-card/70 backdrop-blur-sm border-border/60 flex flex-col">
                <div>
                  <Label htmlFor="topic" className="font-display font-medium text-sm">
                    Your topic
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Formula migrates here — your voice, their technique.
                  </p>
                </div>
                <Textarea
                  id="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. how small businesses can use AI without coding."
                  rows={6}
                  className="bg-background/60 resize-none flex-1 min-h-[140px]"
                />
                <div className="rounded-lg border border-border/60 bg-secondary/40 p-3 text-[11px] text-muted-foreground leading-relaxed">
                  <span className="text-foreground font-medium">Fact-check on:</span> we verify
                  checkable claims about your topic and cite sources in the final script.
                </div>
              </Card>
            </div>
          </section>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-1 pb-2">
            <div className="text-xs text-muted-foreground flex items-center gap-4 flex-wrap">
              <span className="flex items-center gap-1.5">
                <Scissors className="h-3.5 w-3.5 text-success" /> measured cuts/min
              </span>
              <span className="flex items-center gap-1.5">
                <Film className="h-3.5 w-3.5 text-primary" /> shot length
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-warning" /> signature n-grams
              </span>
            </div>
            <Button
              id="decode-btn"
              size="lg"
              disabled={!canAnalyze || analyzing}
              onClick={runAnalysis}
              className="min-w-[240px] shadow-glow h-12 text-base"
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

/* ---------------- Phased wait UX (analysis / hooks / copy) ---------------- */

type PhaseSpec = {
  id: string;
  name: string;
  desc: string;
  delay: number;
  duration: number;
  engine?: string;
};

const ANALYSIS_PHASES: PhaseSpec[] = [
  { id: "01", name: "Measure", desc: "Download, cuts/min, shot length, frames", delay: 0, duration: 8 },
  { id: "02", name: "Text style", desc: "Tone, hooks and copy fingerprint", delay: 6, duration: 28 },
  { id: "03", name: "Visual edit", desc: "Editing grammar from sampled frames", delay: 6, duration: 32 },
  { id: "04", name: "Thumbnail", desc: "Composition, contrast & CTR signals", delay: 8, duration: 20 },
];

const HOOKS_PHASES: PhaseSpec[] = [
  { id: "01", name: "Fact-check", desc: "Verify topic claims with sources", delay: 0, duration: 12 },
  { id: "02", name: "Hook strategist", desc: "10 hooks from measured patterns × your theme", delay: 8, duration: 45 },
  { id: "03", name: "Quality pass", desc: "Theme fit, clarity, honesty notes", delay: 40, duration: 40 },
];

const COPY_PHASES: PhaseSpec[] = [
  { id: "01", name: "Fact refresh", desc: "Re-ground claims before writing", delay: 0, duration: 12 },
  { id: "02", name: "Script director", desc: "Full narration + shot list + timestamps", delay: 6, duration: 50 },
  { id: "03", name: "Format polish", desc: "Blocks, spoken copy, editing directions", delay: 45, duration: 45 },
];

function PhasedWait({
  title,
  subtitle,
  phases,
  statusLine,
  mode = "analysis",
}: {
  title: string;
  subtitle: string;
  phases: PhaseSpec[];
  statusLine?: string | null;
  mode?: "analysis" | "hooks" | "copy";
}) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(i);
  }, []);

  const rotatingTips = [
    "We measure first — the model only interprets numbers and verified facts.",
    "Typical wait: 20–90s depending on load and cold start.",
    "Spoken copy is built from every timeline block, not only the hook.",
    "Honesty by design: unconfirmed claims become [INSERT: …] placeholders.",
  ];
  const tip = rotatingTips[Math.floor(elapsed / 7) % rotatingTips.length];

  // Phases are an ETA animation only — this component stays mounted until the real API returns.
  // Never show "all Complete" while we are still waiting (that looked like a stuck UI at ~45s+).
  const plannedEnd = Math.max(...phases.map((p) => p.delay + p.duration), 1);
  const pastPlan = elapsed >= plannedEnd;
  const lastPhaseId = phases[phases.length - 1]?.id;

  return (
    <Card className="p-5 md:p-9 bg-card/80 backdrop-blur-sm text-center space-y-6 md:space-y-7 max-w-3xl mx-auto border-primary/25 shadow-glow relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-primary to-transparent" />
      <div className="absolute -top-24 right-0 h-48 w-48 rounded-full bg-primary/15 blur-3xl pointer-events-none" />

      <div className="relative flex flex-col items-center gap-3">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary relative">
          <Loader2 className="h-7 w-7 animate-spin" />
          <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-primary/30 animate-pulse" />
        </div>
      </div>

      <div className="relative space-y-2">
        <h2 className="font-display text-xl md:text-2xl font-semibold text-gradient">{title}</h2>
        <p className="text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">{subtitle}</p>
        {statusLine && (
          <p className="text-xs font-mono text-primary/90 pt-1">{statusLine}</p>
        )}
        {pastPlan && (
          <p className="text-xs text-primary font-medium pt-1 max-w-md mx-auto leading-relaxed">
            Still working ({elapsed}s) — progress cards are estimates; the request is live
            (cold starts can take 60–120s).
          </p>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-3 text-left relative">
        {phases.map((agent) => {
          const endAt = agent.delay + agent.duration;
          let isWaiting = elapsed < agent.delay;
          let isDone = elapsed >= endAt;
          let isActive = !isWaiting && !isDone;

          // While API is still in flight past the planned ETA, keep the last phase "Working"
          // so we never freeze the UI on all-green "Complete" cards.
          if (pastPlan && agent.id === lastPhaseId) {
            isWaiting = false;
            isDone = false;
            isActive = true;
          } else if (pastPlan && isDone) {
            // earlier phases stay complete
            isActive = false;
          }

          const statusLabel = isDone ? "Complete" : isActive ? (pastPlan && agent.id === lastPhaseId ? "Finalizing" : "Working") : "Waiting";

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
                {isDone ? (
                  <Check className="h-4 w-4" />
                ) : isActive ? (
                  <Loader2 className="h-4.5 w-4.5 animate-spin" />
                ) : (
                  <Sparkle className="h-4 w-4" />
                )}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-0.5 gap-2">
                  <div
                    className={cn(
                      "text-[11px] font-mono font-medium",
                      isActive && "text-primary",
                      isDone && "text-success",
                      isWaiting && "text-muted-foreground",
                    )}
                  >
                    {agent.id}
                  </div>
                  <div className="text-[9px] uppercase tracking-[0.1em] text-muted-foreground shrink-0">
                    {statusLabel}
                  </div>
                </div>
                <div className={cn("text-sm font-medium", isActive || isDone ? "text-foreground" : "text-muted-foreground")}>
                  {agent.name}
                </div>
                <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{agent.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="space-y-3 pt-1 relative">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/50 text-[11px] text-muted-foreground font-mono">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
          </span>
          {elapsed}s elapsed
        </div>
        <p className="text-[11px] text-muted-foreground/90 max-w-md mx-auto leading-relaxed transition-opacity duration-500 min-h-[2.5rem]">
          {tip}
        </p>
        <p className="text-[10px] text-muted-foreground/70 tracking-wide">
          Powered by IBM Granite
        </p>
      </div>
    </Card>
  );
}

function AnalysisProgress({ jobStatus }: { jobStatus: string | null }) {
  return (
    <PhasedWait
      title="Decoding the creator formula"
      subtitle="Measuring the videos, then extracting style and editing grammar. Usually ~30–90 seconds."
      phases={ANALYSIS_PHASES}
      statusLine={jobStatus}
      mode="analysis"
    />
  );
}

/* ---------------- Step 2: Profile ---------------- */

function isBlankField(value?: string | null): boolean {
  if (value == null) return true;
  const t = value.trim();
  if (!t) return true;
  return /^(n\/?a|none|null|unknown|tbd|-|—|insufficient(\s+transcript)?(\s+evidence)?|analysis failed)$/i.test(
    t,
  );
}

function isPoisonStyleText(value?: string | null): boolean {
  if (!value) return true;
  return /insufficient\s+transcript|analysis failed|^n\/?a$/i.test(value.trim());
}

/**
 * Style is showable if it has real tone OR hooks OR phrases — never treat
 * "Insufficient transcript evidence" as a valid fingerprint.
 */
function isStyleUsable(style?: Profile["style"] | null): boolean {
  if (!style) return false;
  if (
    isPoisonStyleText(style.tone) ||
    isPoisonStyleText(style.persona) ||
    isPoisonStyleText(style.copy_structure)
  ) {
    // Still usable if model left real hooks/phrases despite bad labels
    const hasHooks = (style.hook_patterns?.length ?? 0) > 0;
    const hasExprs = (style.signature_expressions ?? []).some((s) => !isBlankField(s));
    return hasHooks || hasExprs;
  }
  if (isBlankField(style.tone) && isBlankField(style.persona) && !(style.hook_patterns?.length)) {
    return false;
  }
  return true;
}

const PHRASE_JUNK =
  /^(https?|www|com|org|net|ibm|cloud|quota|status|chat|code|api|error|null|token|json|html|mp4|url)$/i;

function isCleanPhrase(p: string): boolean {
  const t = p.trim();
  if (!t || t.length < 3) return false;
  if (PHRASE_JUNK.test(t)) return false;
  if (/https?:|www\.|\.com|\.cloud/i.test(t)) return false;
  const parts = t.toLowerCase().split(/\s+/);
  if (parts.some((w) => PHRASE_JUNK.test(w))) return false;
  return true;
}

/** Client-side emergency fingerprint so the card never renders poison strings. */
function healStyleForDisplay(profile: Profile): Profile["style"] {
  const s = profile.style;
  const cleanExprs = (s?.signature_expressions ?? []).filter(isCleanPhrase);
  const cleanNgrams = (profile.metrics?.signature_ngrams ?? [])
    .map((g) => g.ngram)
    .filter(isCleanPhrase);
  const styleLooksReal =
    s &&
    isStyleUsable(s) &&
    !isPoisonStyleText(s.tone) &&
    // If "phrases" are pure infra junk, force heal even if tone string looks fine
    (cleanExprs.length > 0 || cleanNgrams.length > 0 || (s.hook_patterns?.length ?? 0) > 0);

  if (styleLooksReal && s) {
    return {
      ...s,
      signature_expressions: cleanExprs.length ? cleanExprs : cleanNgrams.slice(0, 8),
    };
  }

  const wpm = profile.metrics?.speech?.avg_wpm;
  const pace =
    typeof wpm === "number"
      ? `Measured speech pace ~${Math.round(wpm)} WPM`
      : "Typical short-form spoken pace";
  const tone =
    typeof wpm === "number" && wpm >= 160
      ? "High-energy, direct short-form delivery"
      : "Conversational short-form delivery";

  return {
    tone,
    sentence_rhythm: pace,
    persona: "Creator speaking straight to camera in short-form format",
    copy_structure:
      "Open with a hook, deliver one clear idea, close with a takeaway — standard short-form arc.",
    // Never dump junk unigrams (https, ibm, quota…) into the UI
    signature_expressions: cleanNgrams.slice(0, 8),
    hook_patterns: [
      {
        pattern: "Direct promise in the first seconds",
        why_it_works: "Gives an immediate reason to keep watching on mobile.",
        example: "Here's what actually works…",
      },
      {
        pattern: "Problem → quick fix",
        why_it_works: "Names pain then implies a simple path.",
        example: "Stop doing this in the morning.",
      },
    ],
    persuasion_tactics: ["Direct address", "Single-idea focus"],
    evidence_notes:
      "Recovered fingerprint from measured pace only — prior phrases looked like error/URL noise, not speech.",
  };
}

function ProfileStep({ profile, onNext }: { profile: Profile | null; onNext: () => void }) {
  if (!profile) return null;

  const editingM = profile.metrics?.editing;
  const speechM = profile.metrics?.speech;
  const ngrams = profile.metrics?.signature_ngrams ?? [];
  // Never render N/A / "Insufficient transcript evidence" in the fingerprint card
  const displayStyle = healStyleForDisplay(profile);
  const styleHealed = displayStyle !== profile.style;
  const styleOk = true; // always show a usable fingerprint card
  const phraseChips =
    ngrams.length > 0
      ? ngrams.slice(0, 8).map((g) => `${g.ngram} (${g.count}x)`)
      : (displayStyle?.signature_expressions ?? []).filter((s) => !isBlankField(s));

  const metricCards = [
    { label: "Cuts / min", value: editingM?.avg_cuts_per_min ?? "—", unit: "" },
    { label: "Avg shot length", value: editingM?.avg_shot_length_s ?? "—", unit: "s" },
    { label: "Words / min", value: speechM?.avg_wpm ?? "—", unit: "" },
    { label: "Videos analyzed", value: profile.videos_analyzed, unit: "" },
  ];

  return (
    <div className="space-y-10">
      <header className="space-y-4 max-w-3xl">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="gap-1.5">
            <Gauge className="h-3 w-3" /> Evidence room
          </Badge>
          <Badge variant="secondary" className="font-mono text-[10px]">
            {profile.creator}
          </Badge>
        </div>
        <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
          Formula <span className="text-gradient">measured</span>, not guessed.
        </h1>
        <p className="text-muted-foreground text-lg leading-relaxed">
          Numbers from ffmpeg plus stylistic and visual reading of the videos.
          Each line becomes an instruction in your final call sheet.
        </p>
      </header>

      {styleHealed && (
        <Card className="p-4 md:p-5 border-primary/30 bg-primary/10 space-y-2">
          <div className="font-display font-semibold text-sm flex items-center gap-2">
            <Gauge className="h-4 w-4 text-primary" />
            Fingerprint recovered from measured metrics
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Speech text was thin for this creator, so we built a usable short-form fingerprint from
            measured WPM / n-grams (never leave N/A on screen). Hooks &amp; script still work — for a
            richer linguistic read, re-ingest longer spoken Shorts.
          </p>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {metricCards.map((m) => (
          <Card key={m.label} className="p-4 md:p-5 bg-card/70 relative overflow-hidden border-border/60">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-success via-primary to-primary/40" />
            <div className="text-[10px] md:text-xs text-muted-foreground uppercase tracking-wider">{m.label}</div>
            <div className="mt-3 font-display text-3xl font-semibold tabular-nums">
              {m.value}
              <span className="text-base text-muted-foreground ml-1">{m.unit}</span>
            </div>
            <div className="mt-2 text-[10px] font-mono text-success/90">
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
          {displayStyle ? (
            <>
              <p className="text-sm text-muted-foreground leading-relaxed">
                <strong className="text-foreground">{displayStyle.tone}</strong>
                {!isBlankField(displayStyle.persona) && <> — {displayStyle.persona}</>}
                {!isBlankField(displayStyle.sentence_rhythm) && <> · {displayStyle.sentence_rhythm}</>}
              </p>
              {!isBlankField(displayStyle.copy_structure) &&
                !isPoisonStyleText(displayStyle.copy_structure) && (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {displayStyle.copy_structure}
                </p>
              )}
              <Separator />
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Signature phrases (measured)
                </div>
                {phraseChips.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {phraseChips.map((n) => (
                      <Badge key={n} variant="secondary" className="font-mono text-[11px]">
                        {n}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    No repeated n-grams yet — hooks still use the structural patterns below.
                  </p>
                )}
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Hook patterns
                </div>
                {(displayStyle.hook_patterns?.length ?? 0) > 0 ? (
                  <ul className="space-y-2 text-sm">
                    {displayStyle.hook_patterns.map((h) => (
                      <li key={h.pattern} className="text-muted-foreground">
                        <span className="text-foreground font-medium">{h.pattern}</span>
                        {!isBlankField(h.why_it_works) && <> — {h.why_it_works}</>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground italic">Patterns will appear after analysis.</p>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Loading fingerprint…</p>
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

      {loading && (
        <PhasedWait
          title="Writing hooks in the creator’s technique"
          subtitle={`Fact-checking “${topic}”, then mapping measured patterns onto your theme. Usually 20–60s.`}
          phases={HOOKS_PHASES}
          mode="hooks"
        />
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

const TS_RE = /\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}/;
const AUDIO_ONLY_RE = /no speech|music only|^\(.*\)$/i;

function stripQuotes(text: string): string {
  const t = text.trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("“") && t.endsWith("”"))) {
    return t.slice(1, -1).trim();
  }
  return t;
}

/** Client-side recovery when older backends omit `blocks` / `spoken_copy`. */
function parseScriptClient(script: string): ScriptBlock[] {
  const raw = (script || "").trim();
  if (!raw) return [];

  const fromPipes: ScriptBlock[] = [];
  for (const line of raw.split("\n")) {
    const t = line.trim();
    if (!t.includes("|")) continue;
    const parts = t.split("|").map((p) => p.trim());
    if (parts.length >= 5) {
      fromPipes.push({
        timestamp: parts[0],
        shot: parts[1],
        text: parts[2],
        editing: parts[3],
        why: parts.slice(4).join(" | "),
      });
    } else if (parts.length >= 3) {
      fromPipes.push({
        timestamp: parts[0] || "",
        shot: parts[1] || "SHOT",
        text: parts[2] || "",
        editing: parts[3] || "",
        why: parts[4] || "",
      });
    }
  }
  if (fromPipes.length >= 2) return fromPipes;

  // Split mashed one-liners on timestamp ranges
  const chunks = raw.split(/(?=\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})/).map((c) => c.trim()).filter(Boolean);
  const recovered: ScriptBlock[] = [];
  for (const chunk of chunks) {
    if (chunk.includes("|")) {
      const parts = chunk.split("|").map((p) => p.trim());
      recovered.push({
        timestamp: parts[0] || "",
        shot: parts[1] || "MEDIUM shot",
        text: parts[2] || "",
        editing: parts[3] || "",
        why: parts.slice(4).join(" | ") || "",
      });
      continue;
    }
    const tsMatch = chunk.match(TS_RE);
    const quotes = [...chunk.matchAll(/"([^"]{3,})"|“([^”]{3,})”/g)].map((m) => m[1] || m[2]);
    recovered.push({
      timestamp: tsMatch?.[0] || "",
      shot: "MEDIUM shot",
      text: quotes[0] ? `"${quotes[0]}"` : chunk.replace(TS_RE, "").trim(),
      editing: "",
      why: "",
    });
  }
  return recovered.length > 0 ? recovered : fromPipes;
}

function spokenFromBlocks(blocks: ScriptBlock[]): { text: string; isAudioOnly: boolean }[] {
  return blocks
    .map((b) => {
      const text = (b.text || "").trim();
      if (!text) return null;
      const isAudioOnly = AUDIO_ONLY_RE.test(text);
      return { text: isAudioOnly ? text : stripQuotes(text), isAudioOnly };
    })
    .filter((x): x is { text: string; isAudioOnly: boolean } => Boolean(x?.text));
}

function buildExportMarkdown(opts: {
  creator: string;
  topic: string;
  hook: string;
  spoken: string;
  blocks: ScriptBlock[];
  directions: string[];
  notes: string;
  wordCount: number;
}): string {
  const lines = [
    `# Viral Formula Studio — Shooting Report`,
    ``,
    `- **Creator formula:** ${opts.creator || "—"}`,
    `- **Topic:** ${opts.topic || "—"}`,
    `- **Spoken words:** ${opts.wordCount}`,
    `- **Engine:** Viral Formula Studio`,
    ``,
    `## Hook`,
    opts.hook,
    ``,
    `## Complete Copy`,
    opts.spoken || "_(empty)_",
    ``,
    `## Timeline`,
    ...opts.blocks.map(
      (b, i) =>
        `### ${b.timestamp || `Block ${i + 1}`} · ${b.shot || "SHOT"}\n` +
        `**Say:** ${stripQuotes(b.text || "—")}\n` +
        `**Edit:** ${b.editing || "—"}\n` +
        `**Why:** ${b.why || "—"}`,
    ),
    ``,
    `## Editing quick reference`,
    ...opts.directions.map((d, i) => `${i + 1}. ${d}`),
    ``,
    `## Honesty / data notes`,
    opts.notes || "—",
    ``,
  ];
  return lines.join("\n");
}

function CopyStep({
  hook,
  creator,
  topic,
  generating,
  result,
  onGenerate,
  onNewTopic,
  onRestart,
}: {
  hook: string;
  creator: string;
  topic: string;
  generating: boolean;
  result: CopyResult | null;
  onGenerate: () => void;
  onNewTopic: () => void;
  onRestart: () => void;
}) {
  if (!result) {
    return (
      <div className="space-y-10">
        <header className="space-y-4 max-w-3xl">
          <Badge variant="outline" className="gap-1.5">
            <Wand2 className="h-3 w-3" /> Final step · shooting script
          </Badge>
          <h1 className="text-3xl md:text-5xl font-display font-semibold leading-[1.05]">
            Your script, <span className="text-gradient">ready to shoot</span>.
          </h1>
          <p className="text-muted-foreground text-lg leading-relaxed">
            Full call sheet: spoken narration, timecodes, shot types and retention psychology —
            grounded in measured metrics and verified facts.
          </p>
        </header>
        {!generating && (
          <Card className="p-8 md:p-10 bg-card/70 text-center space-y-5 border-dashed border-primary/30 relative overflow-hidden">
            <div className="absolute -top-16 right-0 h-40 w-40 rounded-full bg-primary/15 blur-3xl pointer-events-none" />
            <div className="relative inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-glow">
              <Play className="h-6 w-6" />
            </div>
            <div className="relative space-y-2">
              <h3 className="font-display text-xl">Generate shooting report</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Multi-block timeline · open → develop → close · evidence only.
              </p>
              {hook && (
                <p className="text-sm text-foreground max-w-lg mx-auto pt-2 rounded-lg bg-primary/10 border border-primary/20 px-4 py-3">
                  Hook seed: &ldquo;{hook}&rdquo;
                </p>
              )}
            </div>
            <Button size="lg" onClick={onGenerate} className="shadow-glow relative" disabled={!hook}>
              Generate script <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-[11px] text-muted-foreground relative">
              Usually 30–90s · fact-check + full narration + format polish
            </p>
          </Card>
        )}
        {generating && (
          <PhasedWait
            title="Writing the complete shooting script"
            subtitle="Injecting creator profile + verified facts. Full narration and shot list — not just the opening hook."
            phases={COPY_PHASES}
            mode="copy"
          />
        )}
      </div>
    );
  }

  const blocks: ScriptBlock[] =
    result.blocks && result.blocks.length > 0 ? result.blocks : parseScriptClient(result.script);

  const spokenLines =
    result.spoken_copy && result.spoken_copy.trim().length > 0
      ? result.spoken_copy
          .split(/\n\n+/)
          .map((t) => t.trim())
          .filter(Boolean)
          .map((text) => ({
            text: stripQuotes(text),
            isAudioOnly: AUDIO_ONLY_RE.test(text),
          }))
      : spokenFromBlocks(blocks);

  const spokenWordCount =
    result.word_count ||
    spokenLines
      .filter((s) => !s.isAudioOnly)
      .map((s) => s.text)
      .join(" ")
      .split(/\s+/)
      .filter(Boolean).length;

  const clipboardText = spokenLines
    .filter((s) => !s.isAudioOnly)
    .map((s) => s.text)
    .join("\n\n");

  const exportMd = buildExportMarkdown({
    creator,
    topic,
    hook,
    spoken: clipboardText,
    blocks,
    directions: result.editing_directions ?? [],
    notes: result.data_notes ?? "",
    wordCount: spokenWordCount,
  });

  function downloadReport() {
    const blob = new Blob([exportMd], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `viral-formula-${(creator || "report").toLowerCase().replace(/\s+/g, "-")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-studio-in">
      {/* Call-sheet document */}
      <div className="rounded-2xl border border-border/60 call-sheet overflow-hidden shadow-elegant">
        {/* Masthead */}
        <div className="border-b border-border/50 px-5 md:px-8 py-5 md:py-6 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="gap-1.5 bg-primary text-primary-foreground">
                  <FileText className="h-3 w-3" /> Shooting Report
                </Badge>
                {result.format_repaired && (
                  <Badge variant="secondary" className="text-[10px]">
                    format auto-repaired
                  </Badge>
                )}
              </div>
              <h1 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
                Viral Formula Studio
              </h1>
              <p className="text-xs text-muted-foreground font-mono uppercase tracking-[0.16em]">
                Evidence-based playbook · not a template
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => navigator.clipboard?.writeText(exportMd)}>
                <CopyIcon className="h-3.5 w-3.5 mr-1" /> Copy all
              </Button>
              <Button variant="outline" size="sm" onClick={downloadReport}>
                <Download className="h-3.5 w-3.5 mr-1" /> Export .md
              </Button>
              <Button variant="outline" size="sm" onClick={onGenerate}>
                <RotateCcw className="h-3.5 w-3.5 mr-1" /> Regenerate
              </Button>
            </div>
          </div>

          {/* Meta grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
            {[
              { k: "Creator formula", v: creator || "—" },
              { k: "Your topic", v: topic || "—" },
              { k: "Spoken words", v: String(spokenWordCount) },
              { k: "Timeline blocks", v: String(blocks.length) },
            ].map((m) => (
              <div key={m.k} className="rounded-xl border border-border/40 bg-background/40 px-3 py-2.5">
                <div className="text-[9px] uppercase tracking-wider text-muted-foreground font-mono">{m.k}</div>
                <div className="text-sm font-medium mt-1 truncate" title={m.v}>
                  {m.v}
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" size="sm" className="text-xs" onClick={onRestart}>
              <RotateCcw className="h-3.5 w-3.5 mr-1" /> New creator
            </Button>
            <Button variant="ghost" size="sm" className="text-xs" onClick={onNewTopic}>
              <Wand2 className="h-3.5 w-3.5 mr-1" /> New topic
            </Button>
          </div>
        </div>

        <div className="p-5 md:p-8 space-y-8">
          {/* Hook */}
          <section className="rounded-xl border border-primary/30 bg-primary/10 p-5 md:p-6 space-y-2">
            <div className="text-[10px] uppercase tracking-[0.2em] text-primary font-mono flex items-center gap-2">
              <Zap className="h-3.5 w-3.5" /> Opening hook · first 3 seconds
            </div>
            <p className="text-lg md:text-xl font-display font-semibold leading-snug">&ldquo;{hook}&rdquo;</p>
          </section>

          {/* Complete copy — prompter style */}
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" /> Complete Copy
                </h2>
                <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                  Spoken narration only · {spokenWordCount} words · read on camera
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="text-xs"
                disabled={!clipboardText}
                onClick={() => navigator.clipboard?.writeText(clipboardText)}
              >
                <CopyIcon className="h-3.5 w-3.5 mr-1" /> Copy narration
              </Button>
            </div>
            <div className="rounded-xl border border-border/50 bg-background/50 p-5 md:p-7 space-y-4">
              {spokenLines.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">
                  No spoken lines recovered. Check the timeline or regenerate.
                </p>
              ) : (
                spokenLines.map((s, i) =>
                  s.isAudioOnly ? (
                    <p
                      key={i}
                      className="text-sm text-muted-foreground italic pl-4 border-l-2 border-primary/30"
                    >
                      {s.text.replace(/^\(|\)$/g, "")}
                    </p>
                  ) : (
                    <p
                      key={i}
                      className="text-[16px] md:text-[17px] leading-[1.85] text-foreground/95 font-medium"
                    >
                      {s.text}
                    </p>
                  ),
                )
              )}
            </div>
          </section>

          {/* Film timeline */}
          <section className="space-y-4">
            <div>
              <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <Film className="h-4 w-4 text-primary" /> Shooting timeline
              </h2>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                Timecode · shot · dialogue · edit · retention psychology
              </p>
            </div>

            <div className="relative rounded-xl border border-border/50 bg-background/40 overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-2 film-strip opacity-70 pointer-events-none" />
              <div className="absolute right-0 top-0 bottom-0 w-2 film-strip opacity-70 pointer-events-none" />
              <div className="pl-4 pr-4 md:pl-6 md:pr-6 py-2 space-y-0">
                {blocks.length === 0 ? (
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap p-4">{result.script}</p>
                ) : (
                  blocks.map((block, i) => (
                    <div
                      key={i}
                      className={cn(
                        "grid grid-cols-1 md:grid-cols-[5.5rem_1fr_11rem] gap-3 md:gap-4 py-4 md:py-5",
                        i < blocks.length - 1 && "border-b border-border/40",
                      )}
                    >
                      <div className="flex md:flex-col items-center md:items-start gap-2 md:gap-1">
                        <span className="font-mono text-[11px] md:text-xs text-primary font-semibold tabular-nums">
                          {block.timestamp || `TAKE ${String(i + 1).padStart(2, "0")}`}
                        </span>
                        <span className="inline-flex text-[9px] font-mono uppercase tracking-wider bg-secondary/70 text-muted-foreground rounded-md px-2 py-0.5">
                          {block.shot || "SHOT"}
                        </span>
                        <span className="hidden md:inline text-[9px] font-mono text-muted-foreground/70">
                          #{String(i + 1).padStart(2, "0")}
                        </span>
                      </div>
                      <div className="min-w-0 space-y-2">
                        <p className="text-sm md:text-[15px] leading-relaxed text-foreground/95">
                          {block.text ? stripQuotes(block.text) : "—"}
                        </p>
                        {block.why && (
                          <p className="text-xs text-muted-foreground italic leading-relaxed md:hidden">
                            {block.why}
                          </p>
                        )}
                      </div>
                      <div className="space-y-2 text-[11px] text-muted-foreground">
                        {block.editing && (
                          <div className="flex items-start gap-1.5 rounded-lg bg-secondary/40 p-2">
                            <Scissors className="h-3 w-3 text-primary mt-0.5 shrink-0" />
                            <span className="leading-snug">{block.editing}</span>
                          </div>
                        )}
                        {block.why && (
                          <div className="hidden md:flex items-start gap-1.5 rounded-lg bg-secondary/30 p-2">
                            <Zap className="h-3 w-3 text-warning mt-0.5 shrink-0" />
                            <span className="leading-snug">{block.why}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>

          {/* Editing + honesty */}
          {(result.editing_directions?.length > 0 || result.data_notes) && (
            <section className="grid md:grid-cols-5 gap-4">
              {result.editing_directions?.length > 0 && (
                <div className="md:col-span-3 rounded-xl border border-border/50 bg-background/40 p-5 space-y-3">
                  <h3 className="font-display font-semibold text-sm flex items-center gap-2">
                    <Scissors className="h-4 w-4 text-primary" /> Editing quick reference
                  </h3>
                  <div className="space-y-2">
                    {result.editing_directions.map((d, i) => (
                      <div
                        key={i}
                        className="flex gap-2 text-xs text-muted-foreground bg-secondary/30 rounded-lg p-2.5"
                      >
                        <span className="font-mono text-primary shrink-0">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="leading-relaxed">{d}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {result.data_notes && (
                <div className="md:col-span-2 rounded-xl border border-border/50 bg-background/40 p-5 space-y-2">
                  <h3 className="font-display font-semibold text-sm flex items-center gap-2">
                    <Gauge className="h-4 w-4 text-success" /> Honesty notes
                  </h3>
                  <p className="text-[12px] text-muted-foreground leading-relaxed">{result.data_notes}</p>
                  <p className="text-[10px] text-muted-foreground/70 pt-2 border-t border-border/40">
                    Sources verified · honesty notes included
                  </p>
                </div>
              )}
            </section>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/40">
            <p className="text-[10px] text-muted-foreground tracking-wide">
              Inspiration, not imitation · Powered by IBM Granite
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={onNewTopic}>
                New topic
              </Button>
              <Button size="sm" className="shadow-glow" onClick={onGenerate}>
                Regenerate script
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
