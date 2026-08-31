import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MarketTrackerShell } from "@/features/market/market-tracker-shell";
import { isVerifiedTrade, marketActivityKinds } from "@/features/market/market-tracker-types";

describe("MarketTrackerShell", () => {
  it("starts with an explicit deferred, data-empty state", () => {
    render(<MarketTrackerShell nowUtc="2026-08-30 12:00:00" />);

    expect(screen.getByText("Market data not connected")).toBeInTheDocument();
    expect(screen.getByText("Market timeline unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/NVDA|AAPL|MSFT|\$\d/)).not.toBeInTheDocument();
  });

  it("selects all six activity categories by default and supports keyboard toggles", async () => {
    const user = userEvent.setup();
    render(<MarketTrackerShell nowUtc="2026-08-30 12:00:00" />);

    const filters = marketActivityKinds.map(({ label }) =>
      screen.getByRole("button", { name: new RegExp(`^${label}:`, "i") }),
    );
    expect(filters).toHaveLength(6);
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "true");

    await user.click(filters[0]);
    expect(filters[0]).toHaveAttribute("aria-pressed", "false");

    await user.click(screen.getByRole("button", { name: /clear all/i }));
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "false");

    await user.click(screen.getByRole("button", { name: /select all/i }));
    for (const filter of filters) expect(filter).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps timeframe selection local and treats only fills as verified trades", async () => {
    const user = userEvent.setup();
    render(<MarketTrackerShell nowUtc="2026-08-30 12:00:00" />);

    expect(screen.getByRole("button", { name: "1Day" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "15Min" }));
    expect(screen.getByRole("button", { name: "15Min" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Default: 15Min/)).toBeInTheDocument();

    expect(isVerifiedTrade("fill")).toBe(true);
    expect(isVerifiedTrade("proposal")).toBe(false);
    expect(isVerifiedTrade("no_trade")).toBe(false);
    const tradedOnly = screen.getByRole("checkbox", {
      name: /symbols with verified trades only/i,
    });
    expect(tradedOnly).not.toBeChecked();
    await user.click(tradedOnly);
    expect(tradedOnly).toBeChecked();
    expect(screen.getByText(/Verified fills only/)).toBeInTheDocument();
  });
});
