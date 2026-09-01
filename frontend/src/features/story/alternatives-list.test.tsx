import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AlternativeSession } from "@/features/story/monitoring-api";

import { AlternativesList } from "./alternatives-list";

function session(overrides: Partial<AlternativeSession> = {}): AlternativeSession {
  return {
    id: "production-session",
    storyId: "story-1",
    occurredAt: "2026-09-01T12:00:00Z",
    symbol: "NVDA",
    title: "Recorded counterfactual",
    summary: "Recorded counterfactual branches.",
    chosenPathPnl: "$0.00",
    bestBranch: "Cash / no action",
    bestDelta: "$0.00",
    coverage: "100.00%",
    branches: [
      {
        id: "chosen-branch",
        branchKey: "chosen",
        label: "Active Portfolio",
        variation: "Recorded decision path",
        pnl: "$0.00",
        deltaVsChosen: "—",
        drawdown: "$0.00",
        coverage: "100.00%",
        status: "complete",
        chosenPath: true,
      },
    ],
    path: [],
    limitations: [],
    state: "complete",
    sourceMode: "production",
    simulation: null,
    ...overrides,
  };
}

describe("AlternativesList production provenance", () => {
  it("filters simulated sessions and does not render a simulated badge for recorded data", () => {
    render(
      <AlternativesList
        dataMode="recorded"
        sessions={[
          session(),
          session({
            id: "staging-simulation",
            sourceMode: "staging",
            simulation: {
              kind: "historical_options",
              windowStart: "2026-08-24T13:30:00Z",
              windowEnd: "2026-08-27T20:00:00Z",
              cadenceSeconds: 300,
              costModel: "observed_nbbo_touch",
            },
          }),
        ]}
      />,
    );

    expect(screen.getByText("recorded", { exact: true })).toBeInTheDocument();
    expect(screen.queryByText("simulated", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("Historical simulation", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("staging-simulation", { exact: true })).not.toBeInTheDocument();
  });
});
