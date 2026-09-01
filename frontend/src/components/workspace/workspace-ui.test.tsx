import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProvenanceLabel } from "./workspace-ui";

describe("ProvenanceLabel", () => {
  it("labels recorded monitoring data", () => {
    render(<ProvenanceLabel provenance="recorded" />);

    expect(screen.getByText("Recorded PRISM data")).toHaveAttribute("data-provenance", "recorded");
  });

  it("reserves paper and simulation labels for their typed sources", () => {
    const { rerender } = render(<ProvenanceLabel provenance="alpaca_paper" />);
    expect(screen.getByText("Alpaca paper")).toBeInTheDocument();

    rerender(<ProvenanceLabel provenance="shadow" />);
    expect(screen.getByText("ShadowFund")).toBeInTheDocument();
  });
});
