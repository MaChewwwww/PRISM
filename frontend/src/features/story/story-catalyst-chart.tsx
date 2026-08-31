"use client";

import { X } from "lucide-react";
import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { ChartPoint } from "@/features/story/presentation-api";

/**
 * Interactive Catalyst reaction chart (DESIGN.md Section 7.1 step 1-2 and
 * Section 5.2 glass). Observed Reaction is the solid mineral-teal path; Analog
 * Expectation is a dashed amethyst reference line (DESIGN.md Section 3.3 +
 * "solid vs dashed" comparison rule). Clicking a point opens a dismissable
 * glass detail panel with the observed value, analog expectation, and the gap.
 */

const OBSERVED_COLOR = "#38BDF8";
const ANALOG_COLOR = "#818CF8";

type CatalystRow = {
  date: string;
  observed: number | null;
  analog: number | null;
};

function toNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatValue(value: number | null): string {
  return value === null ? "—" : value.toFixed(1);
}

function formatGap(observed: number | null, analog: number | null): string {
  if (observed === null || analog === null) return "—";
  const gap = observed - analog;
  return `${gap >= 0 ? "+" : ""}${gap.toFixed(1)}`;
}

function gapTone(observed: number | null, analog: number | null): string {
  if (observed === null || analog === null) return "text-[#64748B]";
  const gap = observed - analog;
  if (gap > 0) return "text-[#00D084]";
  if (gap < 0) return "text-[#FF6B6B]";
  return "text-[#64748B]";
}

export type CatalystDetail = {
  headline: string;
  source: string;
  classification: string;
  observedMove: string;
  expectedMove: string;
};

export function StoryCatalystChart({
  data,
  catalyst,
  note,
}: {
  data: ChartPoint[];
  catalyst: CatalystDetail;
  note?: string;
}) {
  const rows = useMemo<CatalystRow[]>(
    () =>
      data.map((point) => ({
        date: point.date,
        observed: toNumber(point.chosenPath),
        analog: toNumber(point.alternative),
      })),
    [data],
  );

  // Open the detail panel by default on the last (most complete) observation.
  const [selectedIndex, setSelectedIndex] = useState<number | null>(
    rows.length > 0 ? rows.length - 1 : null,
  );
  const selected = selectedIndex !== null ? (rows[selectedIndex] ?? null) : null;

  function selectIndex(index: number | undefined) {
    if (index === undefined || index < 0 || index >= rows.length) return;
    setSelectedIndex(index);
  }

  if (rows.length === 0) {
    return <p className="inline-empty">No catalyst observations fall inside this date range.</p>;
  }

  return (
    <div
      className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 backdrop-blur-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] sm:p-6"
      role="group"
      aria-label="Catalyst reaction timeline"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {/* Chart region — shrinks to make room for the aside when a point is selected,
            and grows vertically to match the detail panel's height (no gap below). */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div
            className="min-h-72 w-full flex-1 [&_*:focus]:outline-none sm:min-h-80"
            role="img"
            aria-label="Observed reaction versus analog expectation over the event window"
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
                <Line
                  type="monotone"
                  dataKey="analog"
                  name="Analog Expectation"
                  stroke={ANALOG_COLOR}
                  strokeWidth={2}
                  strokeDasharray="6 6"
                  dot={{ r: 3, fill: ANALOG_COLOR, strokeWidth: 0 }}
                  activeDot={{ r: 5, onClick: (_event, payload) => selectIndex(indexOf(payload)) }}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="observed"
                  name="Observed Reaction"
                  stroke={OBSERVED_COLOR}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: OBSERVED_COLOR, strokeWidth: 0 }}
                  activeDot={{ r: 6, onClick: (_event, payload) => selectIndex(indexOf(payload)) }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Legend + hint (DESIGN.md solid vs dashed comparison affordance) */}
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/8 pt-3 text-[12px] text-[#CBD5E1]">
            <span className="inline-flex items-center gap-2">
              <span className="h-0.5 w-5 rounded-full" style={{ background: OBSERVED_COLOR }} />
              Observed Reaction
            </span>
            <span className="inline-flex items-center gap-2">
              <span
                className="h-0.5 w-5 rounded-full"
                style={{
                  backgroundImage: `repeating-linear-gradient(to right, ${ANALOG_COLOR} 0 4px, transparent 4px 8px)`,
                }}
              />
              Analog Expectation
            </span>
            <span className="font-mono text-[11px] text-[#64748B]">
              {selected ? "select another point" : "click a point"}
            </span>
          </div>
        </div>

        {/* Collapsible detail panel — sits beside the chart and matches its height */}
        {selected && (
          <aside
            className="flex shrink-0 flex-col overflow-y-auto rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/8 to-white/3 p-4 shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] lg:w-72"
            aria-label={`Catalyst detail for ${selected.date}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[#B2D8DC]">
                Catalyst
              </span>
              <button
                type="button"
                onClick={() => setSelectedIndex(null)}
                aria-label="Dismiss catalyst detail"
                className="grid h-6 w-6 place-items-center rounded-md text-[#64748B] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>

            {/* Catalyst context first: headline + source, then classification */}
            <dl className="mt-3 space-y-2.5 border-t border-white/8 pt-3">
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                  Headline
                </dt>
                <dd className="m-0 mt-0.5 text-[12px] font-medium leading-snug text-[#F8FAFC]">
                  {catalyst.headline}
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                  Source
                </dt>
                <dd className="m-0 mt-0.5 text-[12px] leading-snug text-[#CBD5E1]">
                  {catalyst.source}
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                  Classification
                </dt>
                <dd className="m-0 mt-0.5 text-[12px] leading-snug text-[#CBD5E1]">
                  {catalyst.classification}
                </dd>
              </div>
            </dl>

            {/* Selected-point reaction gap */}
            <dl className="mt-3 space-y-2 border-t border-white/8 pt-3">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[12px] text-[#94A3B8]">Observed Reaction</dt>
                <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#F8FAFC]">
                  {formatValue(selected.observed)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[12px] text-[#94A3B8]">Analog Expectation</dt>
                <dd className="m-0 font-mono text-[13px] font-semibold tabular-nums text-[#818CF8]">
                  {formatValue(selected.analog)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-[12px] text-[#94A3B8]">Gap</dt>
                <dd
                  className={`m-0 font-mono text-[13px] font-semibold tabular-nums ${gapTone(selected.observed, selected.analog)}`}
                >
                  {formatGap(selected.observed, selected.analog)}
                </dd>
              </div>
            </dl>

            {/* Aggregate move summary */}
            <dl className="mt-3 space-y-2 border-t border-white/8 pt-3">
              <div className="flex items-center justify-between gap-4">
                <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                  Observed Move
                </dt>
                <dd className="m-0 font-mono text-[12px] font-semibold tabular-nums text-[#00D084]">
                  {catalyst.observedMove}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                  Expected Move
                </dt>
                <dd className="m-0 font-mono text-[12px] font-semibold tabular-nums text-[#818CF8]">
                  {catalyst.expectedMove}
                </dd>
              </div>
            </dl>

            {note && (
              <p className="mt-3 border-t border-white/8 pt-3 text-[12px] leading-relaxed text-[#94A3B8]">
                {note}
              </p>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

/** Recharts dot payloads carry the row index; fall back to -1 when absent. */
function indexOf(payload: unknown): number | undefined {
  if (payload && typeof payload === "object" && "index" in payload) {
    const index = (payload as { index?: number }).index;
    return typeof index === "number" ? index : undefined;
  }
  return undefined;
}
