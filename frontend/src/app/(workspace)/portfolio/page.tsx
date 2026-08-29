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
        eyebrow="Active Portfolio & Shadow Analytics"
        title="Active Paper Account vs. Shadow Multiverse"
        description="Monitor active Alpaca paper trading positions, capital utilization, and counterfactual branch performance over shared date ranges."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <MetricStrip
        metrics={[
          {
            label: "Active Equity",
            value: last ? `$${last.actual}` : "No data",
            detail: "Alpaca paper trading",
          },
          {
            label: "Active Period P&L",
            value:
              paperChange === null
                ? "—"
                : `${paperChange >= 0 ? "+" : ""}$${paperChange.toFixed(2)}`,
            detail: `${range.from} to ${range.to}`,
          },
          {
            label: "Best Shadow Delta",
            value:
              alternativeDelta === null
                ? "—"
                : `${alternativeDelta >= 0 ? "+" : ""}$${alternativeDelta.toFixed(2)}`,
            detail: "Shadow vs. Active",
          },
          { label: "Cash Buffer", value: "94.7%", detail: "$98,352.48 available" },
        ]}
      />

      <Section
        id="equity-comparison"
        title="Active Equity vs. Shadow Performance"
        description="Is the performance advantage persistent or concentrated around specific news catalyst events?"
      >
        <StoryLineChart
          title="Portfolio Equity Trajectory"
          description="Interactive multi-branch trajectory. Click any trajectory button to toggle individual shadow branches on or off."
          summary={
            alternativeDelta !== null && alternativeDelta > 0
              ? `Shadow Portfolio ahead by +$${alternativeDelta.toFixed(2)}`
              : "Active Portfolio leads in this period"
          }
          data={portfolio.points}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Active Portfolio (Paper)", color: "#547D83" },
            {
              key: "agentAlternative",
              label: "Shadow: Agent Counterfactual",
              color: "#818CF8",
              dashed: true,
            },
            {
              key: "reducedSize",
              label: "Shadow: Reduced Sizing",
              color: "#34D399",
              dashed: true,
            },
            {
              key: "unhedged",
              label: "Shadow: Unhedged Structure",
              color: "#FB923C",
              dashed: true,
            },
            {
              key: "cashBaseline",
              label: "Shadow: Cash Baseline",
              color: "#94A3B8",
              dashed: true,
            },
            {
              key: "benchmark",
              label: "Market Benchmark",
              color: "#38BDF8",
              dashed: true,
            },
          ]}
        />
      </Section>

      <div className="dashboard-pair portfolio-pair">
        <Section
          id="holdings"
          title="Active Paper Holdings"
          description="Open contract positions, option spreads, and cash reserves in the active paper account."
        >
          <div className="holding-list">
            {portfolio.positions.map((position) => (
              <div
                key={position.symbol}
                className="prism-glass-card p-4 transition-all hover:border-[#547D83]/40"
              >
                <div>
                  <strong className="text-white font-medium">{position.symbol}</strong>
                  <span className="text-xs text-[#547D83] font-semibold">
                    {position.provenance}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>Allocation</dt>
                    <dd className="font-mono tabular-nums">{position.allocation}</dd>
                  </div>
                  <div>
                    <dt>Value</dt>
                    <dd className="font-mono tabular-nums">{position.value}</dd>
                  </div>
                  <div>
                    <dt>P&amp;L</dt>
                    <dd
                      className={`font-mono tabular-nums font-semibold ${position.pnl.startsWith("+") ? "text-[#00D084]" : position.pnl.startsWith("-") ? "text-[#FF6B6B]" : "text-slate-300"}`}
                    >
                      {position.pnl}
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </Section>
        <Section
          id="allocation"
          title="Capital Allocation & Exposure"
          description="Proportional capital exposure across cash buffer and defined-risk option debit spreads."
        >
          <div className="exposure-list">
            {portfolio.exposure.map((item) => (
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
            href={`/alternatives?range=${range.preset}&from=${range.from}&to=${range.to}`}
          >
            Explore ShadowFund Alternative Sessions <ArrowRight aria-hidden="true" />
          </Link>
        </Section>
      </div>

      <Section
        id="portfolio-activity"
        title="Governed Execution Activity"
        description="Decision-linked events and paper order fills during the selected period."
      >
        {portfolio.activities.length > 0 ? (
          <ol className="activity-list">
            {portfolio.activities.map((activity) => (
              <li
                key={activity.occurredAt}
                className="prism-glass-card p-3 my-2 flex items-center justify-between"
              >
                <time dateTime={activity.occurredAt} className="text-xs text-slate-400 font-mono">
                  {formatDateTime(activity.occurredAt)}
                </time>
                <div>
                  <strong className="text-sm text-white block">{activity.label}</strong>
                  <span className="text-xs text-slate-300">{activity.detail}</span>
                </div>
                <b
                  className={`font-mono tabular-nums text-sm ${activity.amount.startsWith("+") ? "text-[#00D084]" : "text-slate-300"}`}
                >
                  {activity.amount}
                </b>
              </li>
            ))}
          </ol>
        ) : (
          <p className="inline-empty">No active portfolio activity falls inside this date range.</p>
        )}
      </Section>
    </>
  );
}
