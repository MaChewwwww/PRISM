import { BookOpenCheck, ShieldCheck, TrendingUp } from "lucide-react";
import Link from "next/link";

import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
} from "@/components/workspace/workspace-ui";
import { getWeeklySummary } from "@/features/story/presentation-api";

import { WeeklySummaryClient } from "./weekly-summary-client";

export default async function WeeklySummaryPage() {
  const summary = await getWeeklySummary();

  return (
    <>
      <PageHeader
        eyebrow={`Week of ${summary.weekOf}`}
        title="Weekly Post-Analysis"
        description="Post-Analysis reviews Active Portfolio decisions and ShadowFund outcomes, then recommends bounded AI Profile changes for manual review."
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
            value: String(summary.storiesAnalyzed),
            detail: `Week of ${summary.weekOf}`,
          },
          {
            label: "Active Portfolio net P&L",
            value: summary.illustrativeNetPnl,
            detail: "Versioned fixture",
          },
          {
            label: "Shadow beat chosen path",
            value: `${summary.shadowBeatChosen} / ${summary.storiesAnalyzed}`,
            detail: "Branches that outperformed",
          },
          {
            label: "Suggestions pending",
            value: String(summary.suggestions.length),
            detail: "AI Profile fields only",
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
        title="AI Profile Recommendations"
        description="Every recommendation is inside an authorized profile bound and still requires deterministic validation plus explicit manual review."
      >
        <WeeklySummaryClient summary={summary} />
      </Section>

      {/* Link to rules */}
      <div className="weekly-rules-link prism-glass-card">
        <BookOpenCheck aria-hidden="true" className="text-[#547D83]" />
        <div>
          <strong>Ready to configure?</strong>
          <p>
            The Rules page shows the active version and approved bounds. Recommendations cannot
            activate until persistence, validation, and approval APIs are implemented.
          </p>
        </div>
        <Link href="/rules" className="primary-action">
          Go to Business Rules {"->"}
        </Link>
      </div>
    </>
  );
}
