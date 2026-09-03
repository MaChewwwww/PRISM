import { Activity, PieChart, Wallet } from "lucide-react";

import { HoldingsTable } from "@/features/portfolio/holdings-table";
import { PageHeader } from "@/components/workspace/workspace-ui";
import { PaginatedList } from "@/components/workspace/paginated-list";
import { RangePresets } from "@/components/workspace/range-presets";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { formatDateTime } from "@/features/story/formatters";
import { loadPortfolio } from "@/features/story/monitoring-api";

function toPercent(value: string) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function amountTone(amount: string) {
  if (amount.startsWith("+")) return "text-[#00D084]";
  if (amount.startsWith("-")) return "text-[#FF6B6B]";
  return "text-[#94A3B8]";
}

const METRIC_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]";

// Section container card matching the Gross Exposure metric card (glass, no hover glow).
const SECTION_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl";

/** Section heading rendered above the card: icon + title + subtitle, left aligned. */
function SectionHeading({
  id,
  icon: Icon,
  title,
  subtitle,
}: {
  id: string;
  icon: typeof Activity;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4">
      <h2
        id={id}
        className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
      >
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        {title}
      </h2>
      <p className="mt-1 text-[12px] text-[#64748B]">{subtitle}</p>
    </div>
  );
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

  // Directional net exposure and gross exposure from server-calculated portfolio metrics.
  const nonCash = portfolio.exposure.filter(
    (item) => !item.label.toLowerCase().includes("cash") && !item.label.toLowerCase().includes("net"),
  );
  const grossExposure = nonCash.reduce((total, item) => total + toPercent(item.value), 0);
  const netExposureItem = portfolio.exposure.find((item) =>
    item.label.toLowerCase().includes("net"),
  );
  const netExposure = netExposureItem ? toPercent(netExposureItem.value) : grossExposure;

  return (
    <>
      <PageHeader
        eyebrow="Active Portfolio"
        title="Portfolio"
        description="Track active positions, allocation, and risk exposure."
      >
        <RangePresets range={range} />
      </PageHeader>

      {/* Metric cards — individual glass cards (DESIGN.md Section 5.2 glass) */}
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className={METRIC_CARD}>
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Gross Exposure
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#F8FAFC]">
            {grossExposure.toFixed(2)}%
          </dd>
          <p className="mt-1 text-[11px] text-[#64748B]"> Overall Market Exposure</p>
        </div>
        <div className={METRIC_CARD}>
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Net Exposure
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#F8FAFC]">
            {netExposure.toFixed(2)}%
          </dd>
          <p className="mt-1 text-[11px] text-[#64748B]">Overall Directional Exposure</p>
        </div>
        <div className={METRIC_CARD}>
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Portfolio Equity
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#00D084]">
            {last ? `$${last.chosenPath}` : (portfolio.positions[0]?.value ?? "$100,000.00")}
          </dd>
          <p className="mt-1 text-[11px] text-[#64748B]">Current Portfolio Value</p>
        </div>
        <div className={METRIC_CARD}>
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Profit and loss this period
          </dt>
          <dd
            className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${
              periodPnl === null
                ? "text-[#64748B]"
                : periodPnl >= 0
                  ? "text-[#00D084]"
                  : "text-[#FF6B6B]"
            }`}
          >
            {periodPnl === null ? "—" : `${periodPnl >= 0 ? "+" : ""}$${periodPnl.toFixed(2)}`}
          </dd>
          <p className="mt-1 text-[11px] text-[#64748B]">
            {range.from} to {range.to}
          </p>
        </div>
      </dl>

      <section aria-labelledby="operational-evidence" className="mt-6">
        <SectionHeading
          id="operational-evidence"
          icon={Activity}
          title="Evidence & Checks"
          subtitle="Latest data and exit-check status."
        />
        <div className={`${SECTION_CARD} divide-y divide-white/8`}>
          {(portfolio.operationalEvidence ?? []).map((item) => (
            <div
              key={item.label}
              className="flex flex-wrap items-baseline justify-between gap-3 p-4"
            >
              <span className="text-sm text-[#CBD5E1]">{item.label}</span>
              <span className="font-mono text-xs text-[#94A3B8]">{item.value}</span>
              <span className="state-badge" data-state={item.status}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Capital Allocation & Exposure */}
      <section aria-labelledby="allocation" className="mt-6">
        <SectionHeading
          id="allocation"
          icon={PieChart}
          title="Portfolio Allocation & Exposure"
          subtitle="Current exposure across positions, spreads, and cash."
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <ul className="space-y-5">
            {portfolio.exposure.map((item) => {
              const pct = toPercent(item.value);
              return (
                <li key={item.label}>
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-[14px] text-[#CBD5E1]">{item.label}</span>
                    <span className="text-[14px] font-semibold tabular-nums text-[#CBD5E1]">
                      {item.value}%
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/8">
                    <div
                      className="h-full rounded-full bg-[#547D83] transition-all duration-500"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* Current Holdings */}
      <section aria-labelledby="holdings" className="mt-6">
        <SectionHeading
          id="holdings"
          icon={Wallet}
          title="Current Holdings"
          subtitle="Active positions and current market values."
        />
        <div className={SECTION_CARD}>
          <HoldingsTable positions={portfolio.positions} />
        </div>
      </section>

      {/* Active Portfolio Decision Activity */}
      <section aria-labelledby="activity" className="mt-6">
        <SectionHeading
          id="activity"
          icon={Activity}
          title="Recent Activity"
          subtitle="Latest portfolio decisions and capital movements."
        />
        {portfolio.activities.length === 0 ? (
          <div className={SECTION_CARD}>
            <p className="inline-empty m-5 sm:m-6">No decision activity falls inside this range.</p>
          </div>
        ) : (
          <PaginatedList
            items={portfolio.activities}
            itemLabel="events"
            getKey={(activity) => `${activity.occurredAt}-${activity.label}`}
            className={`${SECTION_CARD} overflow-hidden`}
            renderItem={(activity) => (
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] items-center gap-4 px-5 py-3.5 not-last:border-b not-last:border-white/8 sm:px-6">
                <time
                  dateTime={activity.occurredAt}
                  className="font-mono text-[13px] tabular-nums text-[#64748B]"
                >
                  {formatDateTime(activity.occurredAt)}
                </time>
                <span className="text-[14px] text-[#CBD5E1]">{activity.label}</span>
                <span
                  className={`text-right text-[14px] font-semibold tabular-nums ${amountTone(activity.amount)}`}
                >
                  {activity.amount}
                </span>
              </div>
            )}
          />
        )}
      </section>
    </>
  );
}
