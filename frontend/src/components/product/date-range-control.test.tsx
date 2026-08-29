import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DateRangeControl } from "@/components/product/date-range-control";
import { rangeForPreset } from "@/features/story/date-range";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/stories",
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => new URLSearchParams("outcome=pass"),
}));

describe("DateRangeControl", () => {
  beforeEach(() => replaceMock.mockClear());

  it("FRS-019 writes preset UTC boundaries to URL state", async () => {
    const user = userEvent.setup();
    render(<DateRangeControl range={rangeForPreset("1m", "2026-08-28")} />);
    await user.click(screen.getByRole("button", { name: "7D" }));
    expect(replaceMock).toHaveBeenCalledWith(
      "/stories?outcome=pass&range=7d&from=2026-08-21&to=2026-08-28",
    );
  });

  it("NFRS-007 rejects an inverted custom range accessibly", async () => {
    const user = userEvent.setup();
    render(<DateRangeControl range={rangeForPreset("1m")} />);
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-08-29" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-08-28" } });
    await user.click(screen.getByRole("button", { name: "Apply" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Start date must be on or before");
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
