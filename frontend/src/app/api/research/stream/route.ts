import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

function apiBaseUrl() {
  return process.env.API_INTERNAL_URL ?? "http://localhost:8000/api/v1";
}

export async function POST(req: NextRequest) {
  try {
    const session = (await cookies()).get("prism_session")?.value;
    if (!session) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const body = await req.json();
    const targetUrl = `${apiBaseUrl()}/research/decision/synthesize/stream`;

    const response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `prism_session=${encodeURIComponent(session)}`,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    if (!response.ok || !response.body) {
      return NextResponse.json(
        { error: "Research streaming service unavailable" },
        { status: response.status },
      );
    }

    // Pipe the SSE stream through to the client
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Research streaming service is temporarily unavailable" },
      { status: 500 },
    );
  }
}
