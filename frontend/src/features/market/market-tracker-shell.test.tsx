import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MarketTrackerShell } from "@/features/market/market-tracker-shell";
import { isVerifiedTrade, marketActivityKinds } from "@/features/market/market-tracker-types";

const range = {
  preset: "1m",
  from: "2026-08-01",
  to: "2026-08-29",
  timezone: "UTC",
} as const;

describe("MarketTrackerShell", () => {
  it("starts with an explicit deferred, data-empty state", () => {
    render(<MarketTrackerShell range={range} />);

    expect(screen.getByText("Market data integration is deferred")).toBeInTheDocument();
    expect(screen.getByText("No market bars available")).toBeInTheDocument();
    expect(screen.getByText("No symbols loaded")).toBeInTheDocument();
    expect(screen.getByText(/no symbols, prices, positions, or fills/i)).toBeInTheDocument();
    expect(screen.queryByText(/NVDA|AAPL|MSFT|\$\d/)).not.toBeInTheDocument();
    expect(screen.getByText(/Requested UTC range:/)).toBeInTheDocument();
  });

  it("selects all six activity categories by default and supports keyboard toggles", async () => {
    const user = userEvent.setup();
    render(<MarketTrackerShell range={range} />);

    const filters = marketActivityKinds.map(({ label }) =>
      screen.getByRole("button", { name: new RegExp(`^${label}:`, "i") }),
    );
    expect(filters).toHaveLength(6);
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "true");

    await user.click(filters[0]);
    expect(filters[0]).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("5 of 6 categories selected")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /clear all/i }));
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("0 of 6 categories selected")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /select all/i }));
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps timeframe selection local and treats only fills as verified trades", async () => {
    const user = userEvent.setup();
    render(<MarketTrackerShell range={range} />);

    expect(screen.getByRole("button", { name: "1Day" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "15Min" }));
    expect(screen.getByRole("button", { name: "15Min" })).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByText("Default: 15Min. Values appear after integration."),
    ).toBeInTheDocument();

    expect(isVerifiedTrade("fill")).toBe(true);
    expect(isVerifiedTrade("proposal")).toBe(false);
    expect(isVerifiedTrade("no_trade")).toBe(false);
    const tradedOnly = screen.getByRole("checkbox", {
      name: /symbols with verified trades only/i,
    });
    expect(tradedOnly).not.toBeChecked();
    await user.click(tradedOnly);
    expect(tradedOnly).toBeChecked();
    expect(screen.getByText("Verified fills only")).toBeInTheDocument();
  });
});
