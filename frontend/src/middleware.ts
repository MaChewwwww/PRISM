/**
 * Next.js 16 Turbopack middleware shim.
 *
 * Next.js 16 renamed the middleware convention from `middleware.ts` to
 * `proxy.ts` (exported function: `middleware` -> `proxy`). However, a known
 * Turbopack issue causes `proxy.ts` to be silently omitted from
 * `middleware-manifest.json` in some build environments, leaving the proxy
 * unregistered and unauthenticated routes unprotected.
 *
 * This file re-exports the proxy function under the legacy `middleware` name
 * so the Next.js build system registers it via both resolution paths, ensuring
 * the auth guard is always active regardless of which Turbopack version is
 * running.
 *
 * See: proxy.ts for the actual implementation.
 */
export { proxy as middleware, config } from "@/proxy";
