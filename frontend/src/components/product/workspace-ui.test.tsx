import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DemoDataNotice, DisabledAction } from "@/components/product/workspace-ui";

describe("workspace placeholder controls", () => {
  it("FRS-019 identifies fixture data as non-live", () => {
    render(<DemoDataNotice />);
    expect(screen.getByRole("note")).toHaveTextContent("No provider request was made");
  });

  it("FRS-005 keeps future authority actions disabled with a reason", () => {
    render(<DisabledAction label="Execute paper order" reason="Execution is unavailable." />);
    const button = screen.getByRole("button", { name: "Execute paper order" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription("Execution is unavailable.");
  });
});
