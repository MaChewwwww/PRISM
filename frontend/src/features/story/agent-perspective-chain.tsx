"use client";

import {
  Activity,
  BarChart3,
  Building2,
  Factory,
  Globe,
  Newspaper,
  Scale,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

/**
 * Interactive "Autonomous Agent Perspective Chain -> Synthesis" section
 * (DESIGN.md Section 7.1 steps 2-8, Section 3.3 spectral perspectives, Section
 * 5.2 glass). Three columns: the seven canonical specialists (selectable list),
 * the selected specialist's perspective detail, and the vetted synthesis.
 *
 * The presentation contract does not expose per-specialist invocation metrics.
 * This fixture therefore displays provenance explicitly and never manufactures
 * confidence, accuracy, recency, token, latency, model, or prompt values.
 */

type AgentKey =
  | "news"
  | "quantitative"
  | "industry"
  | "fundamental"
  | "macroeconomic"
  | "market_reaction"
  | "trading_decision";

type Agent = {
  key: AgentKey;
  label: string;
  icon: LucideIcon;
  color: string;
  /** The agent's recorded decision headline shown in the detail column. */
  headline: string;
  /** Supporting description for the decision. */
  description: string;
};

const ILLUSTRATIVE_NOTE =
  "Illustrative structured output; no model provider was contacted for this fixture.";

// Roster and spectral accents follow DESIGN.md Section 3.3.
const AGENTS: Agent[] = [
  {
    key: "news",
    label: "News Agent",
    icon: Newspaper,
    color: "#38BDF8",
    headline: "Catalyst evidence",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "quantitative",
    label: "Quantitative Agent",
    icon: BarChart3,
    color: "#22D3EE",
    headline: "Market and option statistics",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "industry",
    label: "Industry Agent",
    icon: Factory,
    color: "#F59E0B",
    headline: "Sector and peer context",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "fundamental",
    label: "Fundamental Agent",
    icon: Building2,
    color: "#A78BFA",
    headline: "Company fundamentals",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "macroeconomic",
    label: "Macroeconomic Agent",
    icon: Globe,
    color: "#F472B6",
    headline: "Macro regime evidence",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "market_reaction",
    label: "Market Reaction/Mispricing Agent",
    icon: Activity,
    color: "#10B981",
    headline: "Reaction-gap synthesis",
    description: ILLUSTRATIVE_NOTE,
  },
  {
    key: "trading_decision",
    label: "Trading Decision Agent",
    icon: Scale,
    color: "#34D399",
    headline: "Proposal or NO_TRADE",
    description: ILLUSTRATIVE_NOTE,
  },
];

export type SynthesisDetail = {
  action: string;
  structure: string;
  notional: string;
  consensus: string;
  note: string;
};

export function AgentPerspectiveChain({
  storyId,
  synthesis,
}: {
  storyId: string;
  synthesis: SynthesisDetail;
}) {
  const [activeKey, setActiveKey] = useState<AgentKey>("news");
  const active = AGENTS.find((agent) => agent.key === activeKey) ?? AGENTS[0];
  void storyId;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.6fr)_minmax(0,1fr)] lg:items-stretch">
      {/* Column 1 — one card per agent so all seven choices read as distinct */}
      <ul className="flex flex-col gap-2" aria-label="Agent perspectives">
        {AGENTS.map((agent) => {
          const isActive = agent.key === active.key;
          const Icon = agent.icon;
          return (
            <li key={agent.key} className="flex-1">
              <button
                type="button"
                onClick={() => setActiveKey(agent.key)}
                aria-pressed={isActive}
                className="flex h-full w-full items-center gap-2.5 rounded-xl border border-t-white/16 px-3.5 py-3 text-left backdrop-blur-xl transition-all duration-200 outline-none hover:-translate-y-px hover:!border-[#547D83]/40 hover:!shadow-[0_0_24px_rgba(84,125,131,0.35)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                style={{
                  borderColor: isActive ? "rgba(84,125,131,0.5)" : "rgba(255,255,255,0.08)",
                  background: isActive
                    ? "linear-gradient(180deg, rgba(84,125,131,0.18), rgba(84,125,131,0.06))"
                    : "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                  boxShadow: isActive
                    ? "0 12px 40px -8px rgba(84,125,131,0.25)"
                    : "0 8px 32px 0 rgba(0,0,0,0.37)",
                }}
              >
                <Icon
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0"
                  style={{ color: agent.color }}
                />
                <span
                  className="text-[13px] font-semibold"
                  style={{ color: isActive ? "#F8FAFC" : "#CBD5E1" }}
                >
                  {agent.label}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {/* Column 2 — selected agent decision */}
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
            Agent decision
          </span>
        </div>

        <h3 className="mt-4 text-[17px] font-semibold leading-snug text-[#F8FAFC]">
          {active.headline}
        </h3>
        <p className="mt-1.5 text-[13px] leading-relaxed text-[#94A3B8]">{active.description}</p>

        <div className="mt-5 rounded-md border border-white/8 bg-white/2 p-3 text-[12px] leading-relaxed text-[#94A3B8]">
          Invocation metrics and provider metadata were not recorded for this illustrative fixture.
          They will appear only when emitted by the backend.
        </div>
      </div>

      {/* Column 3 — synthesis: the single candidate action the agents converge on */}
      <aside className="rounded-xl border border-[#34D399]/25 border-t-[#34D399]/40 bg-linear-to-b from-[#34D399]/8 to-white/2 p-5 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#34D399]/30 bg-[#34D399]/15 text-[#34D399]"
          >
            <Sparkles className="h-3.5 w-3.5" />
          </span>
          <div>
            <p className="text-[13px] font-semibold text-[#F8FAFC]">Synthesis</p>
            <p className="text-[11px] text-[#94A3B8]">Overall decision</p>
          </div>
        </div>

        <div className="mt-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
            Candidate action
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="rounded-md bg-[#00D084]/15 px-2 py-1 font-mono text-[11px] font-bold uppercase text-[#00D084]">
              {actionVerb(synthesis.action)}
            </span>
            <span className="text-[15px] font-semibold text-[#F8FAFC]">{synthesis.structure}</span>
          </div>
        </div>

        <dl className="mt-4 space-y-2 border-t border-white/8 pt-4">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-[12px] text-[#94A3B8]">Notional</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#F8FAFC]">
              {synthesis.notional}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-[12px] text-[#94A3B8]">Agent agreement</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#818CF8]">
              {synthesis.consensus}
            </dd>
          </div>
        </dl>

        <p className="mt-4 border-t border-white/8 pt-4 text-[12px] leading-relaxed text-[#94A3B8]">
          <span className="font-semibold text-[#CBD5E1]">Why: </span>
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
