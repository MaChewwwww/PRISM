"use client";

import { useEffect, useMemo, useState } from "react";

import {
  overviewDatasets,
  totalDecisionStories,
  type OverviewRange,
} from "@/features/story/overview-data";

import { OverviewChart } from "./overview-chart";
import { OverviewDecisions } from "./overview-decisions";
import { OverviewSidebar } from "./overview-sidebar";
import type { SelectedPoint } from "./overview-types";
// Feature-scoped styles for the Overview dashboard (see overview-dashboard.css).
import "./overview-dashboard.css";

export function OverviewDashboard() {
  const [range, setRange] = useState<OverviewRange>("1M");
  const [selected, setSelected] = useState<SelectedPoint | null>(null);

  // `now` starts as `null` so the server-rendered markup and the first client
  // render both omit the live clock, avoiding a hydration mismatch. The real
  // timestamp is set only after mount, then ticks once per second.
  const [now, setNow] = useState<Date | null>(null);
  const [syncSeconds, setSyncSeconds] = useState(0);

  const points = overviewDatasets[range];

  useEffect(() => {
    // Defer the first tick to a callback (rather than calling setState
    // synchronously in the effect body) so this is a plain subscription to
    // an external timer, not a state update during render/commit.
    const primeTimeout = window.setTimeout(() => setNow(new Date()), 0);
    const clock = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => {
      window.clearTimeout(primeTimeout);
      window.clearInterval(clock);
    };
  }, []);

  useEffect(() => {
    const sync = window.setInterval(() => {
      setSyncSeconds((value) => value + 1);
    }, 1000);

    return () => window.clearInterval(sync);
    // Reset whenever `range` changes by remounting the interval via the
    // `syncSeconds` reset in `changeRange`; the interval itself only needs to
    // exist for the lifetime of the component.
  }, []);

  const latest = points.at(-1);
  const first = points[0];

  const periodChange = useMemo(() => {
    if (!first || !latest) return 0;
    return latest.actual - first.actual;
  }, [first, latest]);

  const periodPercentage = useMemo(() => {
    if (!first || !latest || first.actual === 0) {
      return 0;
    }
    return ((latest.actual - first.actual) / first.actual) * 100;
  }, [first, latest]);

  function changeRange(nextRange: OverviewRange) {
    setRange(nextRange);
    setSelected(null);
    setSyncSeconds(0);
  }

  return (
    <div className="overview-app">
      <OverviewHeader
        range={range}
        onRangeChange={changeRange}
        now={now}
      />

      <main className="overview-main">
        <OverviewDecisions />

        <OverviewChart points={points} selected={selected} onSelect={setSelected} />
      </main>

      <OverviewSidebar points={points} />

      <OverviewTicker
        latest={latest?.actual ?? 0}
        periodChange={periodChange}
        periodPercentage={periodPercentage}
        tokens={points.reduce((sum, point) => sum + point.tokens, 0)}
        syncSeconds={syncSeconds}
      />
    </div>
  );
}

function OverviewHeader({
  range,
  onRangeChange,
  now,
}: {
  range: OverviewRange;
  onRangeChange: (range: OverviewRange) => void;
  now: Date | null;
}) {
  return (
    <header className="overview-header">
      <div className="overview-header-left">
        <div className="overview-page-title-block">
          <div className="overview-page-title">Overview</div>

          <div className="overview-page-subtitle">Portfolio decision intelligence</div>
        </div>
      </div>

      <div className="overview-header-center">
        <div className="overview-pills" role="group" aria-label="Date range">
          {(["7D", "1M", "3M", "YTD"] as OverviewRange[]).map((item) => (
            <button
              type="button"
              key={item}
              className={`overview-pill ${range === item ? "active" : ""}`}
              aria-pressed={range === item}
              onClick={() => onRangeChange(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="overview-header-right overview-nums">
        <span>
          {now
            ? now.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            : "—"}
        </span>

        <span>
          {now
            ? now.toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
                second: "2-digit",
                timeZoneName: "short",
              })
            : "—"}
        </span>

        <span>
          <span className="overview-status-dot" aria-hidden="true" />
          Live
        </span>
      </div>
    </header>
  );
}

function OverviewTicker({
  latest,
  periodChange,
  periodPercentage,
  tokens,
  syncSeconds,
}: {
  latest: number;
  periodChange: number;
  periodPercentage: number;
  tokens: number;
  syncSeconds: number;
}) {
  return (
    <footer className="overview-ticker overview-nums">
      <span className="overview-ticker-value">
        Illustrative equity $
        {latest.toLocaleString()}
      </span>

      <span className="overview-ticker-separator">
        ·
      </span>

      <span className="overview-ticker-value">
        Period change{" "}
        {periodChange >= 0 ? "+" : "-"}$
        {Math.abs(periodChange).toLocaleString()}{" "}
        ({periodPercentage.toFixed(1)}%)
      </span>

      <span className="overview-ticker-separator">
        ·
      </span>

      <span className="overview-ticker-value">
        {totalDecisionStories} decision stories
      </span>

      <span className="overview-ticker-separator">
        ·
      </span>

      <span className="overview-ticker-value">
        {(tokens / 1000).toFixed(1)}K agent tokens used
      </span>

      <span className="overview-ticker-separator">
        ·
      </span>

      <span className="overview-ticker-value">
        Synced {syncSeconds}s ago
      </span>
    </footer>
  );
}