import { NextResponse } from "next/server";

export async function GET() {
  const email =
    process.env.AUTH_EMAIL ?? process.env.NEXT_PUBLIC_AUTH_EMAIL ?? "operator@prism.local";
  const password =
    process.env.AUTH_PASSWORD ?? process.env.NEXT_PUBLIC_AUTH_PASSWORD ?? "prism-staging-2026!";
  const environment = process.env.ENVIRONMENT ?? "staging";

  return NextResponse.json({
    email,
    password,
    environment,
  });
}
