"use client";

import { useState } from "react";

import type {
  OverviewExposure,
  OverviewOutcome,
  OverviewPoint,
} from "@/features/overview/overview-adapter";

type Props = {
  points: OverviewPoint[];
  outcomes: OverviewOutcome[];
  exposures: OverviewExposure[];
  totalDecisionStories: number;
};

export function OverviewSidebar({ points, outcomes, exposures, totalDecisionStories }: Props) {
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null);
  const [selectedExposure, setSelectedExposure] = useState<string | null>(null);
  const latest = points.at(-1);
  const first = points[0];
  const periodChange =
    first && latest && first.actual !== 0
      ? ((latest.actual - first.actual) / first.actual) * 100
      : 0;
  const totalOutcomes = outcomes.reduce((sum, item) => sum + item.count, 0);

  return (
    <aside className="overview-side">
      <section className="overview-panel overview-side-panel">
        <span className="overview-side-title">Decision outcomes</span>
        {outcomes.length === 0 ? (
          <p className="overview-chart-detail-empty">No outcomes in this period.</p>
        ) : (
          <div className="overview-outcome-bars">
            {outcomes.map((outcome) => {
              const selected = selectedOutcome === outcome.label;
              const dimmed = selectedOutcome !== null && !selected;
              const percentage = totalOutcomes
                ? Math.round((outcome.count / totalOutcomes) * 100)
                : 0;
              return (
                <button
                  key={outcome.label}
                  type="button"
                  className={`overview-outcome-bar-row ${dimmed ? "dim" : ""}`}
                  onClick={() => setSelectedOutcome(selected ? null : outcome.label)}
                >
                  <span className="overview-outcome-bar-label">
                    <span>{outcome.label}</span>
                    <span className="overview-nums">{outcome.count}</span>
                  </span>
                  <span className="overview-outcome-bar-track">
                    <span
                      className="overview-outcome-bar-fill"
                      style={{ width: `${percentage}%`, background: outcome.color }}
                    />
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <section className="overview-panel overview-side-panel">
        <span className="overview-side-title">Active Portfolio exposure</span>
        <div className="overview-exposure-list">
          {exposures.map((exposure) => {
            const selected = selectedExposure === exposure.label;
            const dimmed = selectedExposure !== null && !selected;
            return (
              <button
                key={exposure.label}
                type="button"
                className={`overview-exposure-row ${dimmed ? "dim" : ""}`}
                onClick={() => setSelectedExposure(selected ? null : exposure.label)}
              >
                <span className="overview-exposure-label-row">
                  <span>{exposure.label}</span>
                  <span className="overview-nums">{exposure.pct}%</span>
                </span>
                <span className="overview-exposure-track">
                  <span className="overview-exposure-fill" style={{ width: `${exposure.pct}%` }} />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="overview-panel overview-snapshot-panel">
        <span className="overview-side-title">Snapshot</span>
        <div className="overview-stats-grid overview-nums">
          <div>
            <div className="overview-stat-val">${latest?.actual.toLocaleString() ?? "—"}</div>
            <div className="overview-stat-lbl">Active Portfolio equity</div>
          </div>
          <div>
            <div
              className={`overview-stat-val ${periodChange >= 0 ? "overview-pos" : "overview-neg"}`}
            >
              {periodChange >= 0 ? "+" : ""}
              {periodChange.toFixed(1)}%
            </div>
            <div className="overview-stat-lbl">Period change</div>
          </div>
          <div>
            <div className="overview-stat-val">{totalDecisionStories}</div>
            <div className="overview-stat-lbl">Decision stories</div>
          </div>
          <div>
            <div className="overview-stat-val">—</div>
            <div className="overview-stat-lbl">Agent tokens not reported</div>
          </div>
        </div>
        <div className="overview-snapshot-spark-wrap">
          <div className="overview-snapshot-spark-label">
            Active Portfolio observations · backend range
          </div>
          <PortfolioSparkline points={points} />
        </div>
      </section>
    </aside>
  );
}

function PortfolioSparkline({ points }: { points: OverviewPoint[] }) {
  if (points.length === 0) return <p className="overview-chart-detail-empty">No observations.</p>;
  const min = Math.min(...points.map((point) => point.actual));
  const max = Math.max(...points.map((point) => point.actual));
  const span = max - min || 1;
  return (
    <div className="overview-spark">
      {points.map((point) => {
        const height = Math.max(8, ((point.actual - min) / span) * 48);
        return (
          <button
            type="button"
            key={`${point.date}-${point.time}`}
            className="overview-spark-bar-wrap"
            title={`${point.date} · ${point.actual.toLocaleString()}`}
          >
            <span
              className={`overview-spark-bar ${point.decision ? "decision-day" : ""}`}
              style={{ height: `${height}px` }}
            />
            <span className="overview-spark-label">{point.date.slice(5)}</span>
          </button>
        );
      })}
    </div>
  );
}
