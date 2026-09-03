import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { OrderReceipt } from "@/features/story/monitoring-api";

import { PortfolioOrdersList } from "./portfolio-orders-list";

function makeOrder(i: number, overrides: Partial<OrderReceipt> = {}): OrderReceipt {
  return {
    symbol: `OPT_${i}`,
    strategy: `Strategy ${i}`,
    occurredAt: `2026-09-02T13:${10 + i}:00Z`,
    quantity: `${i + 1} contracts`,
    side: i % 2 === 0 ? "exit" : "entry",
    status: "filled",
    fillPrice: `$${(2.5 + i * 0.1).toFixed(2)}`,
    ...overrides,
  };
}

describe("PortfolioOrdersList pagination and display", () => {
  it("renders empty state when orders list is empty", () => {
    render(<PortfolioOrdersList orders={[]} />);

    expect(screen.getByText("No paper orders submitted in this period.")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("renders order rows without pagination controls when orders count is within page size (<= 5)", () => {
    const orders = [makeOrder(1), makeOrder(2), makeOrder(3)];
    render(<PortfolioOrdersList orders={orders} />);

    expect(screen.getByText("OPT_1")).toBeInTheDocument();
    expect(screen.getByText("OPT_2")).toBeInTheDocument();
    expect(screen.getByText("OPT_3")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("paginates orders and displays navigation when orders count exceeds 5", async () => {
    const user = userEvent.setup();
    const orders = Array.from({ length: 7 }, (_, i) => makeOrder(i + 1));
    render(<PortfolioOrdersList orders={orders} />);

    // Page 1 should display items 1 to 5
    expect(screen.getByText("OPT_1")).toBeInTheDocument();
    expect(screen.getByText("OPT_5")).toBeInTheDocument();
    expect(screen.queryByText("OPT_6")).not.toBeInTheDocument();
    expect(screen.queryByText("OPT_7")).not.toBeInTheDocument();

    expect(screen.getByText("Page 1 of 2 · 7 orders")).toBeInTheDocument();

    const prevButton = screen.getByRole("button", { name: /prev/i });
    const nextButton = screen.getByRole("button", { name: /next/i });

    expect(prevButton).toBeDisabled();
    expect(nextButton).toBeEnabled();

    // Navigate to Page 2
    await user.click(nextButton);

    expect(screen.queryByText("OPT_1")).not.toBeInTheDocument();
    expect(screen.queryByText("OPT_5")).not.toBeInTheDocument();
    expect(screen.getByText("OPT_6")).toBeInTheDocument();
    expect(screen.getByText("OPT_7")).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 2 · 7 orders")).toBeInTheDocument();

    expect(prevButton).toBeEnabled();
    expect(nextButton).toBeDisabled();

    // Navigate back to Page 1
    await user.click(prevButton);

    expect(screen.getByText("OPT_1")).toBeInTheDocument();
    expect(screen.queryByText("OPT_6")).not.toBeInTheDocument();
    expect(screen.getByText("Page 1 of 2 · 7 orders")).toBeInTheDocument();
  });
});
