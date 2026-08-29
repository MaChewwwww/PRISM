import { NextResponse } from "next/server";

const judgeEnvironments = new Set(["staging", "production"]);

function judgeCredentials() {
  const environment = (process.env.ENVIRONMENT ?? "development").toLowerCase();
  const email = process.env.AUTH_EMAIL?.trim();
  const password = process.env.AUTH_PASSWORD;
  const examplePassword =
    !password ||
    password === "prism-development-only" ||
    password === "shadowfund2026!" ||
    password === "shadowfund-staging-2026!" ||
    password.startsWith("replace-") ||
    password.startsWith("your_");
  if (!judgeEnvironments.has(environment) || !email || examplePassword) return null;
  return { email, password };
}

export async function GET() {
  const credentials = judgeCredentials();
  return NextResponse.json({
    enabled: credentials !== null,
    email: credentials?.email ?? null,
  });
}

export async function POST() {
  const credentials = judgeCredentials();
  if (!credentials) {
    return NextResponse.json({ error: "Judge sign-in is unavailable" }, { status: 404 });
  }

  try {
    const baseUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000/api/v1";
    const backendRes = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
      cache: "no-store",
    });

    if (!backendRes.ok) {
      return NextResponse.json(
        { error: "Judge sign-in was rejected by the authentication service" },
        { status: backendRes.status },
      );
    }

    const backendCookie = backendRes.headers.get("set-cookie");
    if (!backendCookie) {
      return NextResponse.json(
        { error: "Authentication service did not create a session" },
        { status: 502 },
      );
    }

    const response = NextResponse.json({ ok: true, email: credentials.email });
    response.headers.set("set-cookie", backendCookie);
    return response;
  } catch {
    return NextResponse.json({ error: "Unable to reach authentication service" }, { status: 503 });
  }
}
