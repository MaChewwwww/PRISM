"use client";

import { Lock, ShieldCheck, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = (await res.json()) as { ok?: boolean; error?: string };

      if (!res.ok || !data.ok) {
        setError(data.error ?? "Invalid credentials. Please verify your email and password.");
        setLoading(false);
        return;
      }

      router.push("/");
      router.refresh();
    } catch {
      setError("An unexpected network error occurred. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="app-shell flex min-h-screen flex-col">
      <header className="topbar">
        <div className="wordmark">
          <span aria-hidden="true">PR</span>
          <strong>PRISM</strong>
        </div>
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" />
          <span>Paper Only</span>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-md border border-[var(--border)] bg-[var(--card)] p-8 shadow-sm">
          <div className="mb-6">
            <p className="eyebrow">PRISM · One signal. Multiple perspectives. Better decisions.</p>
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--foreground)]">
              Sign in
            </h1>
            <p className="mt-1.5 text-xs text-[var(--muted-foreground)]">
              Continue to your decision stories, paper portfolio, and simulated alternatives.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2.5 border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
            >
              <span className="font-semibold">Error:</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-medium text-[var(--foreground)]"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                name="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-medium text-[var(--foreground)]"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                name="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none"
              />
            </div>

            <p className="rounded-md border border-[var(--border)] bg-[var(--surface-raised)]/60 p-3 text-xs text-[var(--muted-foreground)]">
              Use the operator credentials supplied through the environment owner. PRISM never
              displays or pre-fills configured passwords.
            </p>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 flex w-full items-center justify-center gap-2 bg-[var(--primary)] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Sign in</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-6 border-t border-[var(--border)] pt-4">
            <div className="flex items-center gap-2 text-[0.7rem] text-[var(--muted-foreground)]">
              <UserCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>
                Authentication is live. All product stories beyond sign-in use illustrative demo
                data.
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
