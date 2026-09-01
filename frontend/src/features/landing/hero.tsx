import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/features/landing/button";

export function Hero() {
  return (
    <section
      id="top"
      className="relative flex min-h-[100svh] flex-col overflow-hidden bg-[var(--color-bg)] pt-24"
    >
      {/* Perspective grid floor */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[60%] [perspective:600px]"
      >
        <div
          className="absolute inset-0 origin-bottom animate-drift [transform:rotateX(62deg)]"
          style={{
            backgroundImage:
              "linear-gradient(to right, var(--color-line) 1px, transparent 1px), linear-gradient(to bottom, var(--color-line) 1px, transparent 1px)",
            backgroundSize: "72px 72px",
            maskImage: "linear-gradient(to top, black, transparent)",
            WebkitMaskImage: "linear-gradient(to top, black, transparent)",
          }}
        />
      </div>

      {/* Ambient glow behind the crystal */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[8%] top-[24%] h-[520px] w-[520px] animate-glow-breathe rounded-full bg-[var(--color-ice)]/[0.14] blur-[130px]"
      />
      {/* Secondary drifting glow, upper-left, for depth */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-[6%] top-[12%] h-[300px] w-[300px] animate-float-y rounded-full bg-[var(--color-ice-soft)]/[0.06] blur-[120px]"
      />

      <div className="relative mx-auto grid w-full max-w-[1500px] flex-1 grid-cols-1 items-center gap-10 px-6 sm:px-10 lg:grid-cols-[1.05fr_0.95fr] lg:px-14">
        <div>
          <h1
            className="animate-rise font-display text-[clamp(4rem,12vw,9rem)] leading-[0.86] tracking-tight text-[var(--color-text)]"
            style={{ textShadow: "0 0 60px rgba(84,125,131,0.25)" }}
          >
            PRISM
          </h1>

          {/* Tagline moved up, directly under the wordmark */}
          <p
            className="mt-5 w-fit animate-rise-slow rounded-full border border-[var(--color-line)] bg-[#0a1213]/70 px-5 py-2 text-sm text-[var(--color-text)] backdrop-blur-md"
            style={{ animationDelay: "0.1s" }}
          >
            One signal. Multiple perspectives. Clearer decisions.
          </p>

          <p
            className="mt-6 max-w-lg animate-rise-slow text-balance text-lg leading-relaxed text-[var(--color-text-muted)]"
            style={{ animationDelay: "0.18s" }}
          >
            Autonomous market intelligence that turns news and market reactions
            into evidence-driven, risk-aware perspective.
          </p>

          <div
            className="mt-8 flex flex-wrap items-center gap-4 animate-rise-slow"
            style={{ animationDelay: "0.28s" }}
          >
            <Button asChild variant="solid" className="relative overflow-hidden">
              <Link href="/login">
                Explore Prism
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                {/* Sheen sweep across the CTA */}
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-y-0 left-0 w-1/3 animate-sheen bg-white/30 blur-md"
                />
              </Link>
            </Button>
          </div>
        </div>

        {/* Crystal mark */}
        <div
          className="relative mx-auto aspect-square w-full max-w-md animate-rise-slow [perspective:900px]"
          style={{ animationDelay: "0.2s" }}
        >
          {/* Slowly rotating halo ring */}
          <div
            aria-hidden="true"
            className="absolute inset-[8%] animate-spin-slow rounded-full border border-[var(--color-ice)]/20"
            style={{ borderStyle: "dashed" }}
          />
          <div className="relative h-full w-full animate-float-y [transform-style:preserve-3d]">
            <svg
              viewBox="0 0 320 320"
              className="h-full w-full animate-facet [transform-style:preserve-3d] drop-shadow-[0_30px_70px_rgba(0,0,0,0.6)]"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="facet-a" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="var(--color-ice-soft)" />
                  <stop offset="1" stopColor="var(--color-ice-dim)" />
                </linearGradient>
                <linearGradient id="facet-b" x1="0" y1="1" x2="1" y2="0">
                  <stop offset="0" stopColor="var(--color-ice)" />
                  <stop offset="1" stopColor="var(--color-deep-teal)" />
                </linearGradient>
                <linearGradient id="facet-c" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="var(--color-bg-raised)" />
                  <stop offset="1" stopColor="#040706" />
                </linearGradient>
              </defs>
              <polygon points="160,20 280,140 160,180" fill="url(#facet-a)" opacity="0.92" />
              <polygon points="160,20 160,180 60,150" fill="url(#facet-b)" />
              <polygon points="60,150 160,180 150,290" fill="url(#facet-c)" />
              <polygon
                points="160,180 280,140 190,270 150,290"
                fill="url(#facet-b)"
                opacity="0.85"
              />
              <polygon points="160,20 60,150 40,90" fill="var(--color-ice-soft)" opacity="0.55" />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
