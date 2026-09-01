"use client";

import { ArrowLeft, Lock, Mail, Eye, EyeOff, ShieldCheck, UserCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [judgeLoginAvailable, setJudgeLoginAvailable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/auth/judge-login")
      .then(async (response) => {
        if (!response.ok) return;
        return (await response.json()) as { enabled?: boolean };
      })
      .then((hint) => {
        if (!active || !hint?.enabled) return;
        setJudgeLoginAvailable(true);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
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

        router.push("/dashboard");
        router.refresh();
      } catch {
        setError("An unexpected network error occurred. Please try again.");
        setLoading(false);
      }
    },
    [email, password, router],
  );

  const handleJudgeLogin = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/auth/judge-login", { method: "POST" });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (!res.ok || !data.ok) {
        setError(data.error ?? "Judge sign-in is unavailable.");
        setLoading(false);
        return;
      }
      router.push("/dashboard");
      router.refresh();
    } catch {
      setError("An unexpected network error occurred. Please try again.");
      setLoading(false);
    }
  }, [router]);

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-12">
      {/* Page-scoped styles for the animated shining grid background. */}
      <style>{`
        .login-bg {
          position: fixed;
          inset: 0;
          z-index: 0;
          overflow: hidden;
          pointer-events: none;
        }
        .login-bg::before {
          content: "";
          position: absolute;
          inset: -50%;
          background-image:
            linear-gradient(to right, rgba(84, 125, 131, 0.18) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(84, 125, 131, 0.18) 1px, transparent 1px);
          background-size: 44px 44px, 44px 44px;
          mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, #000 20%, transparent 75%);
          -webkit-mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, #000 20%, transparent 75%);
          animation: login-grid-drift 24s linear infinite;
        }
        .login-bg::after {
          content: "";
          position: absolute;
          inset: -50%;
          background: linear-gradient(
            115deg,
            transparent 30%,
            rgba(84, 125, 131, 0.14) 46%,
            rgba(178, 216, 220, 0.28) 50%,
            rgba(84, 125, 131, 0.14) 54%,
            transparent 70%
          );
          animation: login-shine 7s ease-in-out infinite;
        }
        @keyframes login-grid-drift {
          from { transform: translate(0, 0); }
          to { transform: translate(44px, 44px); }
        }
        @keyframes login-shine {
          0% { transform: translateX(-40%) translateY(-10%); opacity: 0; }
          20% { opacity: 1; }
          80% { opacity: 1; }
          100% { transform: translateX(40%) translateY(10%); opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .login-bg::before,
          .login-bg::after { animation: none; }
        }
        .login-field {
          transition: transform 180ms ease;
        }
        .login-field:focus-within {
          transform: scale(1.03);
          z-index: 1;
        }
        .login-field:focus-within input {
          border-color: var(--primary) !important;
          box-shadow: 0 0 0 3px var(--primary-ghost), 0 0 18px var(--primary-glow);
        }
        .login-field:focus-within svg {
          color: var(--primary);
        }
        @media (prefers-reduced-motion: reduce) {
          .login-field { transition: none; }
          .login-field:focus-within { transform: none; }
        }
      `}</style>

      <div className="login-bg" aria-hidden="true" />

      <main className="relative z-10 w-full max-w-md" aria-labelledby="login-title">
        <Link
          href="/"
          className="mb-5 inline-flex items-center gap-1.5 rounded-sm text-sm text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Link>

        <div
          className="w-full rounded-(--radius-card) border border-(--glass-border) p-8 shadow-[0_8px_32px_rgba(0,0,0,0.37)] sm:p-10"
          style={{ background: "var(--surface-strong)" }}
        >
          <div className="mb-8 text-center">
            <h1
              id="login-title"
              aria-label="Sign in"
              className="inline-flex w-full items-center justify-center gap-2 font-serif text-3xl font-bold tracking-tight text-(--foreground)"
            >
              Login to Prism
              <Image
                src="/logo.png"
                alt="PRISM logo"
                width={50}
                height={50}
                className="inline-block"
              />
            </h1>
            <p className="mt-3 text-xs text-muted-foreground">Enter your details to continue</p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 rounded-(--radius-panel) border border-(--status-loss)/30 bg-(--status-loss)/10 p-3 text-xs text-(--status-loss)"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="login-field relative">
              <label htmlFor="email" className="sr-only">
                Email
              </label>
              <Mail
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors"
                aria-hidden="true"
              />
              <Input
                id="email"
                type="email"
                name="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email Address"
                className="h-12 rounded-(--radius-panel) border-border bg-(--surface-elevated) pl-10 text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <div className="login-field relative">
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <Lock
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors"
                aria-hidden="true"
              />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                name="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="h-12 rounded-(--radius-panel) border-border bg-(--surface-elevated) pl-10 pr-10 text-sm text-foreground placeholder:text-muted-foreground"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-sm text-muted-foreground transition-colors hover:text-primary focus-visible:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>

            {judgeLoginAvailable && (
              <div className="space-y-3">
                <p className="rounded-(--radius-panel) border border-border bg-(--surface-elevated)/60 p-3 text-xs text-muted-foreground">
                  Judge access is ready. The password stays server-side.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  disabled={loading}
                  onClick={handleJudgeLogin}
                  className="h-11 w-full rounded-(--radius-panel) border-primary text-xs font-semibold uppercase tracking-wider text-primary hover:bg-primary/10"
                >
                  <UserCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  Login as a Judge
                </Button>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="h-12 w-full rounded-(--radius-panel) bg-primary text-sm font-semibold text-primary-foreground transition-all hover:bg-(--primary-hover) hover:shadow-[0_0_20px_var(--primary-glow)] disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Signing in...
                </span>
              ) : (
                <>Sign in</>
              )}
            </Button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-xs text-muted-foreground">or continue with</p>
            <div className="mt-4 flex items-center justify-center gap-4">
              <button
                type="button"
                aria-label="Continue with Google"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-(--surface-elevated) text-muted-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              </button>
              <button
                type="button"
                aria-label="Continue with Apple"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-(--surface-elevated) text-muted-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                </svg>
              </button>
              <button
                type="button"
                aria-label="Continue with GitHub"
                className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-(--surface-elevated) text-muted-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7.678 1.855.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                </svg>
              </button>
            </div>
          </div>

          <div className="mt-8 border-t border-border pt-5 text-center">
            <p className="text-xs text-muted-foreground">
              Authentication is live for this workspace.
            </p>
            <p className="mt-2 flex items-center justify-center gap-2 text-[0.7rem] text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              Paper-only execution. Active Portfolio views retain explicit backend provenance.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
