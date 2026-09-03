import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "@/proxy";

describe("authentication proxy", () => {
  it("FRS-019 redirects unauthenticated workspace requests to login", () => {
    const response = proxy(new NextRequest("http://localhost/portfolio"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/login");
  });

  it("FRS-019 redirects authenticated operators away from login", () => {
    const request = new NextRequest("http://localhost/login", {
      headers: { cookie: "prism_session=test-session" },
    });
    const response = proxy(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/dashboard");
  });

  it("FRS-019 allows authentication APIs and static assets through", () => {
    const authResponse = proxy(new NextRequest("http://localhost/api/auth/login"));
    const assetResponse = proxy(new NextRequest("http://localhost/example.svg"));

    expect(authResponse.headers.get("x-middleware-next")).toBe("1");
    expect(assetResponse.headers.get("x-middleware-next")).toBe("1");
  });
});
