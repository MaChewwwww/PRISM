"use client";

import { useMemo, useState } from "react";

import {
  exposures,
  outcomes,
  percentChange,
  totalDecisionStories,
  type OverviewPoint,
} from "@/features/story/overview-data";

type Props = {
  points: OverviewPoint[];
};

export function OverviewSidebar({ points }: Props) {
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(
    null,
  );

  const [selectedExposure, setSelectedExposure] = useState<string | null>(
    null,
  );

  const totalTokens = useMemo(
    () => points.reduce((sum, point) => sum + point.tokens, 0),
    [points],
  );

  const latest = points.at(-1);

  const first = points[0];

  const periodChange = first && latest ? percentChange(first.actual, latest.actual) : 0;

  return (
    <aside className="overview-side">
      <section className="overview-panel overview-side-panel">
        <span className="overview-side-title">
          Decision outcomes
        </span>

        <div className="overview-outcome-bars">
          {outcomes.map((outcome) => {
            const selected = selectedOutcome === outcome.label;
            const dimmed =
              selectedOutcome !== null && !selected;

            const percentage = Math.round(
              (outcome.count /
                outcomes.reduce((sum, item) => sum + item.count, 0)) *
                100,
            );

            return (
              <button
                key={outcome.label}
                type="button"
                className={`overview-outcome-bar-row ${
                  dimmed ? "dim" : ""
                }`}
                onClick={() =>
                  setSelectedOutcome(
                    selected ? null : outcome.label,
                  )
                }
              >
                <span className="overview-outcome-bar-label">
                  <span>{outcome.label}</span>
                  <span className="overview-nums">
                    {outcome.count}
                  </span>
                </span>

                <span className="overview-outcome-bar-track">
                  <span
                    className="overview-outcome-bar-fill"
                    style={{
                      width: `${percentage}%`,
                      background: outcome.color,
                    }}
                  />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="overview-panel overview-side-panel">
        <span className="overview-side-title">
          Portfolio exposure
        </span>

        <div className="overview-exposure-list">
          {exposures.map((exposure) => {
            const selected =
              selectedExposure === exposure.label;

            const dimmed =
              selectedExposure !== null && !selected;

            return (
              <button
                key={exposure.label}
                type="button"
                className={`overview-exposure-row ${
                  dimmed ? "dim" : ""
                }`}
                onClick={() =>
                  setSelectedExposure(
                    selected ? null : exposure.label,
                  )
                }
              >
                <span className="overview-exposure-label-row">
                  <span>{exposure.label}</span>
                  <span className="overview-nums">
                    {exposure.pct}%
                  </span>
                </span>

                <span className="overview-exposure-track">
                  <span
                    className="overview-exposure-fill"
                    style={{
                      width: `${exposure.pct}%`,
                    }}
                  />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="overview-panel overview-snapshot-panel">
        <span className="overview-side-title">
          Snapshot
        </span>

        <div className="overview-stats-grid overview-nums">
          <div>
            <div className="overview-stat-val">
              ${latest?.actual.toLocaleString() ?? "—"}
            </div>
            <div className="overview-stat-lbl">
              Illustrative equity
            </div>
          </div>

          <div>
            <div
              className={`overview-stat-val ${
                periodChange >= 0
                  ? "overview-pos"
                  : "overview-neg"
              }`}
            >
              {periodChange >= 0 ? "+" : ""}
              {periodChange.toFixed(1)}%
            </div>
            <div className="overview-stat-lbl">
              Period change
            </div>
          </div>

          <div>
            <div className="overview-stat-val">
              {totalDecisionStories}
            </div>
            <div className="overview-stat-lbl">
              Decision stories
            </div>
          </div>

          <div>
            <div className="overview-stat-val">
              {(totalTokens / 1000).toFixed(1)}K
            </div>
            <div className="overview-stat-lbl">
              Agent tokens
            </div>
          </div>
        </div>

        <div className="overview-snapshot-spark-wrap">
          <div className="overview-snapshot-spark-label">
            Agent tokens, selected period{" "}
            <span className="overview-teal-dot">·</span>{" "}
            teal = decision day
          </div>

          <TokenSparkline points={points} />
        </div>
      </section>
    </aside>
  );
}

function TokenSparkline({
  points,
}: {
  points: OverviewPoint[];
}) {
  const max = Math.max(...points.map((point) => point.tokens), 1);

  return (
    <div className="overview-spark">
      {points.map((point) => {
        const height = Math.max(
          8,
          (point.tokens / max) * 48,
        );

        return (
          <button
            type="button"
            key={`${point.date}-${point.time}`}
            className="overview-spark-bar-wrap"
            title={`${point.date} · ${point.time} — ${point.tokens.toLocaleString()} tokens`}
          >
            <span
              className={`overview-spark-bar ${
                point.decision
                  ? "decision-day"
                  : ""
              }`}
              style={{
                height: `${height}px`,
              }}
            />

            <span className="overview-spark-label">
              {point.date.replace(/^[A-Za-z]+\s/, "")}
            </span>
          </button>
        );
      })}
    </div>
  );
}