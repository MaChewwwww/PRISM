import { Lightbulb, ShieldCheck, SlidersHorizontal, TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { getWeeklySummary } from "@/features/story/presentation-api";

import { WeeklySummaryClient } from "./weekly-summary-client";

const METRIC_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]";

function pnlTone(value: string) {
  if (value.startsWith("+")) return "text-[#00D084]";
  if (value.startsWith("-")) return "text-[#FF6B6B]";
  return "text-[#F8FAFC]";
}

export default async function WeeklySummaryPage() {
  const summary = await getWeeklySummary();

  const metrics = [
    {
      label: "Stories analysed",
      value: String(summary.storiesAnalyzed),
      detail: `Week of ${summary.weekOf}`,
      tone: "text-[#F8FAFC]",
    },
    {
      label: "Active Portfolio net P&L",
      value: summary.illustrativeNetPnl,
      detail: "Net period return",
      tone: pnlTone(summary.illustrativeNetPnl),
    },
    {
      label: "Shadow beat chosen path",
      value: `${summary.shadowBeatChosen} / ${summary.storiesAnalyzed}`,
      detail: "Branches that outperformed",
      tone: "text-[#818CF8]",
    },
    {
      label: "Suggestions pending",
      value: String(summary.suggestions.length),
      detail: "AI Profile fields only",
      tone: "text-[#F8FAFC]",
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow={`Week of ${summary.weekOf}`}
        title="Weekly Post-Analysis"
        description="Post-Analysis reviews Active Portfolio decisions and ShadowFund outcomes, then recommends bounded AI Profile changes for manual review."
      >
        <div className="inline-flex items-center gap-1.5 rounded-full border border-[#818CF8]/30 bg-[#818CF8]/15 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[#C7D2FE]">
          <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" /> Post-analysis
        </div>
      </PageHeader>

      {/* Week at a glance */}
      <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className={METRIC_CARD}>
            <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
              {metric.label}
            </dt>
            <dd className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${metric.tone}`}>
              {metric.value}
            </dd>
            <p className="mt-1 text-[11px] text-[#64748B]">{metric.detail}</p>
          </div>
        ))}
      </dl>

      {/* AI key findings */}
      <section aria-labelledby="ai-findings" className="mt-6">
        <SectionHeading
          id="ai-findings"
          icon={Lightbulb}
          title="AI Analysis — Key Findings"
          subtitle="Vela post-analysis perspective synthesised from this week's decision stories and shadow-fund branch comparisons."
          accent="#818CF8"
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <ol className="space-y-4">
            {summary.keyFindings.map((finding, i) => (
              <li key={finding} className="flex items-start gap-3">
                <span
                  aria-hidden="true"
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 font-mono text-[11px] font-bold text-[#C7D2FE]"
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="text-[14px] leading-relaxed text-[#CBD5E1]">{finding}</p>
              </li>
            ))}
          </ol>
          <div className="mt-5 flex items-start gap-3 border-t border-white/8 pt-4">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#818CF8]" aria-hidden="true" />
            <p className="text-[12px] leading-relaxed text-[#94A3B8]">
              This analysis is produced by the autonomous Post-Analysis agent. It cannot authorise,
              submit, or modify any order or ruleset directly.
            </p>
          </div>
        </div>
      </section>

      {/* AI Profile recommendations */}
      <section aria-labelledby="calibration" className="mt-6">
        <SectionHeading
          id="calibration"
          icon={SlidersHorizontal}
          title="AI Profile Recommendations"
          subtitle="Every recommendation is inside an authorized profile bound and still requires deterministic validation plus explicit manual review."
        />
        <WeeklySummaryClient summary={summary} />
      </section>
    </>
  );
}
