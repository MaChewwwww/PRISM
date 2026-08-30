"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSignOut() {
    setLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/login");
      router.refresh();
    } catch {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleSignOut}
      disabled={loading}
      className="flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-panel)] border border-[var(--border)] px-2.5 py-2 text-[0.68rem] font-medium uppercase tracking-wider text-[var(--muted-foreground)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--foreground)] disabled:opacity-50"
      aria-label="Sign out of operator console"
    >
      <LogOut className="h-3 w-3" aria-hidden="true" />
      <span>{loading ? "Signing out..." : "Sign out"}</span>
    </button>
  );
}
