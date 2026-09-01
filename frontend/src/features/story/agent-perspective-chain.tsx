"use client";

import {
  Activity,
  BarChart3,
  Building2,
  Factory,
  Globe,
  Newspaper,
  Scale,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import type { AgentPerspective } from "@/features/story/monitoring-api";

type AgentKey = NonNullable<AgentPerspective["agentKey"]>;
type Agent = { key: AgentKey; label: string; icon: LucideIcon; color: string };

// This roster provides visual identity only. Decision content is always API data.
const AGENTS: Agent[] = [
  { key: "news", label: "News Agent", icon: Newspaper, color: "#38BDF8" },
  { key: "quantitative", label: "Quantitative Agent", icon: BarChart3, color: "#22D3EE" },
  { key: "industry", label: "Industry Agent", icon: Factory, color: "#F59E0B" },
  { key: "fundamental", label: "Fundamental Agent", icon: Building2, color: "#A78BFA" },
  { key: "macroeconomic", label: "Macroeconomic Agent", icon: Globe, color: "#F472B6" },
  {
    key: "market_reaction",
    label: "Market Reaction/Mispricing Agent",
    icon: Activity,
    color: "#10B981",
  },
  { key: "trading_decision", label: "Trading Decision Agent", icon: Scale, color: "#34D399" },
];

export function AgentPerspectiveChain({ perspectives }: { perspectives: AgentPerspective[] }) {
  const [activeKey, setActiveKey] = useState<AgentKey>("news");
  const active = AGENTS.find((agent) => agent.key === activeKey) ?? AGENTS[0];
  const record = perspectives.find((item) => item.agentKey === active.key);
  const unavailable = !record || record.status === "unavailable";
  const reconstructed = record?.provenance === "retrospective_reconstruction";
  const evidence = record?.evidence ?? [];
  const limitations = record?.limitations ?? [];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.8fr)] lg:items-stretch">
      <ul className="flex flex-col gap-2" aria-label="Agent perspectives">
        {AGENTS.map((agent) => {
          const Icon = agent.icon;
          const selected = agent.key === active.key;
          const state = perspectives.find((item) => item.agentKey === agent.key);
          return (
            <li key={agent.key} className="flex-1">
              <button
                type="button"
                onClick={() => setActiveKey(agent.key)}
                aria-pressed={selected}
                className="flex h-full w-full items-center gap-2.5 rounded-xl border border-t-white/16 px-3.5 py-3 text-left backdrop-blur-xl transition-all duration-200 outline-none hover:-translate-y-px hover:!border-[#547D83]/40 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                style={{
                  borderColor: selected ? "rgba(84,125,131,0.5)" : "rgba(255,255,255,0.08)",
                  background: selected
                    ? "linear-gradient(180deg, rgba(84,125,131,0.18), rgba(84,125,131,0.06))"
                    : "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                }}
              >
                <Icon
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0"
                  style={{ color: agent.color }}
                />
                <span
                  className="text-[13px] font-semibold"
                  style={{ color: selected ? "#F8FAFC" : "#CBD5E1" }}
                >
                  {agent.label}
                </span>
                <span
                  className="ml-auto h-2 w-2 rounded-full"
                  aria-hidden="true"
                  style={{ background: state?.status === "recorded" ? agent.color : "#64748B" }}
                />
              </button>
            </li>
          );
        })}
      </ul>
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
          {reconstructed ? (
            <span className="rounded-full border border-[#00D084]/40 bg-[#00D084]/15 px-2.5 py-1 text-[11px] font-semibold text-[#00D084]">
              Success
            </span>
          ) : (
            <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
              Recorded live research
            </span>
          )}
        </div>
        {unavailable ? (
          <p className="mt-5 text-[13px] leading-relaxed text-[#94A3B8]">
            No durable decision was recorded.
          </p>
        ) : (
          <>
            <h3 className="mt-4 text-[17px] font-semibold leading-snug text-[#F8FAFC]">
              {record.headline}
            </h3>
            <p className="mt-1.5 text-[13px] leading-relaxed text-[#94A3B8]">{record.summary}</p>
            {evidence.length > 0 && (
              <p className="mt-4 text-[12px] leading-relaxed text-[#CBD5E1]">
                <span className="font-semibold">Evidence:</span> {evidence.join(" · ")}
              </p>
            )}
            {limitations.length > 0 && (
              <p className="mt-2 text-[12px] leading-relaxed text-[#FCD34D]">
                <span className="font-semibold">Limitations:</span> {limitations.join(" · ")}
              </p>
            )}
            <p className="mt-5 font-mono text-[11px] text-[#64748B]">
              {record.occurredAt
                ? new Date(record.occurredAt).toISOString()
                : "Timestamp unavailable"}
            </p>
            {reconstructed && (
              <p className="mt-2 text-[12px] text-[#94A3B8]">
                Source: {record.sourceTitle ?? "Day 1 operations report"} · original invocation
                metadata unavailable
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
