"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

const DANGER = "#FF6B6B";

export function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  async function handleSignOut() {
    setLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/login");
      router.refresh();
    } catch {
      setLoading(false);
      setConfirmOpen(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setConfirmOpen(true)}
        className="flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-panel)] border px-2.5 py-2 text-[0.68rem] font-medium uppercase tracking-wider transition-colors"
        style={{
          borderColor: `${DANGER}40`,
          color: DANGER,
          background: `${DANGER}14`,
        }}
        aria-label="Sign out of operator console"
      >
        <LogOut className="h-3 w-3 shrink-0" aria-hidden="true" />
        <span className="nav-label">Sign out</span>
      </button>

      {confirmOpen && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="signout-title"
          aria-describedby="signout-desc"
        >
          {/* Backdrop */}
          <button
            type="button"
            aria-label="Cancel sign out"
            onClick={() => !loading && setConfirmOpen(false)}
            className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm"
          />

          {/* Dialog card (DESIGN.md Section 5.2 glass) */}
          <div className="relative w-full max-w-sm rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/8 to-white/3 p-6 shadow-[0_12px_40px_-8px_rgba(0,0,0,0.5)] backdrop-blur-xl">
            <div className="flex items-start gap-3">
              <span
                aria-hidden="true"
                className="grid h-9 w-9 shrink-0 place-items-center rounded-md"
                style={{ background: `${DANGER}1f`, color: DANGER }}
              >
                <LogOut className="h-4 w-4" />
              </span>
              <div>
                <h2 id="signout-title" className="text-[15px] font-semibold text-[#F8FAFC]">
                  Sign out?
                </h2>
                <p id="signout-desc" className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
                  Are you sure you want to sign out of the operator console?
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                disabled={loading}
                className="rounded-md border border-white/8 bg-white/5 px-3.5 py-2 text-[13px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-white/16 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSignOut}
                disabled={loading}
                className="rounded-md border px-3.5 py-2 text-[13px] font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] disabled:opacity-50"
                style={{
                  borderColor: `${DANGER}66`,
                  background: `${DANGER}26`,
                  color: DANGER,
                }}
              >
                {loading ? "Signing out..." : "Sign out"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
