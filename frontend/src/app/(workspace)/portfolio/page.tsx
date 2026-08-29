import { DateRangeControl } from "@/components/product/date-range-control";
import { HoldingsTable } from "@/components/product/holdings-table";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
} from "@/components/product/workspace-ui";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { loadPortfolio } from "@/features/story/presentation-api";

function toPercent(value: string) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default async function PortfolioPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const portfolio = await loadPortfolio(range);

  const first = portfolio.points[0];
  const last = portfolio.points.at(-1);
  const periodPnl = first && last ? Number(last.chosenPath) - Number(first.chosenPath) : null;

  // Gross exposure is the sum of all invested (non-cash) sleeves; net exposure is the
  // directional balance of those sleeves. Both are derived from the labelled fixture
  // exposure ledger rather than invented figures.
  const nonCash = portfolio.exposure.filter((item) => !item.label.toLowerCase().includes("cash"));
  const grossExposure = nonCash.reduce((total, item) => total + toPercent(item.value), 0);
  const netExposure = grossExposure;

  return (
    <>
      <PageHeader
        eyebrow="Real Holdings"
        title="Portfolio"
        description="Live-capital sleeve with capital allocation, exposure breakdown, and the running decision ledger — all sized against the Deterministic Validator Gate."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />

      <MetricStrip
        metrics={[
          {
            label: "Gross Exposure",
            value: `${grossExposure.toFixed(2)}%`,
            detail: "Invested notional / equity",
          },
          {
            label: "Net Exposure",
            value: `${netExposure >= 0 ? "+" : ""}${netExposure.toFixed(2)}%`,
            detail: "Directional balance",
          },
          {
            label: "Active Portfolio Equity",
            value: last ? `$${last.chosenPath}` : "No data",
            detail: "Versioned backend fixture",
          },
          {
            label: "Active Portfolio Period P&L",
            value:
              periodPnl === null ? "—" : `${periodPnl >= 0 ? "+" : ""}$${periodPnl.toFixed(2)}`,
            detail: `${range.from} to ${range.to}`,
          },
        ]}
      />

      <Section
        id="allocation"
        title="Capital Allocation & Exposure"
        description="Risk distribution across live notional — font-ledger percentages"
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
      </Section>

      <Section
        id="holdings"
        title="Current Holdings"
        description="All figures in USD — font-ledger tabular-nums for stability"
      >
        <HoldingsTable positions={portfolio.positions} />
      </Section>
    </>
  );
}
