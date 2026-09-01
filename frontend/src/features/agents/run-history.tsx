"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD } from "@/components/workspace/section-heading";
import { formatDateTime, formatTokens } from "@/features/story/formatters";
import { rangeForPreset, type RangePreset } from "@/features/story/date-range";

export type AgentRunItem = {
  id: string;
  trigger: string;
  status: string;
  occurredAt: string;
  summary: string;
  durationMs: number;
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
};

const PRESETS: Array<{ value: Exclude<RangePreset, "custom">; label: string }> = [
  { value: "7d", label: "7D" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
];

/**
 * Run history with its OWN client-side range filter. Selecting a preset only
 * refilters this list; it does not navigate or reload the rest of the page.
 */
export function RunHistory({
  runs,
  anchor,
  heading,
}: {
  runs: AgentRunItem[];
  anchor: string;
  heading?: ReactNode;
}) {
  const [preset, setPreset] = useState<Exclude<RangePreset, "custom">>("1m");

  const filtered = useMemo(() => {
    const range = rangeForPreset(preset, anchor);
    return runs.filter((run) => {
      const day = run.occurredAt.slice(0, 10);
      return day >= range.from && day <= range.to;
    });
  }, [runs, preset, anchor]);

  return (
    <>
      {/* Heading (left) inline with the range picker (right) */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {heading && <div className="min-w-0">{heading}</div>}
        <div
          className="inline-flex items-center gap-1 rounded-full border border-white/8 bg-white/5 p-1"
          role="group"
          aria-label="Run history date range presets"
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

      {filtered.length === 0 ? (
        <div className={`${SECTION_CARD} p-6`}>
          <p className="text-[13px] text-[#94A3B8]">
            No recorded runs fall inside this date range.
          </p>
        </div>
      ) : (
        <ul className="space-y-4">
          {filtered.map((run) => (
            <li key={run.id} className={`${SECTION_CARD} p-5 sm:p-6`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="text-[15px] font-semibold text-[#F8FAFC]">{run.trigger}</span>
                  <StateBadge state={run.status} />
                </div>
                <time
                  dateTime={run.occurredAt}
                  className="font-mono text-[12px] tabular-nums text-[#64748B]"
                >
                  {formatDateTime(run.occurredAt)}
                </time>
              </div>
              <p className="mt-2 text-[14px] leading-relaxed text-[#CBD5E1]">{run.summary}</p>
              <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-white/8 pt-4 sm:grid-cols-4">
                {[
                  { dt: "Duration", dd: `${run.durationMs} ms` },
                  { dt: "Input", dd: formatTokens(run.inputTokens) },
                  { dt: "Output", dd: formatTokens(run.outputTokens) },
                  { dt: "Cached", dd: formatTokens(run.cachedTokens) },
                ].map((row) => (
                  <div key={row.dt}>
                    <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                      {row.dt}
                    </dt>
                    <dd className="mt-1 font-mono text-[14px] tabular-nums text-[#CBD5E1]">
                      {row.dd}
                    </dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
