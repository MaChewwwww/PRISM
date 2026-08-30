import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AgentPlaygroundModal, TryAgentButton } from "@/features/agents/agent-playground-modal";

describe("AgentPlaygroundModal", () => {
  it("renders when open and displays all 7 specialist agents", () => {
    render(<AgentPlaygroundModal isOpen={true} onClose={() => {}} />);

    expect(screen.getByText("Live Agent Playground")).toBeInTheDocument();
    expect(screen.getByText("CIO Master Synthesizer")).toBeInTheDocument();
    expect(screen.getByText("Fundamental Analysis")).toBeInTheDocument();
    expect(screen.getByText("Quantitative Engine")).toBeInTheDocument();
    expect(screen.getByText("Industry Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Macro Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Market Reaction")).toBeInTheDocument();
    expect(screen.getByText("News Intelligence")).toBeInTheDocument();
  });

  it("handles quick select ticker buttons", async () => {
    const user = userEvent.setup();
    render(<AgentPlaygroundModal isOpen={true} onClose={() => {}} initialSymbol="NVDA" />);

    const tickerInput = screen.getByPlaceholderText("e.g. NVDA") as HTMLInputElement;
    expect(tickerInput.value).toBe("NVDA");

    const aaplButton = screen.getByRole("button", { name: "AAPL" });
    await user.click(aaplButton);

    expect(tickerInput.value).toBe("AAPL");
  });

  it("triggers agent analysis and renders structured result", async () => {
    const user = userEvent.setup();

    const mockResponse = {
      success: true,
      data: {
        schema_version: "1.0",
        verdict: "proceed_to_options_proposal",
        direction: "bullish",
        recommended_structure: "bull_call_spread",
        net_ev_r: "0.45",
        reward_risk_ratio: "2.20",
        composite_opportunity_score: "86.5",
        specialist_scores: {
          reaction_opportunity_score: "85.0",
          quant_momentum_score: "84.0",
          fundamental_quality_score: "90.0",
          sector_health_score: "78.0",
          macro_climate_score: "75.0",
          news_sentiment_score: "85.0",
        },
        evidence_summary: [
          "Quant momentum score is 84/100 with RSI continuation",
          "Fundamental quality score is 90/100 (Piotroski F-Score 8/9)",
        ],
        contradictions: ["Short-term 5-day displacement is elevated"],
        contradiction_analysis: "Short-term stretch is outweighed by robust multi-quarter growth.",
        portfolio_fit: "Semiconductor beta 1.15x fits existing risk parameters.",
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    render(
      <AgentPlaygroundModal
        isOpen={true}
        onClose={() => {}}
        initialAgentId="decision"
        initialSymbol="NVDA"
      />,
    );

    const runButton = screen.getByRole("button", { name: /run agent/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/proceed to options proposal/i)).toBeInTheDocument();
    });

    expect(screen.getByText("+0.45R")).toBeInTheDocument();
    expect(screen.getByText("2.20:1")).toBeInTheDocument();
    expect(screen.getByText("86.5/100")).toBeInTheDocument();
    expect(screen.getByText(/Piotroski F-Score 8\/9/)).toBeInTheDocument();
  });

  it("TryAgentButton toggles modal open and closed", async () => {
    const user = userEvent.setup();
    render(<TryAgentButton label="Try Agent" />);

    const openButton = screen.getByRole("button", { name: /try agent/i });
    expect(screen.queryByText("Live Agent Playground")).not.toBeInTheDocument();

    await user.click(openButton);
    expect(screen.getByText("Live Agent Playground")).toBeInTheDocument();

    const closeButton = screen.getByRole("button", { name: /close modal/i });
    await user.click(closeButton);

    expect(screen.queryByText("Live Agent Playground")).not.toBeInTheDocument();
  });
});
