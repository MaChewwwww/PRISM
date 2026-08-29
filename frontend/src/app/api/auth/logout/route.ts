import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true, status: "logged_out" });
  response.cookies.delete("shadowfund_session");
  return response;
}
