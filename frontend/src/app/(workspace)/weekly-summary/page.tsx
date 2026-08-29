import { BookOpenCheck, ShieldCheck, TrendingUp } from "lucide-react";
import Link from "next/link";

import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
} from "@/components/product/workspace-ui";
import { getWeeklySummary } from "@/features/story/story-data";

import { WeeklySummaryClient } from "./weekly-summary-client";

export default function WeeklySummaryPage() {
  const summary = getWeeklySummary();

  return (
    <>
      <PageHeader
        eyebrow={`Week of ${summary.weekOf}`}
        title="Weekly Post-Analysis"
        description="AI reviews the week's decision stories, shadow-fund branch outcomes, and rule performance — then surfaces calibration suggestions for your next draft ruleset."
      >
        <div className="mode-stamp">
          <TrendingUp aria-hidden="true" /> Post-analysis
        </div>
      </PageHeader>
      <DemoDataNotice />

      {/* Week at a glance */}
      <MetricStrip
        metrics={[
          {
            label: "Stories analysed",
            value: String(summary.storiesAnalysed),
            detail: `Week of ${summary.weekOf}`,
          },
          {
            label: "Net active P&L",
            value: summary.netPnl,
            detail: "Governed paper execution",
          },
          {
            label: "Shadow beat active",
            value: `${summary.shadowBeatActive} / ${summary.storiesAnalysed}`,
            detail: "Branches that outperformed",
          },
          {
            label: "Suggestions pending",
            value: String(summary.suggestions.length),
            detail: "AI rule calibrations",
          },
        ]}
      />

      {/* AI key findings */}
      <Section
        id="ai-findings"
        title="AI Analysis — Key Findings"
        description="Vela post-analysis perspective synthesised from this week's decision stories and shadow-fund branch comparisons."
      >
        <ul className="weekly-findings-list">
          {summary.keyFindings.map((finding, i) => (
            <li key={i} className="weekly-finding-item">
              <span className="weekly-finding-index" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <p>{finding}</p>
            </li>
          ))}
        </ul>
        <div className="inspector-note">
          <ShieldCheck aria-hidden="true" />
          <p>
            This analysis is produced by the illustrative Vela agent from fixture data. It cannot
            authorise, submit, or modify any order or ruleset directly.
          </p>
        </div>
      </Section>

      {/* Interactive calibration section */}
      <Section
        id="calibration"
        title="Rule Calibration Suggestions"
        description="Each suggestion targets a specific configurable rule. Review the rationale, then accept or dismiss individually (Manual), or stage all at once (Auto-calibration)."
      >
        <WeeklySummaryClient summary={summary} />
      </Section>

      {/* Link to rules */}
      <div className="weekly-rules-link prism-glass-card">
        <BookOpenCheck aria-hidden="true" className="text-[#547D83]" />
        <div>
          <strong>Ready to configure?</strong>
          <p>
            Staged suggestions become draft fields in the Rules page. No suggestion can activate
            without an explicit approval.
          </p>
        </div>
        <Link href="/rules" className="primary-action">
          Go to Business Rules →
        </Link>
      </div>
    </>
  );
}
