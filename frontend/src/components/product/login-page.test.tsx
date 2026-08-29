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
    vi.clearAllMocks();
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
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      const urlStr = String(url);
      if (urlStr.includes("/api/auth/demo-credentials")) {
        return {
          ok: true,
          json: async () => ({
            email: "operator@prism.local",
            password: "prism-staging-2026!",
            environment: "staging",
          }),
        } as Response;
      }
      if (urlStr.includes("/api/auth/login")) {
        return {
          ok: false,
          json: async () => ({ error: "Invalid credentials" }),
        } as Response;
      }
      return { ok: false } as Response;
    });

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "wrong@test.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "badpass" } });
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("handles successful login and navigates to home", async () => {
    const user = userEvent.setup();
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      const urlStr = String(url);
      if (urlStr.includes("/api/auth/demo-credentials")) {
        return {
          ok: true,
          json: async () => ({
            email: "operator@prism.local",
            password: "prism-staging-2026!",
            environment: "staging",
          }),
        } as Response;
      }
      if (urlStr.includes("/api/auth/login")) {
        return {
          ok: true,
          json: async () => ({ ok: true, email: "operator@prism.local" }),
        } as Response;
      }
      return { ok: false } as Response;
    });

    render(<LoginPage />);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(pushMock).toHaveBeenCalledWith("/");
  });
});
