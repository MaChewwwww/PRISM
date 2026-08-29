"use client";

import { ArrowRight, Bot } from "lucide-react";
import Link from "next/link";

import type { OverviewDecision } from "@/features/story/overview-adapter";

const agentClass = {
  risk: "overview-agent-risk",
  proposal: "overview-agent-proposal",
  research: "overview-agent-research",
  rules: "overview-agent-rules",
} as const;

const outcomeClass = {
  Modify: "overview-outcome-modify",
  Pass: "overview-outcome-pass",
  "No trade": "overview-outcome-notrade",
} as const;

function formatResult(value: number) {
  if (value === 0) return "$0";
  return `${value > 0 ? "+" : "-"}$${Math.abs(Math.round(value)).toLocaleString()}`;
}

function resultClass(value: number) {
  if (value > 0) return "overview-pos";
  if (value < 0) return "overview-neg";
  return "overview-neu";
}

function decisionDisplay(decision: OverviewDecision): {
  label: keyof typeof outcomeClass;
  agent: keyof typeof agentClass;
} {
  if (decision.ruleResult === "MODIFY") return { label: "Modify", agent: "risk" as const };
  if (decision.ruleResult === "PASS") return { label: "Pass", agent: "proposal" as const };
  if (decision.ruleResult === "FAIL") return { label: "No trade", agent: "research" as const };
  return { label: "No trade", agent: "rules" as const };
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
          {decisions.slice(0, 3).map((decision) => {
            const display = decisionDisplay(decision);
            return (
              <Link
                href={`/stories/${decision.storyId}`}
                key={decision.storyId}
                className="overview-chip"
              >
                <div className="overview-chip-top">
                  <div className="overview-chip-symbol-wrap">
                    <div className="overview-chip-icon">
                      {decision.storyId.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="overview-chip-symbol">{decision.perspective}</div>
                      <div className="overview-chip-date">Active Portfolio</div>
                    </div>
                  </div>
                  <span className={`overview-outcome-tag ${outcomeClass[display.label]}`}>
                    {display.label}
                  </span>
                </div>

                <div>
                  <span
                    className={`overview-agent-tag ${agentClass[display.agent]}`}
                    style={
                      {
                        "--chip-accent":
                          display.agent === "risk"
                            ? "#F59E0B"
                            : display.agent === "proposal"
                              ? "#10B981"
                              : display.agent === "rules"
                                ? "#547D83"
                                : "#38BDF8",
                      } as React.CSSProperties
                    }
                  >
                    <span className="overview-agent-dot" />
                    <Bot size={9} />
                    {display.agent === "risk"
                      ? "Risk Management"
                      : display.agent === "proposal"
                        ? "Trading Decision"
                        : display.agent === "rules"
                          ? "Rules Engine"
                          : "Research"}
                  </span>
                  <div className="overview-chip-title">{decision.title}</div>
                  <div className="overview-chip-reasoning">{decision.outcome} governed outcome</div>
                </div>

                <div className="overview-chip-bottom overview-nums">
                  <span className={resultClass(decision.active)}>
                    {formatResult(decision.active)}
                  </span>
                  <span className="overview-chip-alt">
                    alt {formatResult(decision.alternative)}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
