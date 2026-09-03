import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { AlternativeSession } from "@/features/story/monitoring-api";

import { ShadowMultiverseChart } from "./shadow-multiverse-chart";

function mockSession(overrides: Partial<AlternativeSession> = {}): AlternativeSession {
  return {
    id: "session-1",
    storyId: "story-1",
    occurredAt: "2026-09-03T18:18:00Z",
    symbol: "NVDA",
    title: "ShadowFund counterfactual — NVDA",
    summary: "Recorded counterfactual branches from terminal autonomous decision.",
    chosenPathPnl: "$0.00",
    bestBranch: "Contrarian strategy",
    bestDelta: "+$2.00",
    coverage: "100.00%",
    branches: [
      {
        id: "b-chosen",
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
      {
        id: "b-cash",
        branchKey: "cash",
        label: "Stay in cash",
        variation: "Zero-risk baseline",
        pnl: "$0.00",
        deltaVsChosen: "$0.00",
        drawdown: "$0.00",
        coverage: "100.00%",
        status: "complete",
        chosenPath: false,
      },
      {
        id: "b-half",
        branchKey: "half_size",
        label: "Half position (50%)",
        variation: "Conservative sizing",
        pnl: "$0.00",
        deltaVsChosen: "$0.00",
        drawdown: "$0.00",
        coverage: "100.00%",
        status: "complete",
        chosenPath: false,
      },
      {
        id: "b-contra",
        branchKey: "contrarian",
        label: "Contrarian strategy",
        variation: "Thesis reversed",
        pnl: "+$2.00",
        deltaVsChosen: "+$2.00",
        drawdown: "$0.00",
        coverage: "100.00%",
        status: "complete",
        chosenPath: false,
      },
      {
        id: "b-ai",
        branchKey: "ai_alternative",
        label: "Agent alternative",
        variation: "Specialist research",
        pnl: "$0.00",
        deltaVsChosen: "$0.00",
        drawdown: "$0.00",
        coverage: "100.00%",
        status: "complete",
        chosenPath: false,
      },
    ],
    path: [],
    limitations: [],
    state: "complete",
    sourceMode: "production",
    ...overrides,
  };
}

describe("ShadowMultiverseChart", () => {
  it("renders empty state when no sessions or points exist", () => {
    render(<ShadowMultiverseChart sessions={[]} aggregatePath={[]} />);
    expect(
      screen.getByText("No shadow portfolio trajectories fall inside this period."),
    ).toBeInTheDocument();
  });

  it("renders chart header, summary badges, and branch toggle controls", () => {
    const session = mockSession();
    render(<ShadowMultiverseChart sessions={[session]} />);

    expect(screen.getByText("Multiverse Trajectory Comparison")).toBeInTheDocument();
    expect(screen.getByText("Active Return")).toBeInTheDocument();
    expect(screen.getByText("Best Alternative")).toBeInTheDocument();
    expect(screen.getByText("Delta vs Active")).toBeInTheDocument();

    // Verify all 5 branch toggle buttons exist
    expect(screen.getByRole("button", { name: "Active Portfolio" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cash Baseline" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Half Size (50%)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Contrarian Thesis" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI Alternative" })).toBeInTheDocument();
  });

  it("handles toggling branch lines on and off", async () => {
    const user = userEvent.setup();
    const session = mockSession();
    render(<ShadowMultiverseChart sessions={[session]} />);

    const contrarianBtn = screen.getByRole("button", { name: "Contrarian Thesis" });
    expect(contrarianBtn).toHaveAttribute("aria-pressed", "true");

    await user.click(contrarianBtn);
    expect(contrarianBtn).toHaveAttribute("aria-pressed", "false");

    await user.click(contrarianBtn);
    expect(contrarianBtn).toHaveAttribute("aria-pressed", "true");
  });
});
