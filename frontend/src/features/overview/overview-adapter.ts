import type { components } from "@/types/api.generated";

export type OverviewRange = "7d" | "1m" | "3m" | "ytd";

export type OverviewDecision = {
  title: string;
  perspective: string;
  outcome: "Positive" | "Neutral" | "Negative";
  ruleResult: "PASS" | "MODIFY" | "FAIL" | "NOT_EVALUATED";
  active: number;
  alternative: number;
  storyId: string;
};

export type OverviewPoint = {
  date: string;
  time: string;
  actual: number;
  alt: number;
  bench: number;
  decision: OverviewDecision | null;
  tokens: number | null;
};

export type OverviewOutcome = {
  label: string;
  count: number;
  color: string;
};

export type OverviewExposure = {
  label: string;
  pct: number;
};

export type OverviewViewModel = {
  points: OverviewPoint[];
  decisions: OverviewDecision[];
  outcomes: OverviewOutcome[];
  exposures: OverviewExposure[];
  recommendations: string[];
};

type Overview = components["schemas"]["Overview"];
type StorySummary = components["schemas"]["StorySummary"];
type ChartPoint = components["schemas"]["ChartPoint"];

const outcomeColors: Record<string, string> = {
  pass: "#00D084",
  modify: "#F59E0B",
  fail: "#FF6B6B",
  no_trade: "#547D83",
  degraded: "#94A3B8",
};

function numeric(value: string | null | undefined) {
  if (!value) return 0;
  const parsed = Number(value.replace(/[^0-9.-]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function decisionOutcome(story: StorySummary): OverviewDecision["outcome"] {
  if (story.outcome === "fail") return "Negative";
  if (story.outcome === "pass") return "Positive";
  return "Neutral";
}

function toDecision(story: StorySummary): OverviewDecision {
  return {
    title: story.title,
    perspective: story.category,
    outcome: decisionOutcome(story),
    ruleResult: story.ruleResult,
    active: numeric(story.chosenPathImpact),
    alternative: numeric(story.bestAlternativeImpact),
    storyId: story.id,
  };
}

function decisionByDate(stories: StorySummary[]) {
  return new Map(stories.map((story) => [story.occurredAt.slice(0, 10), toDecision(story)]));
}

function toPoint(point: ChartPoint, byDate: Map<string, OverviewDecision>): OverviewPoint | null {
  if (!point.chosenPath) return null;
  return {
    date: point.date,
    time: "UTC snapshot",
    actual: numeric(point.chosenPath),
    alt: numeric(point.alternative ?? point.chosenPath),
    bench: numeric(point.benchmark ?? point.chosenPath),
    decision: byDate.get(point.date) ?? null,
    tokens: null,
  };
}

export function adaptOverview(overview: Overview): OverviewViewModel {
  const byDate = decisionByDate(overview.stories);
  const points = overview.portfolio.points
    .map((point) => toPoint(point, byDate))
    .filter((point): point is OverviewPoint => point !== null);

  return {
    points,
    decisions: overview.stories.map(toDecision),
    outcomes: overview.outcomes.map((outcome) => ({
      label: outcome.label.replaceAll("_", " "),
      count: Number(outcome.value) || 0,
      color: outcomeColors[outcome.label] ?? "#547D83",
    })),
    exposures: overview.portfolio.exposure.map((exposure) => ({
      label: exposure.label.replace(/^Illustrative\s+/i, ""),
      pct: numeric(exposure.value),
    })),
    recommendations: overview.recommendations,
  };
}

export function percentChange(base: number, value: number) {
  if (base === 0) return 0;
  return ((value - base) / base) * 100;
}

export function formatCurrency(value: number) {
  return `$${Math.round(value).toLocaleString()}`;
}

export function formatSignedCurrency(value: number) {
  const rounded = Math.round(value);
  return `${rounded >= 0 ? "+" : "-"}$${Math.abs(rounded).toLocaleString()}`;
}

export function formatSignedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}
