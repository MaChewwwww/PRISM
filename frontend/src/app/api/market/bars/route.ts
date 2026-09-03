import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

function apiBaseUrl() {
  return process.env.API_INTERNAL_URL ?? "http://localhost:8000/api/v1";
}

export async function GET(req: NextRequest) {
  try {
    const session = (await cookies()).get("prism_session")?.value;
    if (!session) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const symbol = searchParams.get("symbol") ?? "NVDA";
    const timeframe = searchParams.get("timeframe") ?? "1Day";
    const limit = searchParams.get("limit") ?? "30";

    const targetUrl = new URL(`${apiBaseUrl()}/monitoring/market-bars`);
    targetUrl.searchParams.set("symbol", symbol);
    targetUrl.searchParams.set("timeframe", timeframe);
    targetUrl.searchParams.set("limit", limit);

    const response = await fetch(targetUrl.toString(), {
      method: "GET",
      headers: {
        Cookie: `prism_session=${encodeURIComponent(session)}`,
      },
      cache: "no-store",
    });

    const data: unknown = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch market bars", status: response.status },
        { status: response.status },
      );
    }

    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Market data service is temporarily unavailable" },
      { status: 500 },
    );
  }
}
