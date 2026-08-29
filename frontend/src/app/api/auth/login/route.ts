import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { email, password } = (await request.json()) as { email?: string; password?: string };

    if (!email || !password) {
      return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
    }

    const baseUrl =
      process.env.API_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "http://localhost:8000/api/v1";

    const backendRes = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });

    if (!backendRes.ok) {
      const errData = (await backendRes.json().catch(() => ({}))) as { detail?: string };
      return NextResponse.json(
        { error: errData.detail ?? "Authentication failed" },
        { status: backendRes.status },
      );
    }

    const data = (await backendRes.json()) as { token: string; email: string; expires_at: string };

    const response = NextResponse.json({ ok: true, email: data.email });
    response.cookies.set("shadowfund_session", data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 24 * 60 * 60,
    });

    return response;
  } catch {
    return NextResponse.json({ error: "Unable to reach authentication service" }, { status: 503 });
  }
}
