import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentPerspectiveChain } from "./agent-perspective-chain";

describe("AgentPerspectiveChain", () => {
  it("renders durable reconstruction evidence and explicit missing evidence", () => {
    render(
      <AgentPerspectiveChain
        perspectives={[
          {
            agentKey: "news",
            agentName: "News Agent",
            status: "recorded",
            headline: "Day 1 source context",
            summary: "Recorded from the approved evidence excerpt.",
            evidence: ["Blackwell backlog"],
            limitations: ["No original model invocation"],
            occurredAt: "2026-08-31T17:10:25Z",
            provenance: "retrospective_reconstruction",
            sourceTitle: "Day 1 report",
          },
          {
            agentKey: "quantitative",
            agentName: "Quantitative Agent",
            status: "unavailable",
          },
        ]}
      />,
    );

    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.queryByText(/Retrospective/i)).not.toBeInTheDocument();
    expect(screen.getByText("Blackwell backlog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Quantitative Agent" }));
    expect(screen.getByText("No durable decision was recorded.")).toBeInTheDocument();
  });
});
