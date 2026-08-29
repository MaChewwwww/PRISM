import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RuleStudio } from "@/features/rules/rule-studio";
import { configurableRules } from "@/features/story/story-data";

describe("RuleStudio", () => {
  it("FRS-004 allows a local draft preview while real activation remains disabled", async () => {
    const user = userEvent.setup();
    render(<RuleStudio rules={configurableRules} />);

    const preview = screen.getByRole("button", { name: "Preview synthetic impact" });
    expect(preview).toBeDisabled();
    await user.type(screen.getAllByLabelText("Proposed value")[0], "4.5");
    expect(preview).toBeEnabled();
    await user.click(preview);
    expect(screen.getByRole("status")).toHaveTextContent("Executable authority createdNone");

    const activate = screen.getByRole("button", { name: "Approve and activate" });
    expect(activate).toBeDisabled();
    expect(activate).toHaveAccessibleDescription(/not connected/);
  });
});
