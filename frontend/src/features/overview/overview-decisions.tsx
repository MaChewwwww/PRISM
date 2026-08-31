"use client";

import { AlertTriangle, ArrowRight, ArrowUpRight, CircleDot, Diamond } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { OverviewDecision } from "@/features/overview/overview-adapter";

/**
 * Agent perspective chips mirror the Decision Stories feed (story-list.tsx) so
 * the Overview "Recent decisions" cards share the same look and mood: DESIGN.md
 * Section 6.3 chip variants keyed to the prismatic spectral tokens (Section
 * 3.3). Which perspective shows is derived from the recorded rule-gate result.
 */
type AgentKind = "research" | "proposal" | "risk" | "gate";

type AgentTag = {
  kind: AgentKind;
  label: string;
  icon: LucideIcon;
  chipClass: string;
};

const AGENT_TAGS: Record<AgentKind, AgentTag> = {
  research: {
    kind: "research",
    label: "Research",
    icon: Diamond,
    chipClass: "bg-[#38BDF8]/15 text-[#38BDF8] border-[#38BDF8]/30",
  },
  proposal: {
    kind: "proposal",
    label: "Proposal",
    icon: Diamond,
    chipClass: "bg-[#10B981]/15 text-[#10B981] border-[#10B981]/30",
  },
  risk: {
    kind: "risk",
    label: "Risk",
    icon: AlertTriangle,
    chipClass: "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30",
  },
  gate: {
    kind: "gate",
    label: "Gate",
    icon: CircleDot,
    chipClass: "bg-[#547D83]/20 text-[#B2D8DC] border-[#547D83]/40",
  },
};

const OUTCOME_LABEL: Record<OverviewDecision["ruleResult"], string> = {
  PASS: "Pass",
  MODIFY: "Modify",
  FAIL: "No trade",
  NOT_EVALUATED: "No trade",
};

function agentKindFor(ruleResult: OverviewDecision["ruleResult"]): AgentKind {
  switch (ruleResult) {
    case "PASS":
      return "proposal";
    case "MODIFY":
      return "gate";
    case "FAIL":
      return "risk";
    case "NOT_EVALUATED":
    default:
      return "research";
  }
}

function formatResult(value: number) {
  if (value === 0) return "$0";
  return `${value > 0 ? "+" : "-"}$${Math.abs(Math.round(value)).toLocaleString()}`;
}

function resultColor(value: number) {
  if (value > 0) return "text-[#00D084]";
  if (value < 0) return "text-[#FF6B6B]";
  return "text-[#64748B]";
}

function AgentChip({ tag }: { tag: AgentTag }) {
  const Icon = tag.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-semibold ${tag.chipClass}`}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5" strokeWidth={2.5} />
      {tag.label}
    </span>
  );
}

function DecisionCard({ decision }: { decision: OverviewDecision }) {
  const [active, setActive] = useState(false);
  const tag = AGENT_TAGS[agentKindFor(decision.ruleResult)];
  const outcomeLabel = OUTCOME_LABEL[decision.ruleResult];

  return (
    <Link
      href={`/stories/${decision.storyId}`}
      onMouseEnter={() => setActive(true)}
      onMouseLeave={() => setActive(false)}
      onFocus={() => setActive(true)}
      onBlur={() => setActive(false)}
      className={`group flex flex-col gap-3 rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 outline-none backdrop-blur-xl transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:border-t-[#B2D8DC]/50 hover:from-white/8 hover:to-white/3 hover:shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] ${
        active
          ? "shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)]"
          : "shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]"
      }`}
    >
      {/* Kicker: perspective + outcome badge */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[13px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
          {decision.perspective}
        </span>
        <span
          className={`rounded-full border px-2.5 py-0.5 font-mono text-[13px] font-semibold uppercase ${
            outcomeLabel === "Pass"
              ? "border-[#00D084]/40 bg-[#00D084]/15 text-[#00D084]"
              : outcomeLabel === "Modify"
                ? "border-[#F59E0B]/40 bg-[#F59E0B]/15 text-[#F59E0B]"
                : "border-[#547D83]/40 bg-[#547D83]/20 text-[#B2D8DC]"
          }`}
        >
          {outcomeLabel}
        </span>
      </div>

      {/* Title: matches the Decision Stories card scale */}
      <h3 className="text-[22px] font-semibold leading-tight tracking-tight text-[#F8FAFC] transition-colors group-hover:text-[#B2D8DC]">
        {decision.title}
      </h3>

      {/* Agent perspective chip */}
      <div className="flex flex-wrap gap-2">
        <AgentChip tag={tag} />
      </div>

      {/* Outcome figures + open affordance */}
      <div className="mt-auto flex items-end justify-between gap-4 pt-1">
        <dl className="space-y-1.5">
          <div className="flex items-center gap-4">
            <dt className="font-mono text-[13px] text-[#64748B]">Active Outcome</dt>
            <dd
              className={`m-0 font-mono text-[16px] font-semibold tabular-nums ${resultColor(decision.active)}`}
            >
              {formatResult(decision.active)}
            </dd>
          </div>
          <div className="flex items-center gap-4">
            <dt className="font-mono text-[13px] text-[#64748B]">Best Shadow Path</dt>
            <dd className="m-0 font-mono text-[16px] font-semibold tabular-nums text-[#818CF8]">
              {formatResult(decision.alternative)}
            </dd>
          </div>
        </dl>
        <span
          aria-hidden="true"
          className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border transition-colors duration-200 ${
            active ? "border-[#547D83]/50 text-[#B2D8DC]" : "border-white/8 text-[#64748B]"
          }`}
        >
          <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </span>
      </div>
    </Link>
  );
}

export function OverviewDecisions({ decisions }: { decisions: OverviewDecision[] }) {
  return (
    <section className="overview-panel overview-decisions-panel">
      <div className="overview-decisions-head">
        <span className="overview-side-title">Recent decisions</span>
        <Link href="/stories" className="overview-see-all">
          See all decision stories
          <ArrowRight size={12} aria-hidden="true" />
        </Link>
      </div>

      {decisions.length === 0 ? (
        <p className="overview-chart-detail-empty">No decisions were recorded in this period.</p>
      ) : (
        <div className="overview-chips-row">
          {decisions.slice(0, 3).map((decision) => (
            <DecisionCard key={decision.storyId} decision={decision} />
          ))}
        </div>
      )}
    </section>
  );
}
