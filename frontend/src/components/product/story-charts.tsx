"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartPoint } from "@/features/story/presentation-api";

type ChartSeriesKey = Exclude<keyof ChartPoint, "date">;

export type SeriesDefinition = {
  key: ChartSeriesKey;
  label: string;
  color: string;
  dashed?: boolean;
};

export function StoryLineChart({
  title,
  description,
  summary,
  data,
  series,
  valuePrefix = "",
}: {
  title: string;
  description: string;
  summary: string;
  data: ChartPoint[];
  series: SeriesDefinition[];
  valuePrefix?: string;
}) {
  const [visibleKeys, setVisibleKeys] = useState<Set<ChartSeriesKey>>(
    () => new Set(series.map((s) => s.key)),
  );

  const toggleKey = (key: ChartSeriesKey) => {
    setVisibleKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) {
          next.delete(key);
        }
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (visibleKeys.size === series.length) {
      setVisibleKeys(new Set([series[0]?.key ?? "chosenPath"]));
    } else {
      setVisibleKeys(new Set(series.map((s) => s.key)));
    }
  };

  const visibleSeries = series.filter((s) => visibleKeys.has(s.key));

  const numericData = data.map((point) => {
    const row: Record<string, number | string | undefined> = { date: point.date };
    for (const s of series) {
      const val = point[s.key];
      row[s.key] = val === undefined || val === null ? undefined : Number(val);
    }
    return row;
  });

  return (
    <figure className="chart-frame" aria-labelledby={`${slug(title)}-title`}>
      <figcaption>
        <div>
          <h3 id={`${slug(title)}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        <strong>{summary}</strong>
      </figcaption>

      {series.length > 1 && (
        <div
          className="chart-series-toggles"
          role="toolbar"
          aria-label="Toggle visible trajectories"
        >
          <span className="chart-series-toggles-label">Trajectories:</span>
          <div className="flex flex-wrap items-center gap-1.5 flex-1">
            {series.map((s) => {
              const isActive = visibleKeys.has(s.key);
              return (
                <button
                  key={s.key}
                  type="button"
                  className="chart-toggle-btn"
                  data-active={isActive ? "true" : "false"}
                  onClick={() => toggleKey(s.key)}
                  aria-pressed={isActive}
                >
                  <span
                    className="chart-toggle-dot"
                    style={{ backgroundColor: s.color }}
                    aria-hidden="true"
                  />
                  <span>{s.label}</span>
                </button>
              );
            })}
          </div>
          <button type="button" className="chart-toggle-action" onClick={toggleAll}>
            {visibleKeys.size === series.length ? "Primary only" : "Select all"}
          </button>
        </div>
      )}

      {data.length > 0 ? (
        <div className="chart-canvas" role="img" aria-label={`${title}. ${summary}`}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <LineChart
              data={numericData}
              margin={{ top: 16, right: 16, bottom: 8, left: 0 }}
              accessibilityLayer
            >
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={70}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface-strong)",
                  border: "1px solid var(--border)",
                  borderRadius: 0,
                  fontSize: "0.75rem",
                }}
                formatter={(value) => `${valuePrefix}${String(value)}`}
              />
              <Legend wrapperStyle={{ fontSize: "0.72rem", paddingTop: "0.75rem" }} />
              {visibleSeries.map((item) => (
                <Line
                  key={item.key}
                  type="monotone"
                  dataKey={item.key}
                  name={item.label}
                  stroke={item.color}
                  strokeWidth={item.key === "chosenPath" ? 2.5 : 2}
                  strokeDasharray={item.dashed ? "6 6" : undefined}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="inline-empty">No chart observations fall inside this date range.</p>
      )}
      <details className="chart-table">
        <summary>View exact values</summary>
        <div className="table-wrap">
          <table>
            <caption>{title} exact fixture values</caption>
            <thead>
              <tr>
                <th scope="col">Observation</th>
                {visibleSeries.map((item) => (
                  <th scope="col" key={item.key}>
                    {item.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((point) => (
                <tr key={point.date}>
                  <th scope="row">{point.date}</th>
                  {visibleSeries.map((item) => (
                    <td key={item.key}>
                      {valuePrefix}
                      {point[item.key] ?? "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

export function StoryBarChart({
  title,
  description,
  summary,
  data,
}: {
  title: string;
  description: string;
  summary: string;
  data: Array<{ label: string; value: string }>;
}) {
  const numericData = data.map((item) => ({ ...item, numericValue: Number(item.value) }));
  return (
    <figure className="chart-frame" aria-labelledby={`${slug(title)}-title`}>
      <figcaption>
        <div>
          <h3 id={`${slug(title)}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        <strong>{summary}</strong>
      </figcaption>
      <div className="chart-canvas compact" role="img" aria-label={`${title}. ${summary}`}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart
            data={numericData}
            layout="vertical"
            margin={{ top: 8, right: 20, bottom: 8, left: 4 }}
            accessibilityLayer
          >
            <CartesianGrid stroke="var(--chart-grid)" horizontal={false} />
            <XAxis
              type="number"
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={80}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "var(--accent-soft)" }}
              contentStyle={{
                background: "var(--surface-strong)",
                border: "1px solid var(--border)",
                borderRadius: 0,
                fontSize: "0.75rem",
              }}
            />
            <Bar dataKey="numericValue" name="Count" fill="var(--primary)" radius={0} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="chart-table">
        <summary>View exact values</summary>
        <ul className="exact-value-list">
          {data.map((item) => (
            <li key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </li>
          ))}
        </ul>
      </details>
    </figure>
  );
}

function slug(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}
