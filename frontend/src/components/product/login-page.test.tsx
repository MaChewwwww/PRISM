import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("prefills the non-secret judge email without exposing the password", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ enabled: true, email: "judge@prism.local" }),
    } as Response);
    render(<LoginPage />);

    await waitFor(() => expect(screen.getByLabelText("Email")).toHaveValue("judge@prism.local"));
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByText(/password stays server-side/i)).toBeVisible();
  });

  it("uses server-side judge credentials without sending them through the browser", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/api/auth/judge-login") && init?.method !== "POST") {
        return {
          ok: true,
          json: async () => ({ enabled: true, email: "judge@prism.local" }),
        } as Response;
      }
      return { ok: true, json: async () => ({ ok: true }) } as Response;
    });
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.click(await screen.findByRole("button", { name: "Sign in as judge" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/judge-login", { method: "POST" });
    expect(pushMock).toHaveBeenCalledWith("/");
  });
});
