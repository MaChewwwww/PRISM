"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { rangeForPreset, rangeQuery, type DateRange } from "@/features/story/date-range";
import { adaptOverview, type OverviewRange } from "@/features/overview/overview-adapter";
import type { components } from "@/types/api.generated";

import { OverviewChart } from "./overview-chart";
import { OverviewDecisions } from "./overview-decisions";
import { OverviewSidebar } from "./overview-sidebar";
// Feature-scoped styles for the Overview dashboard (see overview-dashboard.css).
import "./overview-dashboard.css";

type Overview = components["schemas"]["Overview"];

export function OverviewDashboard({ overview, range }: { overview: Overview; range: DateRange }) {
  const router = useRouter();
  const [selected, setSelected] = useState<SelectedPoint | null>(null);

  // `now` starts as `null` so server-rendered markup and the first client
  // render omit the live clock, avoiding a hydration mismatch.
  const [now, setNow] = useState<Date | null>(null);
  const [syncSeconds, setSyncSeconds] = useState(0);
  const view = useMemo(() => adaptOverview(overview), [overview]);
  const points = view.points;

  useEffect(() => {
    const primeTimeout = window.setTimeout(() => setNow(new Date()), 0);
    const clock = window.setInterval(() => setNow(new Date()), 1000);
    return () => {
      window.clearTimeout(primeTimeout);
      window.clearInterval(clock);
    };
  }, []);

  useEffect(() => {
    const sync = window.setInterval(() => setSyncSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(sync);
  }, []);

  const latest = points.at(-1);
  const first = points[0];
  const periodChange = useMemo(
    () => (first && latest ? latest.actual - first.actual : 0),
    [first, latest],
  );
  const periodPercentage = useMemo(() => {
    if (!first || !latest || first.actual === 0) return 0;
    return ((latest.actual - first.actual) / first.actual) * 100;
  }, [first, latest]);

  function changeRange(nextRange: OverviewRange) {
    setSelected(null);
    const next = rangeForPreset(nextRange, range.to);
    router.push(`/?${rangeQuery(next)}`);
  }

  return (
    <div className="overview-app">
      <OverviewHeader range={range} onRangeChange={changeRange} now={now} />

      <section className="overview-main" aria-label="Active Portfolio overview">
        <OverviewDecisions decisions={view.decisions} />
        <OverviewChart points={points} selected={selected} onSelect={setSelected} />
      </section>

      <OverviewSidebar
        points={points}
        outcomes={view.outcomes}
        exposures={view.exposures}
        totalDecisionStories={view.decisions.length}
      />

      <OverviewTicker
        latest={latest?.actual ?? 0}
        periodChange={periodChange}
        periodPercentage={periodPercentage}
        tokens={null}
        syncSeconds={syncSeconds}
        totalDecisionStories={view.decisions.length}
      />
    </div>
  );
}

type SelectedPoint = {
  point: ReturnType<typeof adaptOverview>["points"][number];
  index: number;
};

function OverviewHeader({
  range,
  onRangeChange,
  now,
}: {
  range: DateRange;
  onRangeChange: (range: OverviewRange) => void;
  now: Date | null;
}) {
  return (
    <header className="overview-header">
      <div className="overview-header-left">
        <div className="overview-page-title-block">
          <div className="overview-page-title">Overview</div>
          <div className="overview-page-subtitle">Active Portfolio decision intelligence</div>
        </div>
      </div>

      <div className="overview-header-center">
        <div className="overview-pills" role="group" aria-label="Date range">
          {(["7d", "1m", "3m", "ytd"] as OverviewRange[]).map((item) => (
            <button
              type="button"
              key={item}
              className={`overview-pill ${range.preset === item ? "active" : ""}`}
              aria-pressed={range.preset === item}
              onClick={() => onRangeChange(item)}
            >
              {item.toUpperCase()}
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
                timeZone: "UTC",
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
                timeZone: "UTC",
              })
            : "—"}
        </span>
        <span>
          <span className="overview-status-dot" aria-hidden="true" />
          Active
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
  totalDecisionStories,
}: {
  latest: number;
  periodChange: number;
  periodPercentage: number;
  tokens: number | null;
  syncSeconds: number;
  totalDecisionStories: number;
}) {
  return (
    <footer className="overview-ticker overview-nums">
      <span className="overview-ticker-value">
        Active Portfolio equity ${latest.toLocaleString()}
      </span>
      <span className="overview-ticker-separator">·</span>
      <span className="overview-ticker-value">
        Period change {periodChange >= 0 ? "+" : "-"}${Math.abs(periodChange).toLocaleString()} (
        {periodPercentage.toFixed(1)}%)
      </span>
      <span className="overview-ticker-separator">·</span>
      <span className="overview-ticker-value">{totalDecisionStories} decision stories</span>
      <span className="overview-ticker-separator">·</span>
      <span className="overview-ticker-value">
        {tokens === null
          ? "Agent usage not reported"
          : `${(tokens / 1000).toFixed(1)}K agent tokens used`}
      </span>
      <span className="overview-ticker-separator">·</span>
      <span className="overview-ticker-value">Synced {syncSeconds}s ago</span>
    </footer>
  );
}
