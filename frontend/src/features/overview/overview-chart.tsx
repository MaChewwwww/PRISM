"use client";

import { useMemo, useState } from "react";
import { X, TrendingUp, Sparkles } from "lucide-react";

import {
  formatCurrency,
  formatSignedPercent,
  percentChange,
  type OverviewPoint,
} from "@/features/overview/overview-adapter";

import type { OverviewChartProps } from "./overview-types";

const PLOT_PADDING_PCT = 8;

export function formatHumanDateTime(rawIso: string): {
  date: string;
  time: string;
  full: string;
} {
  try {
    const d = new Date(rawIso);
    if (isNaN(d.getTime())) {
      const clean = rawIso.replace("T", " ").replace(/\.\d+/, "").slice(0, 19);
      return { date: clean, time: "UTC", full: `${clean} UTC` };
    }
    const date = d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    });
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");
    const seconds = String(d.getUTCSeconds()).padStart(2, "0");
    const time = `${hours}:${minutes}:${seconds} UTC`;
    return {
      date,
      time,
      full: `${date} · ${time}`,
    };
  } catch {
    return { date: rawIso, time: "", full: rawIso };
  }
}

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

  // Gradient area polygon under Active Portfolio path down to chart baseline (y=100)
  const actualAreaPolygon = useMemo(() => {
    if (points.length < 2) return "";
    const top = points.map((point, index) => `${scale.xFor(index)},${scale.yFor(point.actual)}`);
    const firstX = scale.xFor(0);
    const lastX = scale.xFor(points.length - 1);
    return `${firstX},100 ${top.join(" ")} ${lastX},100`;
  }, [points, scale]);

  const gapPolygon = useMemo(() => {
    if (points.length < 2) return "";
    const top = points.map((point, index) => `${scale.xFor(index)},${scale.yFor(point.alt)}`);
    const bottom = points
      .map((point, index) => `${scale.xFor(index)},${scale.yFor(point.actual)}`)
      .reverse();
    return [...top, ...bottom].join(" ");
  }, [points, scale]);

  // Build clean, human-readable x-axis labels adaptively based on date range span
  const xAxisLabels = useMemo(() => {
    if (points.length === 0) return [];
    const labels: Array<{ index: number; label: string }> = [];
    const firstDate = new Date(points[0].date);
    const lastDate = new Date(points[points.length - 1].date);
    const diffDays = Math.abs(lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24);

    const targetCount = Math.min(5, Math.max(2, points.length));
    const step = Math.max(1, Math.floor((points.length - 1) / (targetCount - 1)));
    const indices = new Set<number>();
    for (let i = 0; i < points.length; i += step) {
      indices.add(i);
    }
    indices.add(points.length - 1);

    for (const index of Array.from(indices).sort((a, b) => a - b)) {
      const d = new Date(points[index].date);
      let label = "";
      if (isNaN(d.getTime())) {
        label = points[index].date.slice(0, 10);
      } else if (diffDays <= 2) {
        const month = d.toLocaleDateString("en-US", { month: "short", timeZone: "UTC" });
        const day = d.getUTCDate();
        const hr = String(d.getUTCHours()).padStart(2, "0");
        const min = String(d.getUTCMinutes()).padStart(2, "0");
        label = `${month} ${day} ${hr}:${min}`;
      } else if (diffDays <= 35) {
        label = d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
      } else {
        const month = d.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          timeZone: "UTC",
        });
        const yr = String(d.getUTCFullYear()).slice(2);
        label = `${month} '${yr}`;
      }
      labels.push({ index, label });
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

        {/* Empty state: a ghost chart so it reads as 'a graph will render here'. */}
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

  // Calculate high-level summary metrics for the header
  const latestValue = points[points.length - 1].actual;
  const initialValue = points[0].actual;
  const deltaValue = latestValue - initialValue;
  const deltaPct = initialValue !== 0 ? (deltaValue / initialValue) * 100 : 0;
  const isPositive = deltaValue >= 0;

  return (
    <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] backdrop-blur-xl sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="overview-chart-head flex flex-wrap items-center justify-between gap-3">
            <div>
              <SectionHeading
                icon={TrendingUp}
                title="Active Portfolio path"
                description="Equity performance vs. alternative and benchmark strategies."
              />
            </div>

            {/* Quick summary metrics header */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-xl sm:text-2xl font-bold tracking-tight text-white">
                  {formatCurrency(latestValue)}
                </span>
                <span
                  className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-mono text-xs font-semibold ${
                    isPositive
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                      : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                  }`}
                >
                  {isPositive ? "+" : ""}
                  {formatCurrency(deltaValue)} ({isPositive ? "+" : ""}
                  {deltaPct.toFixed(2)}%)
                </span>
              </div>
              <span className="overview-chart-hint hidden sm:inline-block">
                {defaultSelected ? "Selected point" : "Click a point for details"}
              </span>
            </div>
          </div>

          <div
            className="overview-chart-plot mt-4 min-h-72 w-full [&_*:focus]:outline-none sm:min-h-80"
            role="img"
            aria-label="Active Portfolio, alternative, and benchmark equity paths over the selected date range, with the gap between the portfolio and the best alternative shaded"
          >
            <svg
              className="overview-chart-svg"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                {/* Area Gradient for Active Portfolio */}
                <linearGradient id="overviewActiveAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.32" />
                  <stop offset="45%" stopColor="#547D83" stopOpacity="0.12" />
                  <stop offset="95%" stopColor="#0F172A" stopOpacity="0.0" />
                </linearGradient>

                {/* Line Gradient for Active Portfolio */}
                <linearGradient id="overviewLineGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#38BDF8" />
                  <stop offset="100%" stopColor="#2DD4BF" />
                </linearGradient>
              </defs>

              {/* Horizontal Gridlines */}
              {[15, 35, 55, 75, 95].map((line) => (
                <line
                  key={line}
                  x1={0}
                  y1={line}
                  x2={100}
                  y2={line}
                  className="overview-chart-gridline"
                />
              ))}

              {/* Gap between Alternative and Actual */}
              {gapPolygon && <polygon points={gapPolygon} className="overview-chart-gap" />}

              {/* Shaded Area under Active Portfolio path */}
              {actualAreaPolygon && (
                <polygon
                  points={actualAreaPolygon}
                  fill="url(#overviewActiveAreaGrad)"
                  className="transition-all duration-300 pointer-events-none"
                />
              )}

              {/* Benchmark dashed path */}
              <polyline
                points={benchPath}
                className="overview-chart-line overview-chart-line-bench"
              />

              {/* Alternative dashed path */}
              <polyline points={altPath} className="overview-chart-line overview-chart-line-alt" />

              {/* Active Portfolio solid path */}
              <polyline
                points={actualPath}
                className="overview-chart-line overview-chart-line-actual"
                style={{ stroke: "url(#overviewLineGrad)", strokeWidth: "2" }}
              />

              {/* Vertical Crosshair Line on hover / select */}
              {activeIndex !== null && (
                <line
                  x1={scale.xFor(activeIndex)}
                  y1={0}
                  x2={scale.xFor(activeIndex)}
                  y2={100}
                  stroke="rgba(56, 189, 248, 0.45)"
                  strokeWidth="0.8"
                  strokeDasharray="2 2"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>

            {/* Glowing Active Marker on Active Portfolio Line */}
            {activePoint && activeIndex !== null && (
              <div
                className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-1/2 transition-transform duration-100"
                style={{
                  left: `${scale.xFor(activeIndex)}%`,
                  top: `${scale.yFor(activePoint.actual)}%`,
                }}
              >
                <span className="relative flex h-4 w-4 items-center justify-center">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full border-2 border-slate-900 bg-cyan-300 shadow-[0_0_8px_#38BDF8]" />
                </span>
              </div>
            )}

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
                const formatted = formatHumanDateTime(point.date);
                return (
                  <button
                    type="button"
                    key={`${point.date}-${index}`}
                    className={`overview-chart-point-hit ${isActive ? "active" : ""}`}
                    style={{ left: `${scale.xFor(index)}%` }}
                    onMouseEnter={() => setHoverIndex(index)}
                    onMouseLeave={() => setHoverIndex(null)}
                    onFocus={() => setHoverIndex(index)}
                    onBlur={() => setHoverIndex(null)}
                    onClick={() => selectPoint(index)}
                    aria-pressed={isSelected}
                    aria-label={`${formatted.full}: active portfolio ${formatCurrency(point.actual)}${
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

            {/* Overhauled Human-Readable Tooltip */}
            {activePoint &&
              activeIndex !== null &&
              (() => {
                const formatted = formatHumanDateTime(activePoint.date);
                const xPos = scale.xFor(activeIndex);
                return (
                  <div
                    className="overview-chart-tooltip rounded-xl border border-white/12 bg-slate-900/90 p-3 shadow-2xl backdrop-blur-xl"
                    style={{
                      left: `${xPos}%`,
                      ...(xPos > 68 ? { transform: "translateX(-100%)" } : undefined),
                    }}
                    role="status"
                  >
                    <div className="border-b border-white/10 pb-2 mb-2">
                      <strong className="block text-[13px] font-semibold text-white tracking-tight">
                        {formatted.date}
                      </strong>
                      <span className="font-mono text-[11px] text-[#38BDF8] flex items-center gap-1.5 mt-0.5">
                        <span
                          className="h-1.5 w-1.5 rounded-full bg-[#00D084]"
                          aria-hidden="true"
                        />
                        {formatted.time}
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-4 py-0.5">
                      <span className="text-xs text-[#94A3B8]">Active Portfolio</span>
                      <strong className="overview-nums text-xs font-semibold text-white">
                        {formatCurrency(activePoint.actual)}
                      </strong>
                    </div>
                    <div className="flex items-center justify-between gap-4 py-0.5">
                      <span className="text-xs text-[#94A3B8]">Alternative</span>
                      <span className="overview-nums text-xs font-medium text-[#FBBF24]">
                        {formatCurrency(activePoint.alt)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4 py-0.5">
                      <span className="text-xs text-[#94A3B8]">Benchmark</span>
                      <span className="overview-nums text-xs font-medium text-[#94A3B8]">
                        {formatCurrency(activePoint.bench)}
                      </span>
                    </div>

                    {activePoint.decision && (
                      <div className="mt-2 border-t border-white/10 pt-1.5 flex items-center gap-1.5 text-[11px] text-[#38BDF8]">
                        <Sparkles
                          size={12}
                          className="shrink-0 text-amber-400"
                          aria-hidden="true"
                        />
                        <span className="truncate">{activePoint.decision.title}</span>
                      </div>
                    )}
                  </div>
                );
              })()}
          </div>

          {/* Overhauled Human-Readable X-Axis */}
          <div
            className="overview-chart-x-axis mt-3 border-t border-white/8 pt-3"
            style={{ position: "relative", height: "1.5rem" }}
          >
            {xAxisLabels.map(({ index, label }) => (
              <span
                key={`${index}-${label}`}
                style={{
                  position: "absolute",
                  left: `${scale.xFor(index)}%`,
                  transform: "translateX(-50%)",
                  whiteSpace: "nowrap",
                }}
                className="font-mono text-[11px] text-[#94A3B8]"
              >
                {label}
              </span>
            ))}
          </div>

          {/* Legend */}
          <div className="overview-chart-legend mt-4 flex flex-wrap items-center gap-4 border-t border-white/8 pt-4">
            <span className="overview-legend-item flex items-center gap-2 text-xs text-[#CBD5E1]">
              <span className="h-2 w-5 rounded-full bg-linear-to-r from-[#38BDF8] to-[#2DD4BF] shadow-[0_0_8px_rgba(56,189,248,0.5)]" />
              Active Portfolio (Area)
            </span>
            <span className="overview-legend-item flex items-center gap-2 text-xs text-[#CBD5E1]">
              <span className="h-0.5 w-5 border-t-2 border-dashed border-[#FBBF24]" />
              Alternative
            </span>
            <span className="overview-legend-item flex items-center gap-2 text-xs text-[#CBD5E1]">
              <span className="h-0.5 w-5 border-t-2 border-dotted border-[#64748B]" />
              Benchmark
            </span>
            <span className="overview-legend-item flex items-center gap-2 text-xs text-[#CBD5E1]">
              <span className="h-3 w-4 rounded-xs bg-[#F59E0B]/20 border border-[#F59E0B]/40" />
              Gap vs. alternative
            </span>
          </div>
        </div>

        {/* Selected Point Detail Panel */}
        <aside className="flex shrink-0 flex-col lg:w-80" aria-label="Selected point detail">
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
  const formatted = formatHumanDateTime(point.date);

  return (
    <aside
      className="overview-chart-detail w-full rounded-xl border border-white/10 bg-linear-to-b from-white/8 to-white/3 p-4 shadow-xl backdrop-blur-xl"
      aria-label="Selected point detail"
    >
      <div className="overview-chart-detail-head flex items-start justify-between gap-2 border-b border-white/10 pb-3">
        <div>
          <strong className="block text-base font-semibold text-white tracking-tight">
            {formatted.date}
          </strong>
          <span className="font-mono text-xs text-[#38BDF8] flex items-center gap-1.5 mt-1">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00D084]" aria-hidden="true" />
            {formatted.time}
          </span>
        </div>
        <button
          type="button"
          className="overview-chart-detail-close rounded-md border border-white/10 bg-white/5 p-1.5 text-[#94A3B8] transition hover:bg-white/10 hover:text-white"
          onClick={onClose}
          aria-label="Close chart detail"
        >
          <X size={14} aria-hidden="true" />
        </button>
      </div>

      <dl className="overview-chart-detail-values overview-nums mt-3 grid gap-3">
        <div className="flex items-center justify-between border-b border-white/6 pb-2.5">
          <dt className="text-xs uppercase tracking-wider text-[#94A3B8] font-mono">
            Active Portfolio
          </dt>
          <dd className="text-right">
            <div className="text-sm font-bold text-white">{formatCurrency(point.actual)}</div>
            <span className="text-[11px] font-medium text-emerald-400">
              {formatSignedPercent(actualPct)}
            </span>
          </dd>
        </div>
        <div className="flex items-center justify-between border-b border-white/6 pb-2.5">
          <dt className="text-xs uppercase tracking-wider text-[#94A3B8] font-mono">Alternative</dt>
          <dd className="text-right">
            <div className="text-sm font-semibold text-[#FBBF24]">{formatCurrency(point.alt)}</div>
            <span
              className={`text-[11px] font-medium ${
                altPct >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {formatSignedPercent(altPct)}
            </span>
          </dd>
        </div>
        <div className="flex items-center justify-between border-b border-white/6 pb-2.5">
          <dt className="text-xs uppercase tracking-wider text-[#94A3B8] font-mono">Benchmark</dt>
          <dd className="text-right">
            <div className="text-sm font-semibold text-[#94A3B8]">
              {formatCurrency(point.bench)}
            </div>
            <span
              className={`text-[11px] font-medium ${
                benchPct >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {formatSignedPercent(benchPct)}
            </span>
          </dd>
        </div>
      </dl>

      {point.decision && (
        <div className="overview-chart-detail-decision mt-3 rounded-lg border border-white/8 bg-white/4 p-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#64748B]">
            Decision Event
          </span>
          <p className="overview-chart-detail-decision-title mt-1 text-xs font-semibold text-white line-clamp-2">
            {point.decision.title}
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span className="rounded bg-white/10 px-1.5 py-0.5 text-[11px] font-mono text-[#CBD5E1]">
              {point.decision.symbol}
            </span>
            <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[11px] font-mono text-emerald-400 border border-emerald-500/20">
              {point.decision.outcome.toUpperCase()}
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
