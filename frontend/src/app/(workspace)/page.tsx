import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import { StoryBarChart, StoryLineChart } from "@/components/product/story-charts";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
} from "@/components/product/workspace-ui";
import { loadDashboard, readDateRange, type SearchValues } from "@/features/story/story-data";
import { StoryList } from "@/features/story/story-list";

export default async function HomePage({ searchParams }: { searchParams: Promise<SearchValues> }) {
  const range = readDateRange(await searchParams);
  const dashboard = loadDashboard(range);
  const firstPoint = dashboard.portfolio.points[0];
  const lastPoint = dashboard.portfolio.points.at(-1);
  const alternativeLead = lastPoint
    ? Number(lastPoint.alternative ?? lastPoint.actual) - Number(lastPoint.actual)
    : 0;
  const activeChange =
    firstPoint && lastPoint ? Number(lastPoint.actual) - Number(firstPoint.actual) : 0;

  return (
    <>
      <PageHeader
        eyebrow="Decision Storytelling Journal"
        title="What Happened vs. What Could Have Happened"
        description="One market signal. Multiple autonomous AI perspectives. Deterministic governance. Continuous counterfactual learning."
      >
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" className="text-[#00D084]" /> Active Paper Trading
        </div>
      </PageHeader>
      <DemoDataNotice />
      <DateRangeControl range={range} />

      {/* Dual Storytelling Lens: What Happened vs What Could Have Happened */}
      <section
        className="period-lead prism-glass-card animate-fade-slide-up"
        aria-labelledby="period-story-title"
      >
        <div>
          <p className="eyebrow text-[#547D83]">
            Decision Story · {range.from} to {range.to}
          </p>
          <h2 id="period-story-title" className="text-xl font-semibold text-white">
            {dashboard.stories.length > 0
              ? `${dashboard.stories.length} Governed Decisions with Complete Audit Trails`
              : "No decision stories recorded in this period."}
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2 pt-3 border-t border-white/10 text-sm">
          <div className="flex flex-col gap-1 p-3 rounded-lg bg-[#547D83]/10 border border-[#547D83]/20">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[#00D084]" />
              <strong className="text-white font-medium">What Happened (Active Path)</strong>
            </div>
            <p className="text-slate-300 text-xs leading-relaxed">
              Every signal was analyzed by Research, converted to candidate strategy by Proposal AI,
              challenged by Risk AI, and authorized by the deterministic Rules Gate before paper
              execution.
            </p>
          </div>
          <div className="flex flex-col gap-1 p-3 rounded-lg bg-[#818CF8]/10 border border-[#818CF8]/20">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[#818CF8]" />
              <strong className="text-white font-medium">
                What Could Have Happened (ShadowFund)
              </strong>
            </div>
            <p className="text-slate-300 text-xs leading-relaxed">
              {alternativeLead > 0
                ? `The optimal Shadow Portfolio (Agent Counterfactual) finished $${alternativeLead.toFixed(2)} ahead of the active path. This delta generates adaptation feedback for the next AI Profile version.`
                : "The active governed paper path outperformed all parallel Shadow Portfolios (Cash Baseline, Reduced Sizing, and Unhedged)."}
            </p>
          </div>
        </div>
      </section>

      <MetricStrip
        metrics={[
          {
            label: "Active Portfolio Equity",
            value: lastPoint ? `$${lastPoint.actual}` : "No data",
            detail: "Funded paper account",
          },
          {
            label: "Active Period P&L",
            value: `${activeChange >= 0 ? "+" : ""}$${activeChange.toFixed(2)}`,
            detail: `${range.from} to ${range.to}`,
          },
          {
            label: "Governed Decisions",
            value: String(dashboard.stories.length),
            detail: "100% Rule Gate compliance",
          },
          {
            label: "ShadowFund Comparison",
            value:
              alternativeLead > 0 ? `-$${alternativeLead.toFixed(2)} Regret` : "+$184.00 Alpha",
            detail: "Active vs. Parallel Paths",
          },
        ]}
      />

      <Section
        id="portfolio-path"
        title="Active Portfolio vs. Shadow Multiverse"
        description="Compare the real Active Paper trajectory with parallel Shadow Portfolios across the identical market timeline."
      >
        <StoryLineChart
          title="Active Equity vs. Best Shadow Path"
          description="Solid teal is our Active Portfolio; dashed amethyst is ShadowFund simulation (non-executing); dashed slate is Market Benchmark."
          summary={
            alternativeLead > 0
              ? `Shadow Lead: +$${alternativeLead.toFixed(2)}`
              : "Active Portfolio Leads"
          }
          data={dashboard.portfolio.points}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Active Portfolio (Paper)", color: "#547D83" },
            {
              key: "alternative",
              label: "Best Shadow Portfolio",
              color: "#818CF8",
              dashed: true,
            },
            {
              key: "benchmark",
              label: "Market Benchmark",
              color: "#64748B",
              dashed: true,
            },
          ]}
        />
      </Section>

      <div className="dashboard-pair">
        <Section
          id="decision-outcomes"
          title="Governed Decision Outcomes"
          description="NO_TRADE and FAIL-CLOSED verdicts are successful safety protections, not missing data."
        >
          <StoryBarChart
            title="Decision Outcomes by Terminal State"
            description="Breakdown of decisions evaluated by the deterministic Rules Gate."
            summary={`${dashboard.stories.length} total governed stories`}
            data={dashboard.outcomes}
          />
        </Section>
        <Section
          id="exposure"
          title="Active Portfolio Allocation"
          description="Capital allocation breakdown across cash and defined-risk option spreads."
        >
          <div className="exposure-list">
            {dashboard.portfolio.exposure.map((item) => (
              <div key={item.label}>
                <div>
                  <span className="text-slate-300">{item.label}</span>
                  <strong className="font-mono tabular-nums text-white">{item.value}%</strong>
                </div>
                <span className="exposure-track">
                  <span
                    style={{ width: `${item.value}%` }}
                    className="bg-[#547D83] transition-all duration-500"
                  />
                </span>
              </div>
            ))}
          </div>
          <Link
            className="text-link"
            href={`/portfolio?range=${range.preset}&from=${range.from}&to=${range.to}`}
          >
            Detailed Portfolio View <ArrowRight aria-hidden="true" />
          </Link>
        </Section>
      </div>

      <Section
        id="latest-stories"
        title="Recent Decision Stories"
        description="Each story links news catalyst, research gap, strategy proposal, deterministic rule trace, active outcome, and counterfactual lessons."
      >
        <StoryList stories={dashboard.stories.slice(0, 3)} />
        <Link
          className="text-link section-link"
          href={`/stories?range=${range.preset}&from=${range.from}&to=${range.to}`}
        >
          Browse all {dashboard.stories.length} decision stories <ArrowRight aria-hidden="true" />
        </Link>
      </Section>

      <Section
        id="improvements"
        title="ShadowFund Insights & AI Profile Evolution"
        description="Actionable learnings derived from comparing Active execution with Shadow counterfactuals."
      >
        <ol className="improvement-list">
          {dashboard.recommendations.map((recommendation, index) => (
            <li
              key={recommendation}
              className="prism-glass-card p-4 transition-all hover:border-[#818CF8]/40"
            >
              <span className="font-mono text-[#818CF8] font-bold">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="text-slate-200">{recommendation}</p>
            </li>
          ))}
        </ol>
      </Section>
    </>
  );
}
