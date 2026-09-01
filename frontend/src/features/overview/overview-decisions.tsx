"use client";

import { ArrowRight, ArrowUpRight, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { OverviewDecision } from "@/features/overview/overview-adapter";

const OUTCOME_LABEL: Record<OverviewDecision["ruleResult"], string> = {
  PASS: "Pass",
  MODIFY: "Modify",
  FAIL: "No trade",
  NOT_EVALUATED: "No trade",
};

function formatResult(value: number) {
  if (value === 0) return "$0";
  return `${value > 0 ? "+" : "-"}$${Math.abs(Math.round(value)).toLocaleString()}`;
}

function resultColor(value: number) {
  if (value > 0) return "text-[#00D084]";
  if (value < 0) return "text-[#FF6B6B]";
  return "text-[#64748B]";
}

function DecisionCard({ decision }: { decision: OverviewDecision }) {
  const [active, setActive] = useState(false);
  const outcomeLabel = OUTCOME_LABEL[decision.ruleResult];
  const decisionLabel = storyDecisionLabel(decision.symbol, decision.outcome);

  return (
    <Link
      href={`/stories/${decision.storyId}`}
      onMouseEnter={() => setActive(true)}
      onMouseLeave={() => setActive(false)}
      onFocus={() => setActive(true)}
      onBlur={() => setActive(false)}
      className={`group flex flex-col gap-2 rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-3.5 outline-none backdrop-blur-xl transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:border-t-[#B2D8DC]/50 hover:from-white/8 hover:to-white/3 hover:shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] ${
        active
          ? "shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)]"
          : "shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]"
      }`}
    >
      {/* Kicker: perspective + outcome badge */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
          {decision.perspective}
        </span>
        <span
          className={`rounded-full border px-2 py-0.5 font-mono text-[9px] font-semibold uppercase ${
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

      {/* Title: plain decision label */}
      <h3 className="text-[14px] font-semibold leading-snug tracking-tight text-[#F8FAFC] transition-colors group-hover:text-[#B2D8DC]">
        {decisionLabel}
      </h3>

      {/* Outcome figures + open affordance */}
      <div className="mt-auto flex items-end justify-between gap-3 pt-1">
        <dl className="space-y-0.5">
          <div className="flex items-center gap-3">
            <dt className="font-mono text-[10px] text-[#64748B]">Active</dt>
            <dd
              className={`m-0 font-mono text-[13px] font-semibold tabular-nums ${resultColor(decision.active)}`}
            >
              {formatResult(decision.active)}
            </dd>
          </div>
          <div className="flex items-center gap-3">
            <dt className="font-mono text-[10px] text-[#64748B]">Shadow</dt>
            <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#818CF8]">
              {formatResult(decision.alternative)}
            </dd>
          </div>
        </dl>
        <span
          aria-hidden="true"
          className={`grid h-7 w-7 shrink-0 place-items-center rounded-md border transition-colors duration-200 ${
            active ? "border-[#547D83]/50 text-[#B2D8DC]" : "border-white/8 text-[#64748B]"
          }`}
        >
          <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </span>
      </div>
    </Link>
  );
}

function storyDecisionLabel(symbol: string, outcome: string): string {
  switch (outcome) {
    case "pass":
    case "modify":
      return `Opened a position in ${symbol}`;
    case "no_trade":
      return `No trade — ${symbol}`;
    case "fail":
      return `Rejected the proposed ${symbol} trade`;
    case "degraded":
      return `Halted — ${symbol} (incomplete evidence)`;
    case "retrospective":
      return `Success — ${symbol}`;
    default:
      return symbol;
  }
}

function SectionHeading({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Zap;
  title: string;
  description: string;
}) {
  return (
    <div className="overview-section-header">
      <span className="overview-section-icon" aria-hidden="true">
        <Icon size={14} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function OverviewDecisions({ decisions }: { decisions: OverviewDecision[] }) {
  return (
    <section className="overview-panel overview-decisions-panel">
      <div className="overview-decisions-head">
        <SectionHeading
          icon={Zap}
          title="Recent decisions"
          description="Latest Active Portfolio agent decision outcomes."
        />
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
