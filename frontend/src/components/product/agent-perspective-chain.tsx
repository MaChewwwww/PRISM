"use client";

import { Bot, FileCode2, Gauge, ShieldCheck, Timer } from "lucide-react";
import { useMemo, useState } from "react";

/**
 * Interactive "Autonomous Agent Perspective Chain -> Synthesis" section
 * (DESIGN.md Section 7.1 steps 2-8, Section 3.3 spectral perspectives, Section
 * 5.2 glass). Three columns: the seven canonical specialists (selectable list),
 * the selected specialist's perspective detail, and the vetted synthesis.
 *
 * The presentation contract does not expose per-specialist confidence scores or
 * signal/accuracy/recency metrics, so those are derived deterministically from
 * the specialist + story id purely as an illustrative demo surface (stable per
 * render, never network-sourced). All styling is inline per request; nothing is
 * added to globals.css.
 */

type SpecialistKey =
  | "news"
  | "quantitative"
  | "industry"
  | "fundamental"
  | "macroeconomic"
  | "technical"
  | "sentiment";

type Specialist = {
  key: SpecialistKey;
  label: string;
  color: string;
  model: string;
  prompt: string;
  summary: string;
};

// DESIGN.md Section 3.3 spectral perspective accents.
const SPECIALISTS: Specialist[] = [
  {
    key: "news",
    label: "News",
    color: "#38BDF8",
    model: "Claude 4.5 Sonnet",
    prompt: "catalyst-summary-v3",
    summary: "Headline beat with a cautious tone; sell-side recaps hedge the pop.",
  },
  {
    key: "quantitative",
    label: "Quantitative",
    color: "#22D3EE",
    model: "Claude 4.5 Sonnet",
    prompt: "vol-surface-v2",
    summary: "Realized move sits inside the implied band; edge is thin but positive.",
  },
  {
    key: "industry",
    label: "Industry",
    color: "#F59E0B",
    model: "Claude 4.5 Sonnet",
    prompt: "peer-context-v2",
    summary: "Peers drifted flat into the print; no sector-wide confirmation yet.",
  },
  {
    key: "fundamental",
    label: "Fundamental",
    color: "#A78BFA",
    model: "Claude 4.5 Sonnet",
    prompt: "quality-scan-v4",
    summary: "Guidance trim is modest; balance-sheet quality remains intact.",
  },
  {
    key: "macroeconomic",
    label: "Macroeconomic",
    color: "#F472B6",
    model: "Claude 4.5 Sonnet",
    prompt: "regime-detector",
    summary: "Rates backdrop neutral — no macro driver to amplify the move.",
  },
  {
    key: "technical",
    label: "Technical",
    color: "#60A5FA",
    model: "Claude 4.5 Sonnet",
    prompt: "level-map-v1",
    summary: "Price reclaimed the prior range high but volume confirmation is light.",
  },
  {
    key: "sentiment",
    label: "Sentiment",
    color: "#34D399",
    model: "Claude 4.5 Sonnet",
    prompt: "flow-read-v2",
    summary: "Retail chatter is upbeat while options flow leans defensive.",
  },
];

export type SynthesisDetail = {
  action: string;
  structure: string;
  notional: string;
  consensus: string;
  authority: string;
  note: string;
};

/** Deterministic pseudo-metric in [lo, hi] from a string seed (stable per render). */
function seededMetric(seed: string, lo: number, hi: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  const normalized = (Math.abs(hash) % 1000) / 1000;
  return Math.round(lo + normalized * (hi - lo));
}

function metricsFor(key: SpecialistKey, storyId: string) {
  return {
    score: seededMetric(`${storyId}:${key}:score`, 48, 88),
    signal: seededMetric(`${storyId}:${key}:signal`, 38, 72),
    accuracy: seededMetric(`${storyId}:${key}:accuracy`, 62, 92),
    recency: seededMetric(`${storyId}:${key}:recency`, 74, 98),
    tokens: seededMetric(`${storyId}:${key}:tokens`, 62, 108) / 10,
    latency: seededMetric(`${storyId}:${key}:latency`, 8, 22) / 10,
  };
}

function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[12px] text-[#94A3B8]">{label}</span>
        <span className="font-mono text-[12px] font-semibold tabular-nums text-[#CBD5E1]">
          {value}%
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/8">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

function MetaTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Bot;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-white/8 bg-white/2 p-3">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
        <Icon className="h-3 w-3" aria-hidden="true" />
        {label}
      </div>
      <p className="mt-1.5 m-0 font-mono text-[13px] text-[#CBD5E1]">{value}</p>
    </div>
  );
}

export function AgentPerspectiveChain({
  storyId,
  synthesis,
}: {
  storyId: string;
  synthesis: SynthesisDetail;
}) {
  const [activeKey, setActiveKey] = useState<SpecialistKey>("news");
  const active = SPECIALISTS.find((s) => s.key === activeKey) ?? SPECIALISTS[0];
  const metrics = useMemo(() => metricsFor(active.key, storyId), [active.key, storyId]);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.6fr)_minmax(0,1fr)]">
      {/* Column 1 — specialist list */}
      <ul className="flex flex-col gap-2" aria-label="Specialist perspectives">
        {SPECIALISTS.map((specialist) => {
          const isActive = specialist.key === active.key;
          const score = metricsFor(specialist.key, storyId).score;
          return (
            <li key={specialist.key}>
              <button
                type="button"
                onClick={() => setActiveKey(specialist.key)}
                aria-pressed={isActive}
                className="w-full rounded-xl border p-3 text-left outline-none transition-all duration-200 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                style={{
                  borderColor: isActive ? "rgba(84,125,131,0.5)" : "rgba(255,255,255,0.08)",
                  background: isActive
                    ? "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))"
                    : "rgba(255,255,255,0.02)",
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-[13px] font-semibold text-[#F8FAFC]">
                    <span
                      aria-hidden="true"
                      className="h-2 w-2 rounded-full"
                      style={{ background: specialist.color }}
                    />
                    {specialist.label}
                  </span>
                  <span className="font-mono text-[13px] font-semibold tabular-nums text-[#CBD5E1]">
                    {score}
                  </span>
                </div>
                <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-white/8">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${score}%`, background: specialist.color }}
                  />
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {/* Column 2 — selected specialist detail */}
      <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold"
            style={{
              color: active.color,
              borderColor: `${active.color}66`,
              background: `${active.color}26`,
            }}
          >
            {active.label}
          </span>
          <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Specialist · Perspective {active.label}
          </span>
        </div>

        <p className="mt-4 text-[15px] leading-snug text-[#F8FAFC]">{active.summary}</p>

        <div className="mt-5 space-y-3">
          <MetricBar label="Signal strength" value={metrics.signal} color={active.color} />
          <MetricBar label="Historical accuracy" value={metrics.accuracy} color={active.color} />
          <MetricBar label="Data recency" value={metrics.recency} color={active.color} />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <MetaTile icon={Bot} label="Model" value={active.model} />
          <MetaTile icon={FileCode2} label="Prompt" value={active.prompt} />
          <MetaTile icon={Gauge} label="Tokens" value={`${metrics.tokens.toFixed(1)}K`} />
          <MetaTile icon={Timer} label="Latency" value={`${metrics.latency.toFixed(1)}s`} />
        </div>
      </div>

      {/* Column 3 — synthesis */}
      <aside className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-[#34D399]" />
          03 · Synthesis
        </div>

        <span className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-[#547D83]/40 bg-[#547D83]/20 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#B2D8DC]">
          <ShieldCheck className="h-3 w-3" aria-hidden="true" />
          {synthesis.authority}
        </span>

        <div className="mt-4 flex items-center gap-2">
          <span className="rounded-md bg-[#00D084]/15 px-2 py-1 font-mono text-[11px] font-bold uppercase text-[#00D084]">
            {actionVerb(synthesis.action)}
          </span>
          <span className="text-[15px] font-semibold text-[#F8FAFC]">{synthesis.structure}</span>
        </div>

        <dl className="mt-4 space-y-2 border-t border-white/8 pt-4">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-[12px] text-[#94A3B8]">Notional</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#F8FAFC]">
              {synthesis.notional}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-[12px] text-[#94A3B8]">Structure</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#CBD5E1]">
              {synthesis.structure}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-[12px] text-[#94A3B8]">Consensus</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#818CF8]">
              {synthesis.consensus}
            </dd>
          </div>
        </dl>

        <p className="mt-4 border-t border-white/8 pt-4 text-[12px] leading-relaxed text-[#94A3B8]">
          {synthesis.note}
        </p>
      </aside>
    </div>
  );
}

/** Extract a short verb (BUY / SELL / HOLD / NO TRADE) from the action string. */
function actionVerb(action: string): string {
  const upper = action.toUpperCase();
  if (upper.includes("NO TRADE") || upper.includes("NO_TRADE")) return "NO TRADE";
  if (upper.includes("SELL")) return "SELL";
  if (upper.includes("HOLD")) return "HOLD";
  if (upper.includes("BUY")) return "BUY";
  return upper.split(/\s+/)[0] ?? "REVIEW";
}
