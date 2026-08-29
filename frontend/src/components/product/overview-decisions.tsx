"use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
} from "lucide-react";

import { recentDecisions } from "@/features/story/overview-data";

const agentClass = {
  risk: "overview-agent-risk",
  proposal: "overview-agent-proposal",
  research: "overview-agent-research",
} as const;

const outcomeClass = {
  Modify: "overview-outcome-modify",
  Pass: "overview-outcome-pass",
  "No trade": "overview-outcome-notrade",
} as const;

function formatResult(value: number) {
  if (value === 0) return "$0";

  return `${value > 0 ? "+" : "-"}$${Math.abs(value).toLocaleString()}`;
}

function resultClass(value: number) {
  if (value > 0) return "overview-pos";
  if (value < 0) return "overview-neg";
  return "overview-neu";
}

export function OverviewDecisions() {
  return (
    <section className="overview-panel overview-decisions-panel">
      <div className="overview-decisions-head">
        <span className="overview-side-title">Recent decisions</span>

        <Link
          href="/stories"
          className="overview-see-all"
        >
          See all decision stories
          <ArrowRight size={12} aria-hidden="true" />
        </Link>
      </div>

      <div className="overview-chips-row">
        {recentDecisions.map((decision) => (
          <Link
            href="/stories"
            key={`${decision.sym}-${decision.date}`}
            className="overview-chip"
            style={
              {
                "--chip-accent":
                  decision.agent === "risk"
                    ? "#F59E0B"
                    : decision.agent === "proposal"
                      ? "#10B981"
                      : "#38BDF8",
              } as React.CSSProperties
            }
          >
            <div className="overview-chip-top">
              <div className="overview-chip-symbol-wrap">
                <div className="overview-chip-icon">
                  {decision.sym.slice(0, 2)}
                </div>

                <div>
                  <div className="overview-chip-symbol">
                    {decision.sym}
                  </div>

                  <div className="overview-chip-date">
                    {decision.date}
                  </div>
                </div>
              </div>

              <span
                className={`overview-outcome-tag ${outcomeClass[decision.outcome]}`}
              >
                {decision.outcome}
              </span>
            </div>

            <div>
              <span
                className={`overview-agent-tag ${agentClass[decision.agent]}`}
              >
                <span className="overview-agent-dot" />
                <Bot size={9} />
                {decision.agentLabel}
              </span>

              <div className="overview-chip-title">
                {decision.title}
              </div>

              <div className="overview-chip-reasoning">
                {decision.reasoning}
              </div>
            </div>

            <div className="overview-chip-bottom overview-nums">
              <span className={resultClass(decision.paper)}>
                {formatResult(decision.paper)}
              </span>

              <span className="overview-chip-alt">
                alt {formatResult(decision.alt)}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}