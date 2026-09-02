"use client";

import {
  CandlestickChart,
  Check,
  GitCompareArrows,
  LineChart,
  ListChecks,
  Radio,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useState } from "react";

import { SECTION_CARD } from "@/components/workspace/section-heading";
import {
  isVerifiedTrade,
  marketActivityKinds,
  marketTimeframes,
  type MarketActivityKind,
  type MarketTimeframe,
} from "@/features/market/market-tracker-types";

const allActivityKinds = marketActivityKinds.map(({ id }) => id) as MarketActivityKind[];

/** Deterministic ghost-candle heights so the skeleton renders identically each time. */
const GHOST_CANDLES = [
  { body: 40, top: 12, bottom: 10, up: true },
  { body: 54, top: 8, bottom: 14, up: false },
  { body: 30, top: 16, bottom: 8, up: true },
  { body: 66, top: 10, bottom: 12, up: true },
  { body: 44, top: 14, bottom: 18, up: false },
  { body: 58, top: 6, bottom: 10, up: true },
  { body: 34, top: 18, bottom: 8, up: false },
  { body: 72, top: 8, bottom: 14, up: true },
  { body: 48, top: 12, bottom: 20, up: false },
  { body: 38, top: 10, bottom: 12, up: true },
  { body: 62, top: 14, bottom: 8, up: true },
  { body: 32, top: 16, bottom: 16, up: false },
  { body: 50, top: 10, bottom: 10, up: false },
  { body: 68, top: 8, bottom: 12, up: true },
  { body: 42, top: 14, bottom: 14, up: false },
  { body: 56, top: 10, bottom: 8, up: true },
];

/** What the surface will render once a verified feed is connected. */
const CONNECT_ITEMS = [
  { icon: CandlestickChart, text: "Normalized price / candlestick data" },
  { icon: ShieldCheck, text: "Verified Alpaca paper fills" },
  { icon: LineChart, text: "PRISM decisions on the timeline" },
  { icon: GitCompareArrows, text: "ShadowFund and other simulated activity" },
];

const SURFACE_VOCAB = [
  { label: "Market data", value: "OHLCV + ts" },
  { label: "PRISM activity", value: "decision · NO_TRADE" },
  { label: "Verified size", value: "order -> fill" },
  { label: "Shadow activity", value: "sim counterfactual" },
];

export function MarketTrackerShell({ nowUtc }: { nowUtc: string }) {
  const [selectedActivities, setSelectedActivities] = useState<Set<MarketActivityKind>>(
    () => new Set(allActivityKinds),
  );
  const [timeframe, setTimeframe] = useState<MarketTimeframe>("1Day");
  const [tradedOnly, setTradedOnly] = useState(false);

  const selectedCount = selectedActivities.size;

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
      {/* Not-connected banner */}
      <div className={`${SECTION_CARD} p-5 sm:p-6`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-[#F59E0B]/40 bg-[#F59E0B]/15 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-[#F59E0B]">
                <Radio className="h-3 w-3" aria-hidden="true" /> Market data not connected
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wide text-[#94A3B8]">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" /> Paper-only · Provider-neutral
              </span>
            </div>
            <p className="mt-3 text-[14px] leading-relaxed text-[#CBD5E1]">
              Market data integration is deferred. This surface is ready for the future market-data
              feed.
            </p>
            <ul className="mt-3 grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
              {CONNECT_ITEMS.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-2 text-[13px] text-[#94A3B8]">
                  <Icon className="h-3.5 w-3.5 shrink-0 text-[#547D83]" aria-hidden="true" />
                  {text}
                </li>
              ))}
            </ul>
          </div>
          <div className="shrink-0 rounded-lg border border-white/8 bg-white/2 px-4 py-3 text-right">
            <p className="font-mono text-[10px] uppercase tracking-[0.09em] text-[#64748B]">
              Feed status
            </p>
            <p className="mt-1 font-mono text-[15px] font-semibold text-[#94A3B8]">Awaiting</p>
            <p className="font-mono text-[11px] text-[#64748B]">integration</p>
            <p className="mt-2 border-t border-white/8 pt-2 font-mono text-[10px] text-[#64748B]">
              {nowUtc} UTC
            </p>
          </div>
        </div>
        <p className="mt-4 border-t border-white/8 pt-3 text-[12px] leading-relaxed text-[#64748B]">
          No prices, candles, or executions are shown until a verified feed is connected. What
          appears here is deliberately empty, not an error and not &ldquo;no data&rdquo;, just a
          boundary awaiting its data source.
        </p>
      </div>

      {/* Timeframe */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <fieldset className="flex items-center gap-3">
          <legend className="float-left mr-3 font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
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
        </fieldset>
        <p className="font-mono text-[11px] text-[#64748B]">
          Default: {timeframe}. Timeframe selector reserved; queries real data once the feed is
          connected.
        </p>
      </div>

      {/* Price & activity: chart skeleton + activity sidebar */}
      <div className={`${SECTION_CARD} overflow-hidden`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 p-5">
          <div>
            <h2 className="font-mono text-[12px] font-semibold uppercase tracking-[0.09em] text-[#F8FAFC]">
              Price &amp; Activity
            </h2>
            <p className="mt-1 text-[12px] text-[#64748B]">
              Timeline of market data with PRISM activity overlaid.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-white/8 bg-white/5 px-2.5 py-1.5 font-mono text-[11px] text-[#94A3B8]">
            <XCircle className="h-3.5 w-3.5 text-[#64748B]" aria-hidden="true" /> Feed disconnected
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_18rem]">
          {/* Chart skeleton */}
          <div
            className="relative min-h-96 border-b border-white/8 p-6 lg:border-b-0 lg:border-r"
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
            {/* Ghost candlesticks */}
            <div
              aria-hidden="true"
              className="relative flex h-72 items-center justify-center gap-2.5 opacity-25"
            >
              {GHOST_CANDLES.map((candle, index) => {
                const tone = candle.up ? "#547D83" : "#64748B";
                return (
                  <span
                    key={index}
                    className="flex w-3 animate-pulse flex-col items-center"
                    style={{
                      height: `${candle.body + candle.top + candle.bottom}px`,
                      animationDelay: `${index * 80}ms`,
                    }}
                  >
                    <span className="w-px" style={{ height: candle.top, background: tone }} />
                    <span
                      className="w-full rounded-[1px]"
                      style={{ height: candle.body, background: tone }}
                    />
                    <span className="w-px" style={{ height: candle.bottom, background: tone }} />
                  </span>
                );
              })}
            </div>
            {/* Empty message */}
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
              <span className="grid h-10 w-10 place-items-center rounded-lg border border-white/8 bg-white/5 text-[#64748B]">
                <CandlestickChart className="h-5 w-5" aria-hidden="true" />
              </span>
              <strong className="text-[15px] font-semibold text-[#F8FAFC]">
                Market timeline unavailable
              </strong>
              <span className="max-w-sm text-[13px] leading-relaxed text-[#94A3B8]">
                Price and activity data will appear here when market data is connected.
              </span>
              <span className="mt-1 rounded-full border border-white/8 bg-white/5 px-3 py-1 font-mono text-[10px] uppercase tracking-wide text-[#64748B]">
                OHLCV / volume + PRISM &amp; ShadowFund overlays — not live data
              </span>
            </div>
          </div>

          {/* Activity sidebar (all 6 categories) */}
          <aside className="p-5" aria-label="Activity overlays">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.09em] text-[#F8FAFC]">
                Activity
              </h3>
              <span className="font-mono text-[10px] uppercase tracking-[0.09em] text-[#64748B]">
                Reserved
              </span>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B]">Timeline Filters</p>

            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={selectAllActivities}
                aria-pressed={selectedCount === marketActivityKinds.length}
                className="flex-1 rounded border border-white/8 bg-white/5 px-2 py-1.5 text-[11px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                Select all
              </button>
              <button
                type="button"
                onClick={clearActivities}
                aria-pressed={selectedCount === 0}
                className="flex-1 rounded border border-white/8 bg-white/5 px-2 py-1.5 text-[11px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                Clear all
              </button>
            </div>

            <ul className="mt-3 space-y-2" role="group" aria-label="Activity categories">
              {marketActivityKinds.map(({ id, label, description }) => {
                const selected = selectedActivities.has(id);
                return (
                  <li key={id}>
                    <button
                      type="button"
                      data-selected={selected}
                      aria-pressed={selected}
                      aria-label={`${label}: ${description}`}
                      onClick={() => toggleActivity(id)}
                      className={`flex w-full items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83] ${
                        selected
                          ? "border-[#547D83]/50 bg-[#547D83]/15"
                          : "border-white/8 bg-transparent opacity-55"
                      }`}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[13px] font-semibold text-[#F8FAFC]">{label}</span>
                          {isVerifiedTrade(id) && (
                            <span className="rounded border border-[#00D084]/30 bg-[#00D084]/15 px-1.5 py-0.5 font-mono text-[9px] uppercase text-[#00D084]">
                              actual trade
                            </span>
                          )}
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-[#94A3B8]">
                          {description}
                        </span>
                      </span>
                      {selected && (
                        <Check className="h-3.5 w-3.5 shrink-0 text-[#547D83]" aria-hidden="true" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>

            <label className="mt-4 flex cursor-pointer items-start gap-2.5 border-t border-white/8 pt-3">
              <input
                type="checkbox"
                checked={tradedOnly}
                onChange={(event) => setTradedOnly(event.target.checked)}
                className="mt-0.5 h-4 w-4 accent-[#547D83]"
              />
              <span>
                <strong className="block text-[12px] font-semibold text-[#F8FAFC]">
                  Symbols with verified trades only
                </strong>
                <small className="text-[11px] leading-relaxed text-[#94A3B8]">
                  A verified paper fill is a confirmed paper execution, not a proposal or
                  simulation.
                </small>
              </span>
            </label>

            {tradedOnly && (
              <p className="mt-3 text-[11px] text-[#64748B]" aria-live="polite">
                Verified fills only.
              </p>
            )}
          </aside>
        </div>
      </div>

      {/* What this surface will show */}
      <div className={`${SECTION_CARD} p-5 sm:p-6`}>
        <div className="flex items-center gap-2">
          <ListChecks className="h-4 w-4 text-[#547D83]" aria-hidden="true" />
          <h2 className="font-mono text-[12px] font-semibold uppercase tracking-[0.09em] text-[#F8FAFC]">
            What this surface will show
          </h2>
        </div>
        <p className="mt-2 max-w-4xl text-[13px] leading-relaxed text-[#94A3B8]">
          When a verified feed is connected, PRISM will overlay normalized market data, its own
          decisions, confirmed paper fills, and ShadowFund counterfactuals, each as an explicit,
          distinguishable event type with provenance. Nothing here claims a price, candle, or fill
          that has not been verified.
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-white/8 pt-4 lg:grid-cols-4">
          {SURFACE_VOCAB.map((item) => (
            <div key={item.label}>
              <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                {item.label}
              </dt>
              <dd className="mt-1 font-mono text-[12px] text-[#CBD5E1]">{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
