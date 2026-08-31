import type {
  OverviewDecision,
  OverviewExposure,
  OverviewOutcome,
  OverviewPoint,
  OverviewRange,
} from "@/features/overview/overview-adapter";

export type SelectedPoint = {
  point: OverviewPoint;
  index: number;
};

export type OverviewChartProps = {
  points: OverviewPoint[];
  selected: SelectedPoint | null;
  onSelect: (selection: SelectedPoint | null) => void;
};

export type OverviewDashboardView = {
  points: OverviewPoint[];
  decisions: OverviewDecision[];
  outcomes: OverviewOutcome[];
  exposures: OverviewExposure[];
  recommendations: string[];
};

export type { OverviewDecision, OverviewExposure, OverviewOutcome, OverviewPoint, OverviewRange };
