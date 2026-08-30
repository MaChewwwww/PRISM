"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { X } from "lucide-react";

import {
  formatCurrency,
  formatSignedCurrency,
  formatSignedPercent,
  percentChange,
  type OverviewPoint,
} from "@/features/overview/overview-adapter";

import type { OverviewChartProps } from "./overview-types";

const PLOT_PADDING_PCT = 8;

function buildScale(points: OverviewPoint[]) {
  if (points.length === 0) {
    return {
      yFor: () => 50,
      xFor: () => 50,
      min: 0,
      max: 1,
    };
  }
  const values = points.flatMap((point) => [point.actual, point.alt, point.bench]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  function yFor(value: number) {
    const raw = ((max - value) / span) * 100;
    return PLOT_PADDING_PCT + raw * (1 - (PLOT_PADDING_PCT * 2) / 100);
  }

  function xFor(index: number) {
    if (points.length <= 1) return 50;
    return (index / (points.length - 1)) * 100;
  }

  return { yFor, xFor, min, max };
}

function toPath(
  points: OverviewPoint[],
  key: "actual" | "alt" | "bench",
  scale: ReturnType<typeof buildScale>,
) {
  return points.map((point, index) => `${scale.xFor(index)},${scale.yFor(point[key])}`).join(" ");
}

export function OverviewChart({ points, selected, onSelect }: OverviewChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const scale = useMemo(() => buildScale(points), [points]);

  const actualPath = useMemo(() => toPath(points, "actual", scale), [points, scale]);
  const altPath = useMemo(() => toPath(points, "alt", scale), [points, scale]);
  const benchPath = useMemo(() => toPath(points, "bench", scale), [points, scale]);

  const gapPolygon = useMemo(() => {
    if (points.length < 2) return "";
    const top = points.map((point, index) => `${scale.xFor(index)},${scale.yFor(point.alt)}`);
    const bottom = points
      .map((point, index) => `${scale.xFor(index)},${scale.yFor(point.actual)}`)
      .reverse();
    return [...top, ...bottom].join(" ");
  }, [points, scale]);

  const activeIndex = selected ? selected.index : hoverIndex;
  const activePoint = activeIndex !== null ? points[activeIndex] : null;

  if (points.length === 0) {
    return (
      <section
        className="overview-panel overview-chart-panel"
        aria-labelledby="overview-chart-title"
      >
        <div className="overview-chart-head">
          <h2 id="overview-chart-title" className="overview-side-title">
            Active Portfolio path
          </h2>
        </div>
        <p className="overview-chart-detail-empty">No portfolio observations in this date range.</p>
      </section>
    );
  }

  function selectPoint(index: number) {
    if (selected && selected.index === index) {
      onSelect(null);
      return;
    }
    onSelect({ point: points[index], index });
  }

  return (
    <section className="overview-panel overview-chart-panel" aria-labelledby="overview-chart-title">
      <div className="overview-chart-head">
        <h2 id="overview-chart-title" className="overview-side-title">
          Active Portfolio path
        </h2>
        <div className="overview-chart-legend">
          <span className="overview-legend-item">
            <span className="overview-legend-swatch overview-legend-actual" />
            Active Portfolio
          </span>
          <span className="overview-legend-item">
            <span className="overview-legend-swatch overview-legend-alt" />
            Alternative
          </span>
          <span className="overview-legend-item">
            <span className="overview-legend-swatch overview-legend-bench" />
            Benchmark
          </span>
          <span className="overview-legend-item overview-legend-gap">
            <span className="overview-legend-swatch overview-legend-gap-swatch" />
            Gap vs. alternative
          </span>
        </div>
        <span className="overview-chart-hint">
          {selected ? "Selected point" : "Click a point for details"}
        </span>
      </div>

      <div className={`overview-chart-row ${selected ? "has-detail" : ""}`}>
        <div className="overview-chart-body">
          <div className="overview-chart-plot">
            <svg
              className="overview-chart-svg"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              role="img"
              aria-label="Active Portfolio, alternative, and benchmark equity paths over the selected date range, with the gap between the portfolio and the best alternative shaded"
            >
              {[0, 25, 50, 75, 100].map((line) => (
                <line
                  key={line}
                  x1={0}
                  y1={line}
                  x2={100}
                  y2={line}
                  className="overview-chart-gridline"
                />
              ))}
              <polygon points={gapPolygon} className="overview-chart-gap" />
              <polyline
                points={benchPath}
                className="overview-chart-line overview-chart-line-bench"
              />
              <polyline points={altPath} className="overview-chart-line overview-chart-line-alt" />
              <polyline
                points={actualPath}
                className="overview-chart-line overview-chart-line-actual"
              />
            </svg>

            {selected && (
              <div
                className="overview-chart-selected-line"
                style={{ left: `${scale.xFor(selected.index)}%` }}
                aria-hidden="true"
              />
            )}

            <div className="overview-chart-points">
              {points.map((point, index) => {
                const isActive = activeIndex === index;
                const isSelected = selected?.index === index;
                const isLatest = index === points.length - 1;
                return (
                  <button
                    type="button"
                    key={`${point.date}-${point.time}`}
                    className={`overview-chart-point-hit ${isActive ? "active" : ""}`}
                    style={{ left: `${scale.xFor(index)}%` }}
                    onMouseEnter={() => setHoverIndex(index)}
                    onMouseLeave={() => setHoverIndex(null)}
                    onFocus={() => setHoverIndex(index)}
                    onBlur={() => setHoverIndex(null)}
                    onClick={() => selectPoint(index)}
                    aria-pressed={isSelected}
                    aria-label={`${point.date} at ${point.time}: active portfolio ${formatCurrency(point.actual)}${
                      point.decision ? `. Decision: ${point.decision.title}` : ""
                    }`}
                  >
                    <span
                      className={`overview-chart-marker ${point.decision ? "decision" : ""} ${
                        isLatest ? "latest" : ""
                      } ${isSelected ? "selected" : ""}`}
                      style={{ top: `${scale.yFor(point.actual)}%` }}
                    />
                  </button>
                );
              })}
            </div>

            {activePoint && activeIndex !== null && (
              <div
                className="overview-chart-tooltip"
                style={{
                  left: `${scale.xFor(activeIndex)}%`,
                  ...(scale.xFor(activeIndex) > 70
                    ? { transform: "translateX(-100%)" }
                    : undefined),
                }}
                role="status"
              >
                <strong>
                  {activePoint.date} · {activePoint.time}
                </strong>
                <div>
                  <span>Active Portfolio</span>
                  <span className="overview-nums">{formatCurrency(activePoint.actual)}</span>
                </div>
                <div>
                  <span>Alternative</span>
                  <span className="overview-nums">{formatCurrency(activePoint.alt)}</span>
                </div>
                <div>
                  <span>Benchmark</span>
                  <span className="overview-nums">{formatCurrency(activePoint.bench)}</span>
                </div>
              </div>
            )}
          </div>

          <div className="overview-chart-x-axis">
            {points.map((point) => (
              <span key={`${point.date}-${point.time}`}>{point.date}</span>
            ))}
          </div>
        </div>

        {selected && <ChartDetailPanel point={selected.point} onClose={() => onSelect(null)} />}
      </div>
    </section>
  );
}

function ChartDetailPanel({ point, onClose }: { point: OverviewPoint; onClose: () => void }) {
  const actualPct = percentChange(point.actual, point.actual);
  const altPct = percentChange(point.actual, point.alt);
  const benchPct = percentChange(point.actual, point.bench);

  return (
    <aside className="overview-chart-detail" aria-label="Selected point detail">
      <div className="overview-chart-detail-head">
        <div>
          <strong>{point.date}</strong>
          <span>{point.time}</span>
        </div>
        <button
          type="button"
          className="overview-chart-detail-close"
          onClick={onClose}
          aria-label="Close chart detail"
        >
          <X size={14} aria-hidden="true" />
        </button>
      </div>

      <dl className="overview-chart-detail-values overview-nums">
        <div>
          <dt>Active Portfolio</dt>
          <dd>
            {formatCurrency(point.actual)}
            <span>{formatSignedPercent(actualPct)}</span>
          </dd>
        </div>
        <div>
          <dt>Alternative</dt>
          <dd>
            {formatCurrency(point.alt)}
            <span>{formatSignedPercent(altPct)}</span>
          </dd>
        </div>
        <div>
          <dt>Benchmark</dt>
          <dd>
            {formatCurrency(point.bench)}
            <span>{formatSignedPercent(benchPct)}</span>
          </dd>
        </div>
      </dl>

      {point.decision ? (
        <div className="overview-chart-detail-decision">
          <span className="overview-side-title">Decision</span>
          <p className="overview-chart-detail-decision-title">{point.decision.title}</p>
          <dl>
            <div>
              <dt>Agent perspective</dt>
              <dd>{point.decision.perspective}</dd>
            </div>
            <div>
              <dt>Outcome</dt>
              <dd>{point.decision.outcome}</dd>
            </div>
            <div>
              <dt>Active result</dt>
              <dd className="overview-nums">{formatSignedCurrency(point.decision.active)}</dd>
            </div>
          </dl>
          <Link
            className="text-link"
            href={point.decision.storyId ? `/stories/${point.decision.storyId}` : "/stories"}
          >
            View decision story
          </Link>
        </div>
      ) : (
        <p className="overview-chart-detail-empty">No decision was recorded for this session.</p>
      )}
    </aside>
  );
}
