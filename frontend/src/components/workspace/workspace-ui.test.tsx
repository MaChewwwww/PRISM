import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProvenanceLabel } from "./workspace-ui";

describe("ProvenanceLabel", () => {
  it("labels the demonstration snapshot as an illustrative fixture", () => {
    render(<ProvenanceLabel provenance="illustrative_fixture" />);

    expect(screen.getByText("Illustrative fixture")).toHaveAttribute(
      "data-provenance",
      "illustrative_fixture",
    );
  });

  it("reserves paper and simulation labels for their typed sources", () => {
    const { rerender } = render(<ProvenanceLabel provenance="alpaca_paper" />);
    expect(screen.getByText("Alpaca paper")).toBeInTheDocument();

    rerender(<ProvenanceLabel provenance="shadow" />);
    expect(screen.getByText("ShadowFund")).toBeInTheDocument();
  });
});
