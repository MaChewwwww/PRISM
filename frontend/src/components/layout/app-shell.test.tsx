import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/layout/app-shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/stories/acme-earnings-gap",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

describe("AppShell", () => {
  it("FRS-019 maps every story-first workspace route", () => {
    render(
      <AppShell>
        <h1>Workspace content</h1>
      </AppShell>,
    );

    const expectedLinks = [
      ["Overview", "/"],
      ["Decision stories", "/stories"],
      ["Portfolio", "/portfolio"],
      ["Shadow Portfolio", "/alternatives"],
      ["News & catalysts", "/news"],
      ["Market Tracker", "/market-tracker"],
      ["Agents & tools", "/agents"],
      ["Rules", "/rules"],
    ];

    for (const [name, href] of expectedLinks) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
    expect(screen.getByRole("link", { name: "Decision stories" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("link", { name: "System" })).not.toBeInTheDocument();
  });

  it("NFRS-007 exposes keyboard-friendly mobile navigation state", async () => {
    const user = userEvent.setup();
    render(
      <AppShell>
        <h1>Workspace content</h1>
      </AppShell>,
    );
    const trigger = screen.getByRole("button", { name: "Open navigation" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);
    expect(screen.getByRole("button", { expanded: true })).toHaveAccessibleName("Close navigation");
    expect(screen.getByLabelText("Primary navigation")).toHaveAttribute("data-open", "true");
  });
});
