"use client";

import { GitCompareArrows, TrendingDown, TrendingUp, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { parseMoney } from "@/features/story/formatters";
import type { AlternativeSession, ChartPoint } from "@/features/story/monitoring-api";

export type MultiverseBranchKey =
  "active" | "cash" | "halfSize" | "contrarian" | "agentAlternative";

export interface MultiverseSeries {
  key: MultiverseBranchKey;
  label: string;
  description: string;
  color: string;
  dashed: boolean;
}

export const MULTIVERSE_BRANCHES: MultiverseSeries[] = [
  {
    key: "active",
    label: "Active Portfolio",
    description: "Decisions executed / chosen by PRISM",
    color: "#00D084",
    dashed: false,
  },
  {
    key: "cash",
    label: "Cash Baseline",
    description: "Capital kept in cash ($0.00)",
    color: "#94A3B8",
    dashed: true,
  },
  {
    key: "halfSize",
    label: "Half Size (50%)",
    description: "Reduced allocation risk counterfactual",
    color: "#FBBF24",
    dashed: true,
  },
  {
    key: "contrarian",
    label: "Contrarian Thesis",
    description: "Thesis reversed / unhedged counterfactual",
    color: "#F87171",
    dashed: true,
  },
  {
    key: "agentAlternative",
    label: "AI Alternative",
    description: "Specialist research alternative branch",
    color: "#818CF8",
    dashed: true,
  },
];

export interface MultiverseRow {
  date: string;
  rawDate: string;
  active: number;
  cash: number;
  halfSize: number;
  contrarian: number;
  agentAlternative: number;
}

function formatChartTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    });
  } catch {
    return iso;
  }
}

function formatPnl(value: number): string {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}$${value.toFixed(2)}`;
}

function toNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildMultiverseRows(
  aggregatePath: ChartPoint[] | undefined,
  sessions: AlternativeSession[],
): MultiverseRow[] {
  // If aggregatePath has >= 2 data points, prioritize backend-computed trajectory
  if (aggregatePath && aggregatePath.length >= 2) {
    return aggregatePath.map((pt) => ({
      date: formatChartTime(pt.date),
      rawDate: pt.date,
      active: toNumber(pt.chosenPath) ?? 0,
      cash: toNumber(pt.cashBaseline) ?? 0,
      halfSize: toNumber(pt.reducedSize) ?? 0,
      contrarian: toNumber(pt.unhedged) ?? 0,
      agentAlternative: toNumber(pt.agentAlternative) ?? 0,
    }));
  }

  // Synthesize cumulative chronological trajectory across sessions
  if (!sessions || sessions.length === 0) return [];

  const sorted = [...sessions].sort(
    (a, b) => new Date(a.occurredAt).getTime() - new Date(b.occurredAt).getTime(),
  );

  let cumActive = 0;
  let cumCash = 0;
  let cumHalfSize = 0;
  let cumContrarian = 0;
  let cumAgentAlt = 0;

  const rows: MultiverseRow[] = [];

  // Start with a zero baseline point right before the first session
  const firstTime = new Date(sorted[0].occurredAt).getTime();
  const baselineTime = new Date(firstTime - 30 * 60 * 1000).toISOString();
  rows.push({
    date: formatChartTime(baselineTime),
    rawDate: baselineTime,
    active: 0,
    cash: 0,
    halfSize: 0,
    contrarian: 0,
    agentAlternative: 0,
  });

  for (const session of sorted) {
    const chosenPnl = parseMoney(session.chosenPathPnl);
    if (Number.isFinite(chosenPnl)) cumActive += chosenPnl;

    for (const b of session.branches) {
      const pnl = parseMoney(b.pnl);
      if (!Number.isFinite(pnl)) continue;

      if (b.branchKey === "cash" || b.branchKey === "no-action") {
        cumCash += pnl;
      } else if (b.branchKey === "half_size" || b.branchKey === "reduced-size") {
        cumHalfSize += pnl;
      } else if (b.branchKey === "contrarian" || b.branchKey === "unhedged") {
        cumContrarian += pnl;
      } else if (b.branchKey === "ai_alternative" || b.branchKey === "agent-alternative") {
        cumAgentAlt += pnl;
      }
    }

    rows.push({
      date: formatChartTime(session.occurredAt),
      rawDate: session.occurredAt,
      active: Number(cumActive.toFixed(2)),
      cash: Number(cumCash.toFixed(2)),
      halfSize: Number(cumHalfSize.toFixed(2)),
      contrarian: Number(cumContrarian.toFixed(2)),
      agentAlternative: Number(cumAgentAlt.toFixed(2)),
    });
  }

  return rows;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-xl border border-white/12 bg-[#0B0F17]/95 p-3.5 shadow-2xl backdrop-blur-md">
      <p className="font-mono text-[11px] text-[#94A3B8]">{label} UTC</p>
      <div className="mt-2 space-y-1.5 border-t border-white/8 pt-2">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5 font-medium" style={{ color: entry.color }}>
              <span
                aria-hidden="true"
                className="h-2 w-2 rounded-full"
                style={{ background: entry.color }}
              />
              {entry.name}
            </span>
            <span className="font-mono font-semibold tabular-nums text-[#F8FAFC]">
              {formatPnl(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ShadowMultiverseChart({
  aggregatePath,
  sessions,
  className,
}: {
  aggregatePath?: ChartPoint[];
  sessions: AlternativeSession[];
  className?: string;
}) {
  const rows = useMemo(
    () => buildMultiverseRows(aggregatePath, sessions),
    [aggregatePath, sessions],
  );

  // Hidden set for toggling series
  const [hidden, setHidden] = useState<Set<MultiverseBranchKey>>(() => new Set());

  const toggle = (key: MultiverseBranchKey) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const visibleBranches = MULTIVERSE_BRANCHES.filter((b) => !hidden.has(b.key));

  // Compute summary stats from latest observation
  const latest = rows.length > 0 ? rows[rows.length - 1] : null;
  const activePnl = latest?.active ?? 0;

  const shadowPerformance = useMemo(() => {
    if (!latest) return null;
    const candidates = [
      { key: "cash", label: "Cash Baseline", val: latest.cash },
      { key: "halfSize", label: "Half Size (50%)", val: latest.halfSize },
      { key: "contrarian", label: "Contrarian Thesis", val: latest.contrarian },
      { key: "agentAlternative", label: "AI Alternative", val: latest.agentAlternative },
    ];
    candidates.sort((a, b) => b.val - a.val);
    const best = candidates[0];
    const delta = best.val - activePnl;
    return { best, delta };
  }, [latest, activePnl]);

  if (rows.length === 0) {
    return (
      <div
        className={`rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-6 backdrop-blur-xl ${
          className ?? ""
        }`}
      >
        <p className="inline-empty text-center text-[13px] text-[#64748B]">
          No shadow portfolio trajectories fall inside this period.
        </p>
      </div>
    );
  }

  return (
    <section
      aria-labelledby="multiverse-chart-heading"
      className={`rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] sm:p-6 ${
        className ?? ""
      }`}
    >
      {/* Header section */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2
            id="multiverse-chart-heading"
            className="flex items-center gap-2 text-lg font-semibold tracking-tight text-[#F8FAFC]"
          >
            <span className="grid h-7 w-7 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]">
              <GitCompareArrows className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
            Multiverse Trajectory Comparison
          </h2>
          <p className="mt-1 text-[12px] text-[#64748B]">
            Cumulative simulated performance of Active Portfolio vs. every ShadowFund counterfactual
            branch.
          </p>
        </div>

        {/* Metric summary badges */}
        {shadowPerformance && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-lg border border-white/8 bg-white/4 px-3 py-1.5">
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#64748B]">
                Active Return
              </span>
              <p
                className={`font-mono text-sm font-semibold tabular-nums ${
                  activePnl >= 0 ? "text-[#00D084]" : "text-[#FF6B6B]"
                }`}
              >
                {formatPnl(activePnl)}
              </p>
            </div>

            <div className="rounded-lg border border-[#818CF8]/25 bg-[#818CF8]/10 px-3 py-1.5">
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#818CF8]">
                Best Alternative
              </span>
              <p className="font-mono text-sm font-semibold tabular-nums text-[#F8FAFC]">
                {shadowPerformance.best.label}:{" "}
                <span className="text-[#34D399]">{formatPnl(shadowPerformance.best.val)}</span>
              </p>
            </div>

            <div className="rounded-lg border border-white/8 bg-white/4 px-3 py-1.5">
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#64748B]">
                Delta vs Active
              </span>
              <p
                className={`flex items-center gap-1 font-mono text-sm font-semibold tabular-nums ${
                  shadowPerformance.delta >= 0 ? "text-[#34D399]" : "text-[#FF6B6B]"
                }`}
              >
                {shadowPerformance.delta >= 0 ? (
                  <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {formatPnl(shadowPerformance.delta)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Branch toggles */}
      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/8 pt-4">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
          Toggle Portfolios:
        </span>
        {MULTIVERSE_BRANCHES.map((b) => {
          const isOn = !hidden.has(b.key);
          return (
            <button
              key={b.key}
              type="button"
              onClick={() => toggle(b.key)}
              aria-pressed={isOn}
              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-[#547D83]"
              style={{
                color: isOn ? b.color : "#64748B",
                borderColor: isOn ? `${b.color}55` : "rgba(255,255,255,0.08)",
                background: isOn ? `${b.color}15` : "transparent",
                opacity: isOn ? 1 : 0.5,
              }}
            >
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: b.color }}
              />
              {b.label}
            </button>
          );
        })}
      </div>

      {/* Chart container */}
      <div
        className="mt-4 min-h-[320px] w-full sm:min-h-[360px]"
        role="img"
        aria-label="Multiverse Portfolio Comparison Line Chart"
      >
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={rows} margin={{ top: 16, right: 24, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#64748B", fontSize: 11 }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={54}
              tick={{ fill: "#64748B", fontSize: 11 }}
              tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            />
            <Tooltip content={<CustomTooltip />} />
            {visibleBranches.map((b) => (
              <Line
                key={b.key}
                type="monotone"
                dataKey={b.key}
                name={b.label}
                stroke={b.color}
                strokeWidth={b.key === "active" ? 2.5 : 1.75}
                strokeDasharray={b.dashed ? "5 5" : undefined}
                dot={{ r: 2.5, fill: b.color }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "#0B0F17" }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer explanation notice */}
      <div className="mt-3 flex items-center justify-between border-t border-white/8 pt-3 text-[11px] text-[#64748B]">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-[#818CF8]" aria-hidden="true" />
          <span>
            Non-executable ShadowFund simulation tracking deterministic counterfactual outcomes.
          </span>
        </div>
        <span className="font-mono">
          {sessions.length} session{sessions.length === 1 ? "" : "s"} evaluated
        </span>
      </div>
    </section>
  );
}
