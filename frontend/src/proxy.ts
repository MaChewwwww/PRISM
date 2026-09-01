import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Public routes that never require a session: the marketing landing page ("/")
// and the login page. Everything else is a protected workspace route.
const PUBLIC_PATHS = new Set(["/", "/login"]);

export function proxy(request: NextRequest) {
  const sessionToken = request.cookies.get("prism_session")?.value;
  const { pathname } = request.nextUrl;

  const isLoginPage = pathname === "/login";
  const isPublic = PUBLIC_PATHS.has(pathname);
  const isAuthApi = pathname.startsWith("/api/auth");
  const isStatic =
    pathname.startsWith("/_next") || pathname.startsWith("/favicon.ico") || pathname.includes(".");

  if (isAuthApi || isStatic) {
    return NextResponse.next();
  }

  // Unauthenticated visitors may see public pages; protected routes send them
  // to the login page.
  if (!sessionToken && !isPublic) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // A logged-in operator hitting the login page is sent to the workspace.
  if (sessionToken && isLoginPage) {
    const dashboardUrl = new URL("/dashboard", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
