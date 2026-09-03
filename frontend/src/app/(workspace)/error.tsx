"use client";

import Link from "next/link";
import { LogIn, RotateCcw } from "lucide-react";

import { EmptyState } from "@/components/workspace/workspace-ui";

export default function WorkspaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string; status?: number };
  reset: () => void;
}) {
  const isAuthError =
    error?.status === 401 ||
    error?.message?.toLowerCase().includes("auth") ||
    error?.message?.toLowerCase().includes("session") ||
    error?.message?.toLowerCase().includes("unauthorized") ||
    error?.digest?.toLowerCase().includes("auth");

  return (
    <div className="flex flex-col items-center justify-center space-y-4 py-8">
      <EmptyState
        title={
          isAuthError ? "Session expired or sign-in required" : "Workspace temporarily unavailable"
        }
        detail={
          isAuthError
            ? "Your operator session is expired or unauthenticated. Please sign in to access workspace telemetry and decision pipelines."
            : error?.message ||
              "The requested workspace view could not be rendered. No authorization or execution action was attempted."
        }
      />
      <div className="flex flex-wrap items-center justify-center gap-3">
        {isAuthError ? (
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-md border border-[#547D83]/60 bg-[#547D83]/30 px-4 py-2 text-xs font-semibold text-[#B2D8DC] shadow-sm transition hover:bg-[#547D83]/40 focus-visible:ring-2 focus-visible:ring-[#547D83]"
          >
            <LogIn className="h-3.5 w-3.5" aria-hidden="true" />
            Sign in to PRISM
          </Link>
        ) : (
          <button
            className="retry-button inline-flex items-center gap-2 rounded-md border px-4 py-2 text-xs font-semibold"
            type="button"
            onClick={reset}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Try again
          </button>
        )}
        <Link
          href="/login"
          className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-[#94A3B8] transition hover:bg-white/10 hover:text-white"
        >
          Return to login
        </Link>
      </div>
    </div>
  );
}
