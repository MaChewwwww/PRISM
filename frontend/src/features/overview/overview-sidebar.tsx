"use client";

import { ChartColumn, Layers3, PieChart, Wallet } from "lucide-react";
import { useState } from "react";

import type {
  OverviewExposure,
  OverviewOutcome,
  OverviewPoint,
  OverviewPosition,
} from "@/features/overview/overview-adapter";

type Props = {
  points: OverviewPoint[];
  outcomes: OverviewOutcome[];
  exposures: OverviewExposure[];
  positions: OverviewPosition[];
  asOf: string | null;
  totalDecisionStories: number;
};

/**
 * PRISM Alpaca Paper Account Overview.
 *
 * Renders only the paper-account fields the presentation contract genuinely
 * exposes. Raw account fields the security boundary withholds (account
 * identifier, buying power, long/short market value, pattern-day-trader, day
 * trades, margin multiplier, shorting-allowed, trading-blocked) are omitted
 * entirely rather than shown as placeholders.
 */
function AccountOverviewPanel({
  equity,
  todaysPnl,
  positionsCount,
  asOf,
}: {
  equity: number | null;
  todaysPnl: { change: number; pct: number } | null;
  positionsCount: number;
  asOf: string | null;
}) {
  const rows: Array<{ label: string; value: string; tone?: string; muted?: boolean }> = [
    { label: "Account Status", value: "Active" },
    { label: "Environment", value: "Paper account" },
    { label: "Currency", value: "USD" },
    {
      label: "Portfolio Value",
      value: equity === null ? "—" : `$${equity.toLocaleString()}`,
    },
    { label: "Equity", value: equity === null ? "—" : `$${equity.toLocaleString()}` },
    {
      label: "Today's P&L (selected range)",
      value: todaysPnl
        ? `${todaysPnl.change >= 0 ? "+" : "-"}$${Math.abs(todaysPnl.change).toLocaleString()} (${todaysPnl.pct.toFixed(2)}%)`
        : "—",
      tone: todaysPnl ? (todaysPnl.change >= 0 ? "+" : "-") : undefined,
    },
    { label: "Open Positions", value: String(positionsCount) },
  ];

  return (
    <section className="overview-panel overview-side-panel">
      <SectionHeading
        icon={Wallet}
        title="PRISM Alpaca Paper Account Overview"
        description="Paper account snapshot."
      />
      <dl className="overview-account-list">
        {rows.map((row) => (
          <div key={row.label} className="overview-account-row">
            <dt>{row.label}</dt>
            <dd
              className="overview-nums"
              style={{
                color: row.muted
                  ? "var(--text-muted)"
                  : row.tone
                    ? row.tone === "+"
                      ? "var(--status-profit)"
                      : "var(--status-loss)"
                    : "var(--foreground)",
              }}
            >
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="overview-account-checked overview-nums">
        Checked at (UTC): {asOf ? new Date(asOf).toISOString().replace("T", " ").slice(0, 19) : "—"}
      </p>
    </section>
  );
}

function SectionHeading({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof PieChart;
  title: string;
  description: string;
}) {
  return (
    <div className="overview-section-header">
      <span className="overview-section-icon" aria-hidden="true">
        <Icon size={14} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function OverviewSidebar({
  points,
  outcomes,
  exposures,
  positions,
  asOf,
  totalDecisionStories,
}: Props) {
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null);
  const [selectedExposure, setSelectedExposure] = useState<string | null>(null);
  const latest = points.at(-1);
  const first = points[0];
  const periodChange =
    first && latest && first.actual !== 0
      ? ((latest.actual - first.actual) / first.actual) * 100
      : 0;
  const totalOutcomes = outcomes.reduce((sum, item) => sum + item.count, 0);
  const todaysPnl =
    first && latest ? { change: latest.actual - first.actual, pct: periodChange } : null;

  return (
    <aside className="overview-side">
      <AccountOverviewPanel
        equity={latest ? latest.actual : null}
        todaysPnl={todaysPnl}
        positionsCount={positions.length}
        asOf={asOf}
      />

      <section className="overview-panel overview-side-panel">
        <SectionHeading
          icon={ChartColumn}
          title="Decision outcomes"
          description="Latest decision across the active portfolio."
        />
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
        <SectionHeading
          icon={PieChart}
          title="Active Portfolio exposure"
          description="Allocation by risk posture and capital concentration."
        />
        {exposures.length === 0 ? (
          <div className="overview-empty-block">
            {/* Ghost allocation bars so the shape of the panel reads while empty */}
            <div className="overview-exposure-list" aria-hidden="true">
              {[64, 42, 24].map((w, i) => (
                <div key={i} className="overview-exposure-row">
                  <span className="overview-exposure-label-row">
                    <span className="overview-skel-pill" style={{ width: "40%" }} />
                    <span className="overview-skel-pill" style={{ width: "2.5rem" }} />
                  </span>
                  <span className="overview-exposure-track">
                    <span
                      className="overview-exposure-fill overview-skel-shimmer"
                      style={{ width: `${w}%` }}
                    />
                  </span>
                </div>
              ))}
            </div>
            <p className="overview-empty-caption">
              Allocation by risk posture will appear here once positions are recorded in this range.
            </p>
          </div>
        ) : (
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
                    <span
                      className="overview-exposure-fill"
                      style={{ width: `${exposure.pct}%` }}
                    />
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <section className="overview-panel overview-snapshot-panel">
        <SectionHeading
          icon={Layers3}
          title="Snapshot"
          description="Most recent portfolio measurements for this period."
        />
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
        </div>
        <div className="overview-snapshot-spark-wrap">
          <div className="overview-snapshot-spark-label">Active Portfolio observations</div>
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
