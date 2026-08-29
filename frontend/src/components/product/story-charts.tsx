"use client";

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

import type { ChartPoint } from "@/features/story/story-data";

type SeriesKey = "actual" | "alternative" | "benchmark";

type SeriesDefinition = {
  key: SeriesKey;
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
  const numericData = data.map((point) => ({
    date: point.date,
    actual: Number(point.actual),
    alternative: point.alternative === undefined ? undefined : Number(point.alternative),
    benchmark: point.benchmark === undefined ? undefined : Number(point.benchmark),
  }));

  return (
    <figure className="chart-frame" aria-labelledby={`${slug(title)}-title`}>
      <figcaption>
        <div>
          <h3 id={`${slug(title)}-title`}>{title}</h3>
          <p>{description}</p>
        </div>
        <strong>{summary}</strong>
      </figcaption>
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
              {series.map((item) => (
                <Line
                  key={item.key}
                  type="monotone"
                  dataKey={item.key}
                  name={item.label}
                  stroke={item.color}
                  strokeWidth={item.key === "actual" ? 2.5 : 2}
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
                {series.map((item) => (
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
                  {series.map((item) => (
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
