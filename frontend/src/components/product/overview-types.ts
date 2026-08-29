import type { OverviewPoint, OverviewRange } from "@/features/story/overview-data";

export type SelectedPoint = {
  point: OverviewPoint;
  index: number;
};

export type OverviewChartProps = {
  points: OverviewPoint[];
  selected: SelectedPoint | null;
  onSelect: (selection: SelectedPoint | null) => void;
};

export type { OverviewPoint, OverviewRange };
