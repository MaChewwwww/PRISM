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
import { formatTokens } from "@/features/story/formatters";
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
  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="What happened, and what could improve"
        description="Read the period as one connected story across catalysts, agent decisions, governed outcomes, and simulated alternatives."
      >
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" /> Paper only
        </div>
      </PageHeader>
      <DemoDataNotice />
      <DateRangeControl range={range} />

      <section className="period-lead" aria-labelledby="period-story-title">
        <div>
          <p className="eyebrow">
            Period story · {range.from} to {range.to}
          </p>
          <h2 id="period-story-title">
            {dashboard.stories.length > 0
              ? `${dashboard.stories.length} governed decisions left a clearer trail than a trade blotter alone.`
              : "This range contains no decision stories yet."}
          </h2>
        </div>
        <p>
          {alternativeLead > 0
            ? `The strongest simulated portfolio finished $${alternativeLead.toFixed(2)} ahead of the illustrative paper path. That difference is a review signal, not an executable recommendation.`
            : "No simulated branch finished ahead of the illustrative paper path in the selected observations."}
        </p>
      </section>

      <MetricStrip
        metrics={[
          {
            label: "Illustrative equity",
            value: lastPoint ? `$${lastPoint.actual}` : "No observations",
            detail: "Paper-shaped fixture",
          },
          {
            label: "Period change",
            value:
              firstPoint && lastPoint
                ? `$${(Number(lastPoint.actual) - Number(firstPoint.actual)).toFixed(2)}`
                : "—",
            detail: "Exact fixture endpoints",
          },
          {
            label: "Decision stories",
            value: String(dashboard.stories.length),
            detail: "Including no-trade outcomes",
          },
          {
            label: "Agent tokens",
            value: formatTokens(dashboard.tokenTotal),
            detail: "Input + output + cached",
          },
        ]}
      />

      <Section
        id="portfolio-path"
        title="Portfolio path"
        description="Did the illustrative paper path keep pace with the strongest ShadowFund portfolio?"
      >
        <StoryLineChart
          title="Actual-shaped equity versus best alternative"
          description="Solid is the illustrative paper account; dashed is simulated and cannot execute."
          summary={
            alternativeLead > 0
              ? `Alternative lead: $${alternativeLead.toFixed(2)}`
              : "Paper path leads in this range"
          }
          data={dashboard.portfolio.points}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Illustrative paper", color: "var(--primary)" },
            {
              key: "alternative",
              label: "Best simulated branch",
              color: "var(--alternative)",
              dashed: true,
            },
            {
              key: "benchmark",
              label: "Synthetic benchmark",
              color: "var(--benchmark)",
              dashed: true,
            },
          ]}
        />
      </Section>

      <div className="dashboard-pair">
        <Section
          id="decision-outcomes"
          title="Decision outcomes"
          description="No-trade and fail-closed results count as successful governed conclusions."
        >
          <StoryBarChart
            title="Outcomes in the selected period"
            description="Count of fixed fictional stories by terminal state."
            summary={`${dashboard.stories.length} total stories`}
            data={dashboard.outcomes}
          />
        </Section>
        <Section
          id="exposure"
          title="Current illustrative exposure"
          description="A simple allocation view; the numbers are not a live account or approved limits."
        >
          <div className="exposure-list">
            {dashboard.portfolio.exposure.map((item) => (
              <div key={item.label}>
                <div>
                  <span>{item.label}</span>
                  <strong>{item.value}%</strong>
                </div>
                <span className="exposure-track">
                  <span style={{ width: `${item.value}%` }} />
                </span>
              </div>
            ))}
          </div>
          <Link
            className="text-link"
            href={`/portfolio?range=${range.preset}&from=${range.from}&to=${range.to}`}
          >
            Compare portfolios <ArrowRight aria-hidden="true" />
          </Link>
        </Section>
      </div>

      <Section
        id="latest-stories"
        title="Latest decision stories"
        description="Each story keeps evidence, agent summaries, deterministic governance, outcomes, and alternatives together."
      >
        <StoryList stories={dashboard.stories.slice(0, 3)} />
        <Link
          className="text-link section-link"
          href={`/stories?range=${range.preset}&from=${range.from}&to=${range.to}`}
        >
          Browse all stories <ArrowRight aria-hidden="true" />
        </Link>
      </Section>

      <Section
        id="improvements"
        title="What could be better"
        description="Illustrative review prompts from completed and stopped workflows; none change rules or profiles."
      >
        <ol className="improvement-list">
          {dashboard.recommendations.map((recommendation, index) => (
            <li key={recommendation}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <p>{recommendation}</p>
            </li>
          ))}
        </ol>
      </Section>
    </>
  );
}
