import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WeeklySummary } from "@/features/story/presentation-api";

import { WeeklySummaryClient } from "./weekly-summary-client";

const summary: WeeklySummary = {
  weekOf: "2026-08-24",
  storiesAnalyzed: 3,
  illustrativeNetPnl: "125.00",
  shadowBeatChosen: 1,
  keyFindings: ["Illustrative evidence only"],
  suggestions: [
    {
      id: "recommendation-1",
      weekOf: "2026-08-24",
      parameterId: "take_profit_pct",
      parameterName: "Take-profit",
      currentValue: "75.00",
      suggestedValue: "80.00",
      allowedMinimum: "75.00",
      allowedMaximum: "100.00",
      confidence: "medium",
      rationale: "A bounded illustrative recommendation.",
      validationState: "within_authorized_bounds",
      manualReviewRequired: true,
    },
  ],
};

describe("WeeklySummaryClient", () => {
  it("keeps bounded recommendations in manual review without an activation action", () => {
    render(<WeeklySummaryClient summary={summary} />);

    expect(screen.getByText("Manual Prescriptive mode")).toBeInTheDocument();
    expect(screen.getByText(/Automatic switching is deferred/)).toBeInTheDocument();
    expect(screen.getByText("75.00 to 100.00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Validate and activate profile/ })).toBeDisabled();
  });
});
