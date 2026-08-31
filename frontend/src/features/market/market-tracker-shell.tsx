"use client";

import {
  BarChart3,
  CandlestickChart,
  Check,
  Database,
  Filter,
  Layers,
  LineChart,
  ListChecks,
  LockKeyhole,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import { useMemo, useState } from "react";

import { ProvenanceLabel } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import type { DateRange } from "@/features/story/date-range";
import {
  isVerifiedTrade,
  marketActivityKinds,
  marketTimeframes,
  type MarketActivityKind,
  type MarketTimeframe,
} from "@/features/market/market-tracker-types";

const allActivityKinds = marketActivityKinds.map(({ id }) => id) as MarketActivityKind[];

export function MarketTrackerShell({ range }: { range: DateRange }) {
  const [selectedActivities, setSelectedActivities] = useState<Set<MarketActivityKind>>(
    () => new Set(allActivityKinds),
  );
  const [timeframe, setTimeframe] = useState<MarketTimeframe>("1Day");
  const [tradedOnly, setTradedOnly] = useState(false);

  const selectedCount = selectedActivities.size;
  const selectedLabels = useMemo(
    () => marketActivityKinds.filter(({ id }) => selectedActivities.has(id)),
    [selectedActivities],
  );

  function toggleActivity(kind: MarketActivityKind) {
    setSelectedActivities((current) => {
      const next = new Set(current);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  function selectAllActivities() {
    setSelectedActivities(new Set(allActivityKinds));
  }

  function clearActivities() {
    setSelectedActivities(new Set());
  }

  return (
    <div className="mt-6 space-y-6">
      {/* Deferred-integration notice */}
      <div className="flex items-start gap-3 rounded-xl border border-[#818CF8]/30 bg-[#818CF8]/10 p-4">
        <span
          aria-hidden="true"
          className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]"
        >
          <Radio className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <strong className="block text-[14px] font-semibold text-[#F8FAFC]">
            Market data integration is deferred
          </strong>
          <p className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
            This workspace reserves the chart, watchlist, and activity overlays for a future
            authenticated server adapter. No market, account, order, or provider data is loaded.
          </p>
        </div>
        <ProvenanceLabel provenance="planned_integration" />
      </div>

      {/* Toolbar: symbol / timeframe / feed */}
      <div
        className={`${SECTION_CARD} grid grid-cols-1 gap-5 p-5 sm:p-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1.4fr)_minmax(0,1fr)]`}
        aria-label="Market tracker controls"
      >
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Symbol
          </span>
          <span className="relative">
            <input
              type="text"
              placeholder="Symbols load from the server"
              disabled
              aria-describedby="market-tracker-symbol-help"
              className="w-full cursor-not-allowed rounded-md border border-white/8 bg-white/5 px-3 py-2 text-[13px] text-[#94A3B8] placeholder:text-[#64748B]"
            />
            <LockKeyhole
              className="pointer-events-none absolute top-1/2 right-3 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]"
              aria-hidden="true"
            />
          </span>
          <small id="market-tracker-symbol-help" className="text-[11px] text-[#64748B]">
            Symbol search becomes available with the market adapter.
          </small>
        </label>

        <fieldset className="flex flex-col gap-1.5">
          <legend className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Timeframe
          </legend>
          <div
            role="group"
            aria-label="Chart timeframe"
            className="inline-flex flex-wrap items-center gap-1 rounded-full border border-white/8 bg-white/5 p-1"
          >
            {marketTimeframes.map((value) => {
              const isActive = timeframe === value;
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => setTimeframe(value)}
                  className="rounded-full px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83]"
                  style={{
                    color: isActive ? "#B2D8DC" : "#64748B",
                    background: isActive ? "rgba(84,125,131,0.2)" : "transparent",
                  }}
                >
                  {value}
                </button>
              );
            })}
          </div>
          <small className="text-[11px] text-[#64748B]">
            Default: {timeframe}. Values appear after integration.
          </small>
        </fieldset>

        <div className="flex items-start gap-2.5" role="note">
          <Database className="mt-0.5 h-4 w-4 shrink-0 text-[#547D83]" aria-hidden="true" />
          <span>
            <strong className="block text-[13px] font-semibold text-[#F8FAFC]">Feed</strong>
            <small className="text-[11px] text-[#64748B]">Server entitlement (planned)</small>
          </span>
        </div>
      </div>

      {/* Activity overlays */}
      <section aria-labelledby="market-tracker-activity-heading">
        <SectionHeading
          id="market-tracker-activity-heading"
          icon={Layers}
          title="Activity Overlays"
          subtitle="Choose which future PRISM and Alpaca events may appear over the price timeline. Controls are local-only until the server endpoint is authorized."
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 pb-4">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-[#CBD5E1]">
              <Filter className="h-3.5 w-3.5 text-[#64748B]" aria-hidden="true" />
              {selectedCount} of {marketActivityKinds.length} categories selected
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={selectAllActivities}
                aria-pressed={selectedCount === marketActivityKinds.length}
                className="inline-flex items-center gap-1.5 rounded-md border border-white/8 bg-white/5 px-2.5 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                <Check className="h-3.5 w-3.5" aria-hidden="true" /> Select all
              </button>
              <button
                type="button"
                onClick={clearActivities}
                aria-pressed={selectedCount === 0}
                className="rounded-md border border-white/8 bg-white/5 px-2.5 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                Clear all
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Activity categories">
            {marketActivityKinds.map(({ id, label, description, color }) => {
              const selected = selectedActivities.has(id);
              return (
                <button
                  key={id}
                  type="button"
                  data-selected={selected}
                  aria-pressed={selected}
                  aria-label={`${label}: ${description}`}
                  onClick={() => toggleActivity(id)}
                  className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83]"
                  style={{
                    color: selected ? "#F8FAFC" : "#64748B",
                    borderColor: selected ? `${color}66` : "rgba(255,255,255,0.08)",
                    background: selected ? `${color}1f` : "transparent",
                  }}
                >
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 rounded-full"
                    style={{ background: color }}
                  />
                  {label}
                </button>
              );
            })}
          </div>

          <label className="mt-5 flex cursor-pointer items-start gap-3 border-t border-white/8 pt-4">
            <input
              type="checkbox"
              checked={tradedOnly}
              onChange={(event) => setTradedOnly(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[#547D83]"
            />
            <span>
              <strong className="block text-[13px] font-semibold text-[#F8FAFC]">
                Symbols with verified trades only
              </strong>
              <small className="text-[12px] leading-relaxed text-[#94A3B8]">
                Future filter: only symbols with confirmed{" "}
                <code className="rounded bg-white/5 px-1 font-mono text-[11px]">fill</code> activity
                qualify. Proposals, NO_TRADE, and ShadowFund events never count as trades.
              </small>
            </span>
          </label>

          {selectedCount > 0 && (
            <p className="mt-4 text-[12px] text-[#64748B]" aria-live="polite">
              Showing future overlays for {selectedLabels.map(({ label }) => label).join(", ")}.
            </p>
          )}
        </div>
      </section>

      {/* Chart + watchlist */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section aria-labelledby="market-tracker-chart-heading">
          <SectionHeading
            id="market-tracker-chart-heading"
            icon={CandlestickChart}
            title="Price and Activity Timeline"
            subtitle="Candlestick and volume layers are reserved for normalized server bars."
          />
          <div className={`${SECTION_CARD} overflow-hidden`}>
            <div
              className="relative grid min-h-80 place-items-center p-6"
              aria-label="Market chart awaiting integration"
            >
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 opacity-40"
                style={{
                  backgroundImage:
                    "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
                  backgroundSize: "44px 44px",
                }}
              />
              <div className="relative flex flex-col items-center gap-2 text-center">
                <CandlestickChart className="h-8 w-8 text-[#64748B]" aria-hidden="true" />
                <strong className="text-[15px] font-semibold text-[#F8FAFC]">
                  No market bars available
                </strong>
                <span className="max-w-sm text-[13px] leading-relaxed text-[#94A3B8]">
                  Connect the authenticated server market adapter to render OHLCV, volume, and
                  activity markers.
                </span>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/8 px-5 py-3 font-mono text-[11px] text-[#64748B]">
              <span className="inline-flex items-center gap-1.5">
                <CandlestickChart className="h-3.5 w-3.5" aria-hidden="true" /> OHLCV / volume
                reserved
              </span>
              <span className="inline-flex items-center gap-1.5">
                <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />{" "}
                {tradedOnly ? "Verified fills only" : "All selected activities"}
              </span>
            </div>
          </div>
        </section>

        <section aria-labelledby="market-tracker-watchlist-heading">
          <SectionHeading
            id="market-tracker-watchlist-heading"
            icon={LineChart}
            title="Watchlist"
            subtitle="Future snapshots will populate this list without exposing provider credentials."
          />
          <div className={`${SECTION_CARD} grid min-h-80 place-items-center p-6`}>
            <div className="flex flex-col items-center gap-2 text-center">
              <SlidersHorizontal className="h-7 w-7 text-[#64748B]" aria-hidden="true" />
              <strong className="text-[15px] font-semibold text-[#F8FAFC]">
                No symbols loaded
              </strong>
              <p className="max-w-xs text-[13px] leading-relaxed text-[#94A3B8]">
                Watchlist snapshots are unavailable until the server-side integration is enabled.
              </p>
              <span className="text-[11px] text-[#64748B]">
                No symbols, prices, positions, or fills are being represented.
              </span>
            </div>
          </div>
        </section>
      </div>

      {/* Activity legend */}
      <section aria-labelledby="market-tracker-legend-heading">
        <SectionHeading
          id="market-tracker-legend-heading"
          icon={ListChecks}
          title="Activity Legend"
          subtitle="Only confirmed fills qualify as actual trades. Every other category remains a distinct research, decision, order, or simulation event."
        />
        <ul
          className={`${SECTION_CARD} grid grid-cols-1 gap-x-6 gap-y-2 p-5 sm:grid-cols-2 lg:grid-cols-3`}
        >
          {marketActivityKinds.map(({ id, label, color }) => {
            const selected = selectedActivities.has(id);
            return (
              <li
                key={id}
                className="flex items-center gap-2.5 text-[13px]"
                style={{ opacity: selected ? 1 : 0.5 }}
              >
                <span
                  aria-hidden="true"
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: color }}
                />
                <span className="text-[#CBD5E1]">{label}</span>
                {isVerifiedTrade(id) && (
                  <small className="rounded border border-[#00D084]/30 bg-[#00D084]/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-[#00D084]">
                    actual trade
                  </small>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <p className="text-[12px] text-[#64748B]">
        Requested UTC range:{" "}
        <code className="rounded bg-white/5 px-1 font-mono text-[11px] text-[#CBD5E1]">
          {range.from}
        </code>{" "}
        to{" "}
        <code className="rounded bg-white/5 px-1 font-mono text-[11px] text-[#CBD5E1]">
          {range.to}
        </code>
        . The shared URL range is preserved for the future endpoint.
      </p>
    </div>
  );
}
