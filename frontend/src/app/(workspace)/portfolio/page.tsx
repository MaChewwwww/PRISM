import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import { StoryLineChart } from "@/components/product/story-charts";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
} from "@/components/product/workspace-ui";
import { formatDateTime } from "@/features/story/formatters";
import { loadPortfolio, readDateRange, type SearchValues } from "@/features/story/story-data";

export default async function PortfolioPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const portfolio = loadPortfolio(range);
  const first = portfolio.points[0];
  const last = portfolio.points.at(-1);
  const paperChange = first && last ? Number(last.actual) - Number(first.actual) : null;
  const alternativeDelta = last
    ? Number(last.alternative ?? last.actual) - Number(last.actual)
    : null;

  return (
    <>
      <PageHeader
        eyebrow="Portfolio"
        title="One paper path, several ways to learn from it"
        description="Compare the illustrative paper account with ShadowFund alternatives over a shared date range."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <MetricStrip
        metrics={[
          {
            label: "Illustrative equity",
            value: last ? `$${last.actual}` : "No observations",
            detail: "Not a live account",
          },
          {
            label: "Period change",
            value: paperChange === null ? "—" : `$${paperChange.toFixed(2)}`,
            detail: `${range.from} to ${range.to}`,
          },
          {
            label: "Best branch delta",
            value: alternativeDelta === null ? "—" : `$${alternativeDelta.toFixed(2)}`,
            detail: "Simulated versus paper-shaped",
          },
          { label: "Cash allocation", value: "94.7%", detail: "Fictional snapshot" },
        ]}
      />

      <Section
        id="equity-comparison"
        title="Equity comparison"
        description="Is the difference persistent, or concentrated around a few decisions?"
      >
        <StoryLineChart
          title="Portfolio equity"
          description="Exact values are fixed decimal strings; plotting conversion is presentation-only."
          summary={
            alternativeDelta !== null && alternativeDelta > 0
              ? `Best branch ahead by $${alternativeDelta.toFixed(2)}`
              : "No alternative lead in this range"
          }
          data={portfolio.points}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Illustrative paper", color: "var(--primary)" },
            {
              key: "alternative",
              label: "Best ShadowFund",
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

      <div className="dashboard-pair portfolio-pair">
        <Section
          id="holdings"
          title="Illustrative holdings"
          description="Fictional positions reserve the structure for future normalized portfolio data."
        >
          <div className="holding-list">
            {portfolio.positions.map((position) => (
              <div key={position.symbol}>
                <div>
                  <strong>{position.symbol}</strong>
                  <span>{position.provenance}</span>
                </div>
                <dl>
                  <div>
                    <dt>Allocation</dt>
                    <dd>{position.allocation}</dd>
                  </div>
                  <div>
                    <dt>Value</dt>
                    <dd>{position.value}</dd>
                  </div>
                  <div>
                    <dt>P&amp;L</dt>
                    <dd>{position.pnl}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </Section>
        <Section
          id="allocation"
          title="Exposure mix"
          description="A proportional view without presenting demo numbers as policy thresholds."
        >
          <div className="exposure-list">
            {portfolio.exposure.map((item) => (
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
            href={`/alternatives?range=${range.preset}&from=${range.from}&to=${range.to}`}
          >
            Open ShadowFund comparisons <ArrowRight aria-hidden="true" />
          </Link>
        </Section>
      </div>

      <Section
        id="portfolio-activity"
        title="What changed in the period"
        description="Decision-linked activity is more useful here than an undifferentiated order log."
      >
        {portfolio.activities.length > 0 ? (
          <ol className="activity-list">
            {portfolio.activities.map((activity) => (
              <li key={activity.occurredAt}>
                <time dateTime={activity.occurredAt}>{formatDateTime(activity.occurredAt)}</time>
                <div>
                  <strong>{activity.label}</strong>
                  <span>{activity.detail}</span>
                </div>
                <b>{activity.amount}</b>
              </li>
            ))}
          </ol>
        ) : (
          <p className="inline-empty">
            No illustrative portfolio activity falls inside this range.
          </p>
        )}
      </Section>
    </>
  );
}
