import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

function apiBaseUrl() {
  return process.env.API_INTERNAL_URL ?? "http://localhost:8000/api/v1";
}

const ACTION_MAP: Record<string, string> = {
  news: "/research/news/analyze",
  quant: "/research/quant/analyze",
  fundamental: "/research/fundamental/analyze",
  industry: "/research/industry/analyze",
  macro: "/research/macro/analyze",
  reaction: "/research/reaction/analyze",
  decision: "/research/decision/synthesize",
};

export async function POST(req: NextRequest) {
  try {
    const session = (await cookies()).get("prism_session")?.value;
    if (!session) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const body: unknown = await req.json();
    if (!body || typeof body !== "object") {
      return NextResponse.json({ error: "Invalid research request" }, { status: 400 });
    }
    const { action, payload } = body as { action?: unknown; payload?: unknown };

    const path = typeof action === "string" ? ACTION_MAP[action] : undefined;
    if (!path) {
      return NextResponse.json({ error: `Unknown research action: ${action}` }, { status: 400 });
    }

    const targetUrl = `${apiBaseUrl()}${path}`;
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `prism_session=${encodeURIComponent(session)}`,
      },
      body: JSON.stringify(payload ?? {}),
      cache: "no-store",
    });

    const data: unknown = await response.json();
    if (!response.ok) {
      const errorBody = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
      const detail = errorBody.detail ?? errorBody.error;
      return NextResponse.json(
        {
          error: typeof detail === "string" ? detail : "Research service error",
          status: response.status,
        },
        { status: response.status },
      );
    }

    return NextResponse.json({ success: true, data });
  } catch {
    return NextResponse.json(
      { error: "Research service is temporarily unavailable" },
      { status: 500 },
    );
  }
}
