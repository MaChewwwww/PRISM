"use client";

import { Activity, ArrowRight, RefreshCw, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
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

type Overview = components["schemas"]["Overview"] & { asOf?: string };

export function OverviewDashboard({ overview, range }: { overview: Overview; range: DateRange }) {
  const router = useRouter();
  const [selected, setSelected] = useState<SelectedPoint | null>(null);

  // `now` starts as `null` so server-rendered markup and the first client
  // render omit the live clock, avoiding a hydration mismatch.
  const [now, setNow] = useState<Date | null>(null);
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

  function changeRange(nextRange: OverviewRange) {
    setSelected(null);
    const next = rangeForPreset(nextRange, range.to);
    router.push(`/dashboard?${rangeQuery(next)}`);
  }

  return (
    <div className="overview-app">
      <OverviewHeader
        range={range}
        onRangeChange={changeRange}
        now={now}
        onRefresh={() => router.refresh()}
      />

      <section className="overview-main" aria-label="Active Portfolio overview">
        <OverviewChart points={points} selected={selected} onSelect={setSelected} />
        <OverviewDecisions decisions={view.decisions} />
        <OverviewRecommendations recommendations={view.recommendations} />
      </section>

      <OverviewSidebar
        points={points}
        outcomes={view.outcomes}
        exposures={view.exposures}
        positions={view.positions}
        asOf={overview.asOf ?? null}
        totalDecisionStories={view.decisions.length}
      />

      <OverviewTicker />
    </div>
  );
}

/**
 * "This period's recommendations" — surfaces overview.recommendations (real
 * contract data that was previously unused) and links to Weekly Summary where
 * bounded profile changes are reviewed.
 */
function OverviewRecommendations({ recommendations }: { recommendations: string[] }) {
  return (
    <section className="overview-panel overview-recos-panel" aria-label="Recommendations">
      <div className="overview-decisions-head">
        <div className="overview-section-header" style={{ marginBottom: 0 }}>
          <span className="overview-section-icon" aria-hidden="true">
            <ShieldCheck size={14} />
          </span>
          <div>
            <h3>This period&rsquo;s recommendations</h3>
            <p>Bounded post-analysis suggestions awaiting manual review.</p>
          </div>
        </div>
        <Link href="/weekly-summary" className="overview-see-all">
          Review in Weekly Summary
          <ArrowRight size={12} aria-hidden="true" />
        </Link>
      </div>
      {recommendations.length === 0 ? (
        <div className="overview-recos-empty">
          <p>No recommendations for this period.</p>
          <span>
            Post-analysis surfaces bounded AI Profile suggestions after completed evaluation
            windows. They will appear here for manual review.
          </span>
        </div>
      ) : (
        <ul className="overview-recos-list">
          {recommendations.map((item, index) => (
            <li key={index} className="overview-recos-item">
              <span className="overview-recos-index" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
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
  onRefresh,
}: {
  range: DateRange;
  onRangeChange: (range: OverviewRange) => void;
  now: Date | null;
  onRefresh: () => void;
}) {
  return (
    <header className="overview-header">
      <div className="overview-header-left">
        <div className="overview-page-title-block">
          <div className="overview-eyebrow"></div>
          <div className="overview-page-title">Active Portfolio</div>
          <div className="overview-page-subtitle">
            Decision intelligence and capital exposure for the current period.
          </div>
        </div>
      </div>

      <div className="overview-header-right">
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
        <div className="overview-nums overview-clock">
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
        </div>
        <div className="overview-controls" role="group" aria-label="System controls">
          <SystemHealthControl />
          <button
            type="button"
            className="overview-control-btn"
            aria-label="Refresh dashboard data"
            title="Refresh dashboard data"
            onClick={onRefresh}
          >
            <RefreshCw size={15} aria-hidden="true" />
          </button>
          <ActiveProfileControl />
        </div>
      </div>
    </header>
  );
}

/**
 * System Health control. The evidence-freshness SLO (30s) is a governance
 * concept, but this surface does not receive live freshness telemetry, so the
 * popover states the concept and marks live monitoring as deferred rather than
 * showing a fabricated freshness number or a fake "healthy" status.
 */
function SystemHealthControl() {
  const [open, setOpen] = useState(false);
  return (
    <div className="overview-control-wrap">
      <button
        type="button"
        className="overview-control-btn"
        aria-label="System health"
        aria-expanded={open}
        title="System health"
        onClick={() => setOpen((value) => !value)}
      >
        <Activity size={15} aria-hidden="true" />
        <span className="overview-control-dot" aria-hidden="true" />
      </button>
      {open && (
        <div className="overview-control-popover" role="dialog" aria-label="System health">
          <div className="overview-control-popover-head">
            <strong>System health</strong>
            <button
              type="button"
              className="overview-chart-detail-close"
              aria-label="Close"
              onClick={() => setOpen(false)}
            >
              <X size={13} aria-hidden="true" />
            </button>
          </div>
          <p className="overview-control-popover-body">
            Deterministic authorization requires evidence and market data within a 30-second
            freshness window.
          </p>
          <p className="overview-control-popover-note">
            Live freshness and evidence-quality telemetry are not reported to this surface in this
            build. No health status is asserted here.
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Active AI Profile control. The overview endpoint does not carry the active
 * profile or its thresholds, so this links to Rules (the profile source of
 * truth) rather than displaying a hardcoded profile name or threshold values.
 */
function ActiveProfileControl() {
  return (
    <Link
      href="/rules"
      className="overview-control-btn"
      aria-label="Active AI profile (open Rules)"
      title="Active AI profile"
    >
      <ShieldCheck size={15} aria-hidden="true" />
    </Link>
  );
}

function OverviewTicker() {
  return (
    <footer className="overview-ticker overview-nums">
      <span className="overview-ticker-value">
        Paper-only. Illustrative figures with explicit backend provenance — not a broker receipt or
        an authorization to trade.
      </span>
      <span className="overview-ticker-separator">·</span>
      <span className="overview-ticker-value">
        © {new Date().getFullYear()} PRISM. All rights reserved.
      </span>
    </footer>
  );
}
