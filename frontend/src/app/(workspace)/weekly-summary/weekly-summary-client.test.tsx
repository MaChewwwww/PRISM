import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WeeklySummary } from "@/features/story/monitoring-api";

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
  it("keeps bounded recommendations in manual review and links to the profile editor", () => {
    render(<WeeklySummaryClient summary={summary} />);

    expect(screen.getByText(/Manual Prescriptive mode/)).toBeInTheDocument();
    expect(screen.getByText(/Automatic switching is deferred/)).toBeInTheDocument();
    expect(screen.getByText("75.00 to 100.00")).toBeInTheDocument();

    const applyLink = screen.getByRole("link", { name: /Apply in profile editor/ });
    expect(applyLink).toHaveAttribute(
      "href",
      expect.stringContaining("/rules?apply=take_profit_pct&value=80.00"),
    );
  });
});
