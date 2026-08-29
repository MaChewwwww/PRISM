import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/login/page";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}));

describe("Login page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    pushMock.mockReset();
    refreshMock.mockReset();
  });

  it("renders the login form with required fields", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("handles failed login and displays error alert", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ error: "Invalid credentials" }),
    } as Response);

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "wrong@test.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "badpass" } });
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("handles successful login and navigates to home", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, email: "operator@prism.local" }),
    } as Response);

    render(<LoginPage />);
    await user.type(screen.getByLabelText("Email"), "operator@prism.local");
    await user.type(screen.getByLabelText("Password"), "operator-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(pushMock).toHaveBeenCalledWith("/");
  });

  it("does not fetch, display, or prefill configured credentials", () => {
    const fetchMock = vi.spyOn(global, "fetch");
    render(<LoginPage />);

    expect(screen.getByLabelText("Email")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByText(/never displays or pre-fills configured passwords/i)).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
