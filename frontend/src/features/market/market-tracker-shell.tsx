"use client";

import {
  BarChart3,
  CandlestickChart,
  Check,
  Database,
  Filter,
  LockKeyhole,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import { useMemo, useState } from "react";

import type { DateRange } from "@/features/story/date-range";
import {
  isVerifiedTrade,
  marketActivityKinds,
  marketTimeframes,
  type MarketActivityKind,
  type MarketTimeframe,
} from "@/features/market/market-tracker-types";

import { ProvenanceLabel, Section } from "@/components/workspace/workspace-ui";
import "./market-tracker.css";

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
    <div className="market-tracker">
      <div className="market-tracker-notice" role="status">
        <div className="market-tracker-notice-icon" aria-hidden="true">
          <Radio />
        </div>
        <div>
          <strong>Market data integration is deferred</strong>
          <p>
            This workspace reserves the chart, watchlist, and activity overlays for a future
            authenticated server adapter. No market, account, order, or provider data is loaded.
          </p>
        </div>
        <ProvenanceLabel provenance="planned_integration" />
      </div>

      <div className="market-tracker-toolbar" aria-label="Market tracker controls">
        <label className="market-tracker-symbol">
          <span>Symbol</span>
          <div className="market-tracker-input-wrap">
            <input
              type="text"
              placeholder="Symbols load from the server"
              disabled
              aria-describedby="market-tracker-symbol-help"
            />
            <LockKeyhole aria-hidden="true" />
          </div>
          <small id="market-tracker-symbol-help">
            Symbol search becomes available with the market adapter.
          </small>
        </label>
        <fieldset className="market-tracker-timeframes">
          <legend>Timeframe</legend>
          <div role="group" aria-label="Chart timeframe">
            {marketTimeframes.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={timeframe === value}
                onClick={() => setTimeframe(value)}
              >
                {value}
              </button>
            ))}
          </div>
          <small>Default: {timeframe}. Values appear after integration.</small>
        </fieldset>
        <div className="market-tracker-capability" role="note">
          <Database aria-hidden="true" />
          <span>
            <strong>Feed</strong>
            <small>Server entitlement (planned)</small>
          </span>
        </div>
      </div>

      <Section
        title="Activity overlays"
        description="Choose which future PRISM and Alpaca events may appear over the price timeline. Controls are local-only until the server endpoint is authorized."
        id="market-tracker-activity-heading"
      >
        <div className="market-tracker-filter-panel">
          <div className="market-tracker-filter-heading">
            <div>
              <Filter aria-hidden="true" />
              <strong>
                {selectedCount} of {marketActivityKinds.length} categories selected
              </strong>
            </div>
            <div className="market-tracker-filter-actions">
              <button
                type="button"
                onClick={selectAllActivities}
                aria-pressed={selectedCount === marketActivityKinds.length}
              >
                <Check aria-hidden="true" /> Select all
              </button>
              <button type="button" onClick={clearActivities} aria-pressed={selectedCount === 0}>
                Clear all
              </button>
            </div>
          </div>
          <div className="market-tracker-filters" role="group" aria-label="Activity categories">
            {marketActivityKinds.map(({ id, label, description, color }) => {
              const selected = selectedActivities.has(id);
              return (
                <button
                  key={id}
                  type="button"
                  className="market-tracker-filter"
                  data-selected={selected}
                  style={{ "--filter-color": color } as React.CSSProperties}
                  aria-pressed={selected}
                  aria-label={`${label}: ${description}`}
                  onClick={() => toggleActivity(id)}
                >
                  <span className="market-tracker-filter-swatch" aria-hidden="true" />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>
          <label className="market-tracker-traded-only">
            <input
              type="checkbox"
              checked={tradedOnly}
              onChange={(event) => setTradedOnly(event.target.checked)}
            />
            <span>
              <strong>Symbols with verified trades only</strong>
              <small>
                Future filter: only symbols with confirmed <code>fill</code> activity qualify.
                Proposals, NO_TRADE, and ShadowFund events never count as trades.
              </small>
            </span>
          </label>
          {selectedCount > 0 && (
            <p className="market-tracker-selection" aria-live="polite">
              Showing future overlays for {selectedLabels.map(({ label }) => label).join(", ")}.
            </p>
          )}
        </div>
      </Section>

      <div className="market-tracker-grid">
        <Section
          title="Price and activity timeline"
          description="Candlestick and volume layers are reserved for normalized server bars. The textual fallback keeps the empty state understandable to assistive technology."
          id="market-tracker-chart-heading"
        >
          <div className="market-tracker-chart" aria-label="Market chart awaiting integration">
            <div className="market-tracker-chart-grid" aria-hidden="true" />
            <div className="market-tracker-chart-placeholder">
              <CandlestickChart aria-hidden="true" />
              <strong>No market bars available</strong>
              <span>
                Connect the authenticated server market adapter to render OHLCV, volume, and
                activity markers.
              </span>
            </div>
            <div className="market-tracker-chart-footer">
              <span>
                <CandlestickChart aria-hidden="true" /> OHLCV / volume reserved
              </span>
              <span>
                <BarChart3 aria-hidden="true" />{" "}
                {tradedOnly ? "Verified fills only" : "All selected activities"}
              </span>
            </div>
          </div>
        </Section>

        <Section
          title="Watchlist"
          description="Future snapshots will populate this list without exposing provider credentials to the browser."
          id="market-tracker-watchlist-heading"
        >
          <div
            className="market-tracker-watchlist"
            aria-labelledby="market-tracker-watchlist-heading"
          >
            <SlidersHorizontal aria-hidden="true" />
            <strong>No symbols loaded</strong>
            <p>Watchlist snapshots are unavailable until the server-side integration is enabled.</p>
            <span className="market-tracker-watchlist-note">
              No symbols, prices, positions, or fills are being represented.
            </span>
          </div>
        </Section>
      </div>

      <div className="market-tracker-legend" aria-labelledby="market-tracker-legend-heading">
        <div>
          <p className="eyebrow" id="market-tracker-legend-heading">
            Activity legend
          </p>
          <p>
            Only confirmed fills qualify as actual trades. Every other category remains a distinct
            research, decision, order, or simulation event.
          </p>
        </div>
        <ul>
          {marketActivityKinds.map(({ id, label, color }) => (
            <li key={id} data-selected={selectedActivities.has(id)}>
              <span style={{ "--filter-color": color } as React.CSSProperties} aria-hidden="true" />
              <span>{label}</span>
              {isVerifiedTrade(id) && <small>actual trade</small>}
            </li>
          ))}
        </ul>
      </div>

      <p className="market-tracker-range-note">
        Requested UTC range: <code>{range.from}</code> to <code>{range.to}</code>. The shared URL
        range is preserved for the future endpoint.
      </p>
    </div>
  );
}
