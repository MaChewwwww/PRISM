"use client";

import { useMemo, useState } from "react";
import { X, TrendingUp } from "lucide-react";

import {
  formatCurrency,
  formatSignedPercent,
  percentChange,
  type OverviewPoint,
} from "@/features/overview/overview-adapter";

import type { OverviewChartProps } from "./overview-types";

const PLOT_PADDING_PCT = 8;

function SectionHeading({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof TrendingUp;
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

  // Build clean x-axis labels (avoid crowding) - moved before early return to follow Rules of Hooks
  const xAxisLabels = useMemo(() => {
    if (points.length === 0) return [];
    const labels: Array<{ index: number; label: string }> = [];
    const interval = Math.max(1, Math.ceil(points.length / 6));
    let lastShownMonth = "";

    for (let i = 0; i < points.length; i++) {
      if (i === 0 || i === points.length - 1 || i % interval === 0) {
        const [year, month] = points[i].date.split("-").slice(0, 2);
        const monthStr = new Date(2000, parseInt(month) - 1).toLocaleDateString("en-US", {
          month: "short",
        });
        const label = `${monthStr} '${year.slice(2)}`;
        // Avoid showing the exact same month twice in a row
        if (label !== lastShownMonth) {
          labels.push({ index: i, label });
          lastShownMonth = label;
        }
      }
    }
    return labels;
  }, [points]);

  const activeIndex = selected ? selected.index : hoverIndex;
  const activePoint = activeIndex !== null ? points[activeIndex] : null;

  // Default to last point if not selected
  const defaultSelected =
    selected ||
    (points.length > 0 ? { point: points[points.length - 1], index: points.length - 1 } : null);

  if (points.length === 0) {
    return (
      <div
        className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] backdrop-blur-xl sm:p-6"
        aria-labelledby="overview-chart-title"
      >
        <div className="overview-chart-head">
          <SectionHeading
            icon={TrendingUp}
            title="Active Portfolio Path"
            description="Equity Performance vs. Alternative and Benchmark Strategies."
          />
        </div>

        {/* Empty state: a ghost chart so it reads as "a graph will render here". */}
        <div
          className="overview-chart-plot overview-chart-empty mt-4 min-h-72 w-full sm:min-h-80"
          role="img"
          aria-label="Active Portfolio path awaiting recorded observations"
        >
          <svg
            className="overview-chart-svg"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
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
            {/* Muted ghost line + soft area, animated shimmer */}
            <polygon
              points="0,72 16,60 32,66 48,48 64,54 80,38 100,44 100,100 0,100"
              className="overview-chart-empty-area"
            />
            <polyline
              points="0,72 16,60 32,66 48,48 64,54 80,38 100,44"
              className="overview-chart-empty-line"
            />
          </svg>
          <div className="overview-chart-empty-overlay">
            <span className="overview-chart-empty-badge">
              <TrendingUp size={13} aria-hidden="true" />
              Awaiting observations
            </span>
            <p>
              No portfolio observations in this date range yet. The equity path will render here
              once data is recorded.
            </p>
          </div>
        </div>
      </div>
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
    <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] backdrop-blur-xl sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="overview-chart-head">
            <SectionHeading
              icon={TrendingUp}
              title="Active Portfolio path"
              description="Equity performance vs. alternative and benchmark strategies."
            />
            <span className="overview-chart-hint">
              {defaultSelected ? "Selected point" : "Click a point for details"}
            </span>
          </div>

          <div
            className="overview-chart-plot mt-4 min-h-72 w-full flex-1 [&_*:focus]:outline-none sm:min-h-80"
            role="img"
            aria-label="Active Portfolio, alternative, and benchmark equity paths over the selected date range, with the gap between the portfolio and the best alternative shaded"
          >
            <svg
              className="overview-chart-svg"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
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

          <div
            className="overview-chart-x-axis mt-3 border-t border-white/8 pt-3"
            style={{ position: "relative", height: "1.4rem" }}
          >
            {xAxisLabels.map(({ index, label }) => (
              <span
                key={`${index}`}
                style={{
                  position: "absolute",
                  left: `${scale.xFor(index)}%`,
                  transform: "translateX(-50%)",
                }}
              >
                {label}
              </span>
            ))}
          </div>

          <div className="overview-chart-legend mt-4 border-t border-white/8 pt-4">
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
        </div>

        <aside
          className="flex shrink-0 flex-col rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/8 to-white/3 p-4 shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] lg:w-72"
          aria-label="Selected point detail"
        >
          {defaultSelected && (
            <ChartDetailPanel point={defaultSelected.point} onClose={() => onSelect(null)} />
          )}
        </aside>
      </div>
    </div>
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
    </aside>
  );
}
