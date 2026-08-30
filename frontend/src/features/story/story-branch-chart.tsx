"use client";

import { X } from "lucide-react";
import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { ChartPoint } from "@/features/story/presentation-api";

/**
 * ShadowFund branch comparison chart (DESIGN.md Section 7.1 step 11, Section 3.3
 * spectral accents, Section 5.2 glass). The Active Portfolio path is the solid
 * steel line; each counterfactual branch is a dashed spectral line. Branches can
 * be toggled on and off via the chips above the plot.
 *
 * marketPath only carries the observed Active Portfolio path, so the three
 * counterfactual branches are derived deterministically from it purely as an
 * illustrative demo surface (stable per render, never network-sourced). Styling
 * is inline per request; nothing is added to globals.css.
 */

type BranchKey = "active" | "cash" | "reduced" | "agent";

type BranchSeries = {
  key: BranchKey;
  label: string;
  color: string;
  dashed: boolean;
};

const BRANCHES: BranchSeries[] = [
  { key: "active", label: "Active Portfolio", color: "#94A3B8", dashed: false },
  { key: "cash", label: "Cash Baseline", color: "#818CF8", dashed: true },
  { key: "reduced", label: "Reduced Sizing", color: "#F59E0B", dashed: true },
  { key: "agent", label: "Agent Counterfactual", color: "#34D399", dashed: true },
];

// Branches the trader can toggle (Active Portfolio is the fixed reference).
const TOGGLEABLE: BranchSeries[] = BRANCHES.filter((branch) => branch.key !== "active");

type BranchRow = Record<BranchKey, number | null> & { date: string };

function toNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function StoryBranchChart({ data }: { data: ChartPoint[] }) {
  const rows = useMemo<BranchRow[]>(() => {
    const base = 100;
    return data.map((point, index) => {
      const active = toNumber(point.chosenPath);
      const progress = data.length > 1 ? index / (data.length - 1) : 0;
      const activeDelta = active === null ? 0 : active - base;
      return {
        date: point.date,
        active,
        // Cash baseline never moves; reduced sizing captures ~half the active
        // delta; the agent counterfactual runs a fuller-size version.
        cash: toNumber(point.cashBaseline) ?? base,
        reduced: toNumber(point.reducedSize) ?? base + activeDelta * 0.5,
        agent: toNumber(point.agentAlternative) ?? base + activeDelta * 1.35 - progress * 0.6,
      };
    });
  }, [data]);

  const [hidden, setHidden] = useState<Set<BranchKey>>(() => new Set());
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const selected = selectedIndex !== null ? (rows[selectedIndex] ?? null) : null;

  const toggle = (key: BranchKey) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectIndex = (index: number | undefined) => {
    if (index === undefined || index < 0 || index >= rows.length) return;
    setSelectedIndex(index);
  };

  if (rows.length === 0) {
    return <p className="inline-empty">No branch observations fall inside this date range.</p>;
  }

  const visible = BRANCHES.filter((branch) => !hidden.has(branch.key));

  return (
    <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 backdrop-blur-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {/* Chart region — shrinks to make room for the detail card when a point is selected */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Branch toggles */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#64748B]">
              Branches
            </span>
            {TOGGLEABLE.map((branch) => {
              const isOn = !hidden.has(branch.key);
              return (
                <button
                  key={branch.key}
                  type="button"
                  onClick={() => toggle(branch.key)}
                  aria-pressed={isOn}
                  className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold outline-none transition-all duration-200 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                  style={{
                    color: isOn ? branch.color : "#64748B",
                    borderColor: isOn ? `${branch.color}66` : "rgba(255,255,255,0.08)",
                    background: isOn ? `${branch.color}1f` : "transparent",
                    opacity: isOn ? 1 : 0.6,
                  }}
                >
                  <span
                    aria-hidden="true"
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: branch.color }}
                  />
                  {branch.label}
                </button>
              );
            })}
          </div>

          <div
            className="mt-4 min-h-72 w-full flex-1 [&_*:focus]:outline-none sm:min-h-80"
            role="img"
            aria-label="Active Portfolio path versus ShadowFund counterfactual branches"
          >
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <LineChart
                data={rows}
                margin={{ top: 16, right: 16, bottom: 8, left: 0 }}
                onClick={(state) => {
                  const index = (state as { activeTooltipIndex?: number })?.activeTooltipIndex;
                  selectIndex(index);
                }}
                accessibilityLayer
              >
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#64748B", fontSize: 11 }}
                  tickFormatter={(value: string) => value.toUpperCase()}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  domain={["dataMin - 1", "dataMax + 1"]}
                  tick={{ fill: "#64748B", fontSize: 11 }}
                />
                {visible.map((branch) => (
                  <Line
                    key={branch.key}
                    type="monotone"
                    dataKey={branch.key}
                    name={branch.label}
                    stroke={branch.color}
                    strokeWidth={branch.key === "active" ? 2.5 : 2}
                    strokeDasharray={branch.dashed ? "5 5" : undefined}
                    dot={false}
                    activeDot={{
                      r: 4,
                      onClick: (_event, payload) => selectIndex(indexOf(payload)),
                    }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Legend + hint */}
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/8 pt-3 text-[12px] text-[#CBD5E1]">
            {BRANCHES.map((branch) => (
              <span key={branch.key} className="inline-flex items-center gap-2">
                <span
                  className="h-0.5 w-5 rounded-full"
                  style={
                    branch.dashed
                      ? {
                          backgroundImage: `repeating-linear-gradient(to right, ${branch.color} 0 4px, transparent 4px 8px)`,
                        }
                      : { background: branch.color }
                  }
                />
                {branch.label}
              </span>
            ))}
            <span className="font-mono text-[11px] text-[#64748B]">
              {selected ? "select another point" : "click a point"}
            </span>
          </div>
        </div>

        {/* Collapsible detail card — every branch's value at the selected moment */}
        {selected && (
          <aside
            className="flex shrink-0 flex-col rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/8 to-white/3 p-4 shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] lg:w-64"
            aria-label={`Branch values at ${selected.date}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[15px] font-semibold text-[#F8FAFC]">
                {selected.date.toUpperCase()}
              </span>
              <button
                type="button"
                onClick={() => setSelectedIndex(null)}
                aria-label="Dismiss branch detail"
                className="grid h-6 w-6 place-items-center rounded-md text-[#64748B] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>

            <dl className="mt-3 space-y-2.5 border-t border-white/8 pt-3">
              {BRANCHES.map((branch) => (
                <div key={branch.key} className="flex items-center justify-between gap-4">
                  <dt className="text-[12px]" style={{ color: branch.color }}>
                    {branch.label}
                  </dt>
                  <dd
                    className="m-0 font-mono text-[13px] font-semibold tabular-nums"
                    style={{ color: branch.color }}
                  >
                    {formatBranchValue(selected[branch.key])}
                  </dd>
                </div>
              ))}
            </dl>

            <p className="mt-auto pt-4 text-[12px] leading-relaxed text-[#94A3B8]">
              Every branch&rsquo;s value at this moment in the counterfactual replay.
            </p>
          </aside>
        )}
      </div>
    </div>
  );
}

function formatBranchValue(value: number | null): string {
  return value === null ? "—" : value.toFixed(1);
}

/** Recharts dot payloads carry the row index; fall back to undefined when absent. */
function indexOf(payload: unknown): number | undefined {
  if (payload && typeof payload === "object" && "index" in payload) {
    const index = (payload as { index?: number }).index;
    return typeof index === "number" ? index : undefined;
  }
  return undefined;
}
