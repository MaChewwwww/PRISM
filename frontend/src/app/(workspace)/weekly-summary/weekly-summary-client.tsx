import { ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";

import { DisabledAction, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD } from "@/components/workspace/section-heading";
import type { WeeklySummary } from "@/features/story/presentation-api";

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
      {/* Mode header */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/8 pb-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
            Manual Prescriptive mode
          </p>
          <h3 className="mt-1 text-[15px] font-semibold text-[#F8FAFC]">
            Recommendations awaiting operator review
          </h3>
          <p className="mt-1 text-[13px] text-[#94A3B8]">
            Automatic switching is deferred. Nothing on this screen changes the active profile.
          </p>
        </div>
        <StateBadge state="manual review" />
      </div>

      {/* Deterministic boundary note */}
      <div className="mt-4 flex items-start gap-3 rounded-xl border border-[#547D83]/30 bg-[#547D83]/10 p-4">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#B2D8DC]" aria-hidden="true" />
        <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
          <strong className="font-semibold text-[#F8FAFC]">Deterministic boundary:</strong> only
          approved AI Profile fields may be proposed, and each value must remain inside the
          BA-authorized range.
        </p>
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
            </article>
          );
        })}
      </div>

      {/* Manual activation boundary */}
      <section className="mt-5 border-t border-white/8 pt-5" aria-labelledby="manual-review-title">
        <h3 id="manual-review-title" className="text-[15px] font-semibold text-[#F8FAFC]">
          Manual activation boundary
        </h3>
        <p className="mt-1 mb-3 text-[13px] leading-relaxed text-[#94A3B8]">
          The skeleton exposes review evidence only. It does not persist, approve, schedule, or
          activate a profile.
        </p>
        <DisabledAction
          label="Validate and activate profile"
          reason="Profile persistence, deterministic validation, and approval APIs are outside this aligned-skeleton pass."
        />
      </section>
    </div>
  );
}
