import { ArrowRight, CheckCircle2, SlidersHorizontal } from "lucide-react";
import Link from "next/link";

import { StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD } from "@/components/workspace/section-heading";
import type { WeeklySummary } from "@/features/story/monitoring-api";

const CONFIDENCE_TONE: Record<string, string> = {
  high: "#00D084",
  medium: "#F59E0B",
  low: "#64748B",
};

export function WeeklySummaryClient({ summary }: { summary: WeeklySummary }) {
  const confidenceOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...summary.suggestions].sort(
    (a, b) => (confidenceOrder[a.confidence] ?? 3) - (confidenceOrder[b.confidence] ?? 3),
  );

  return (
    <div className={`${SECTION_CARD} p-5 sm:p-6`}>
      {/* Mode row (compact — the section heading already names this block) */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 pb-4">
        <p className="text-[13px] text-[#94A3B8]">
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
            Manual Prescriptive mode.
          </span>{" "}
          Automatic switching is deferred; nothing here changes the active profile.
        </p>
        <StateBadge state="manual review" />
      </div>

      {/* Recommendation cards */}
      <div
        className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
        aria-label="AI Profile recommendations"
      >
        {sorted.map((suggestion) => {
          const tone = CONFIDENCE_TONE[suggestion.confidence] ?? "#64748B";
          return (
            <article
              key={suggestion.id}
              className="rounded-xl border border-white/8 bg-white/2 p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-semibold text-[#F8FAFC]">
                    {suggestion.parameterName}
                  </span>
                  <span
                    className="rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide"
                    style={{ color: tone, borderColor: `${tone}66`, background: `${tone}26` }}
                    aria-label={`${suggestion.confidence} confidence`}
                  >
                    {suggestion.confidence}
                  </span>
                </div>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[#00D084]">
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Within authorized
                  bounds
                </span>
              </div>

              {/* Current -> Recommended */}
              <div className="mt-4 flex items-center gap-4">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                    Current
                  </span>
                  <span className="mt-1 block font-mono text-[16px] font-semibold tabular-nums text-[#94A3B8]">
                    {suggestion.currentValue}
                  </span>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-[#64748B]" aria-hidden="true" />
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                    Recommended
                  </span>
                  <span className="mt-1 block font-mono text-[16px] font-semibold tabular-nums text-[#00D084]">
                    {suggestion.suggestedValue}
                  </span>
                </div>
              </div>

              <dl className="mt-4 space-y-2 border-t border-white/8 pt-3">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-[12px] text-[#64748B]">Authorized range</dt>
                  <dd className="m-0 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {suggestion.allowedMinimum} to {suggestion.allowedMaximum}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-[12px] text-[#64748B]">Validation state</dt>
                  <dd className="m-0 text-[13px] text-[#CBD5E1]">
                    {suggestion.validationState.replaceAll("_", " ")}
                  </dd>
                </div>
              </dl>

              <p className="mt-3 text-[13px] leading-relaxed text-[#94A3B8]">
                {suggestion.rationale}
              </p>

              {/* Carry the recommendation into the Rules profile editor for review + activation */}
              <Link
                href={`/rules?apply=${encodeURIComponent(suggestion.parameterId)}&value=${encodeURIComponent(suggestion.suggestedValue)}#configure-profile`}
                className="mt-4 inline-flex items-center gap-2 rounded-md border border-[#547D83]/40 bg-[#547D83]/20 px-3.5 py-2 text-[12px] font-semibold text-[#B2D8DC] outline-none transition-colors hover:bg-[#547D83]/30 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                Apply in profile editor
              </Link>
            </article>
          );
        })}
      </div>
    </div>
  );
}
