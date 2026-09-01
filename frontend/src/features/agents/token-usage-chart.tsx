"use client";

import { useMemo, useState } from "react";

import { formatTokens } from "@/features/story/formatters";
import { rangeForPreset, type RangePreset } from "@/features/story/date-range";
import { StoryColumnChart } from "@/features/story/story-charts";

/** One agent's runs, trimmed to what the chart needs to filter + total by date. */
export type AgentTokenSeries = {
  name: string;
  role: string;
  runs: Array<{
    occurredAt: string;
    inputTokens: number;
    outputTokens: number;
    cachedTokens: number;
  }>;
};

const PRESETS: Array<{ value: Exclude<RangePreset, "custom">; label: string }> = [
  { value: "7d", label: "7D" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
];

/**
 * Token-usage column chart with its OWN client-side range filter. Selecting a
 * preset only recomputes and re-renders this chart; it does not navigate or
 * reload the rest of the page. The full run history is passed once from the
 * server and filtered here by each run's occurredAt date.
 */
export function TokenUsageChart({
  agents,
  anchor,
}: {
  agents: AgentTokenSeries[];
  /** Today (YYYY-MM-DD) from the server, so preset ranges are stable. */
  anchor: string;
}) {
  const [preset, setPreset] = useState<Exclude<RangePreset, "custom">>("1m");

  const { data, total } = useMemo(() => {
    const range = rangeForPreset(preset, anchor);
    const from = range.from;
    const to = range.to;
    const rows = agents.map((agent) => {
      const tokens = agent.runs.reduce((sum, run) => {
        const day = run.occurredAt.slice(0, 10);
        if (day < from || day > to) return sum;
        return sum + run.inputTokens + run.outputTokens + run.cachedTokens;
      }, 0);
      return { label: agent.name.split(" ")[0], value: String(tokens), description: agent.role };
    });
    const sum = rows.reduce((acc, row) => acc + Number(row.value), 0);
    return { data: rows, total: sum };
  }, [agents, preset, anchor]);

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <div
          className="inline-flex items-center gap-1 rounded-full border border-white/8 bg-white/5 p-1"
          role="group"
          aria-label="Chart date range presets"
        >
          {PRESETS.map((item) => {
            const isActive = preset === item.value;
            return (
              <button
                key={item.value}
                type="button"
                aria-pressed={isActive}
                onClick={() => setPreset(item.value)}
                className="rounded-full px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                style={{
                  color: isActive ? "#B2D8DC" : "#64748B",
                  background: isActive ? "rgba(84,125,131,0.2)" : "transparent",
                }}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <StoryColumnChart
        title="Visible token consumption"
        description="Input, output, and cached tokens from recorded runs. No provider billing claim is made."
        summary={`${formatTokens(total)} visible tokens`}
        data={data}
        barName="Tokens"
      />
    </div>
  );
}
