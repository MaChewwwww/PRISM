import { ArrowRight } from "lucide-react";
import "@/app/globals.css";
import Link from "next/link";

import { buttonClasses } from "@/features/landing/button-classes";

// More, varied stars for a livelier field.
const STARS = [
  { top: "10%", left: "16%", s: 3, d: "0s" },
  { top: "20%", left: "40%", s: 2, d: "0.9s" },
  { top: "14%", left: "62%", s: 2, d: "1.6s" },
  { top: "26%", left: "78%", s: 3, d: "0.4s" },
  { top: "34%", left: "24%", s: 2, d: "2.1s" },
  { top: "40%", left: "54%", s: 3, d: "1.2s" },
  { top: "48%", left: "8%", s: 2, d: "0.6s" },
  { top: "52%", left: "88%", s: 3, d: "1.9s" },
  { top: "60%", left: "34%", s: 2, d: "2.4s" },
  { top: "66%", left: "68%", s: 3, d: "0.3s" },
  { top: "72%", left: "18%", s: 2, d: "1.4s" },
  { top: "78%", left: "50%", s: 2, d: "2.7s" },
  { top: "82%", left: "80%", s: 3, d: "0.8s" },
  { top: "30%", left: "92%", s: 2, d: "1.1s" },
  { top: "88%", left: "38%", s: 2, d: "2.2s" },
  { top: "18%", left: "6%", s: 2, d: "1.7s" },
];

export function Hero() {
  return (
    <section
      id="top"
      className="relative flex h-[100svh] max-h-[100svh] flex-col overflow-hidden bg-[var(--color-bg)] pt-20"
    >
      {/* ---- Animated ambient background ---- */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Perspective grid floor — visible teal with GPU-accelerated transform */}
        <div className="absolute -inset-x-[25%] bottom-0 h-[62%] [perspective:640px]">
          <div
            className="absolute inset-0 origin-bottom animate-drift will-change-transform"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(84,125,131,0.45) 1px, transparent 1px), linear-gradient(to bottom, rgba(84,125,131,0.45) 1px, transparent 1px)",
              backgroundSize: "64px 64px",
              maskImage: "linear-gradient(to top, black 10%, transparent 85%)",
              WebkitMaskImage: "linear-gradient(to top, black 10%, transparent 85%)",
            }}
          />
        </div>

        {/* Twinkling stars */}
        {STARS.map((s, i) => (
          <span
            key={i}
            className="absolute animate-twinkle rounded-full bg-white shadow-[0_0_8px_1px_rgba(255,255,255,0.75)]"
            style={{
              top: s.top,
              left: s.left,
              width: `${s.s}px`,
              height: `${s.s}px`,
              animationDelay: s.d,
            }}
          />
        ))}
      </div>

      <div className="relative mx-auto grid w-full max-w-[1500px] flex-1 grid-cols-1 items-center gap-6 px-6 sm:px-10 lg:grid-cols-[0.95fr_1.05fr] lg:px-14">
        <div className="relative z-10 -translate-y-3">
          <h1
            className="text-shine font-display text-[clamp(4rem,12vw,9rem)] leading-[0.86] tracking-tight"
            style={{ filter: "drop-shadow(0 0 80px rgba(84,125,131,0.35))" }}
          >
            PRISM
          </h1>

          <p
            className="mt-5 w-fit animate-rise-slow text-[23px] text-[var(--color-text)]"
            style={{ animationDelay: "0.1s" }}
          >
            One Signal. <span className="text-[var(--primary)]">Multiple Perspectives.</span> Better
            Decisions.
          </p>

          <p
            className="mt-6 max-w-xl animate-rise-slow text-balance text-[20px] leading-relaxed text-[var(--color-text-muted)] sm:text-base"
            style={{ animationDelay: "0.18s" }}
          >
            Autonomous multi-agent trading that analyzes catalysts, stress-tests strategies and
            governs execution.
          </p>

          <div
            className="mt-8 flex flex-wrap items-center gap-4 animate-rise-slow"
            style={{ animationDelay: "0.28s" }}
          >
            <Link
              href="/login"
              className={buttonClasses(
                "glass",
                "min-w-[13rem] overflow-hidden px-5 py-2.5 text-base",
              )}
            >
              <span>Explore Platform</span>
              <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 left-0 w-1/3 animate-sheen bg-white/40 blur-md"
              />
            </Link>
          </div>
        </div>

        {/* ---- Hardware-accelerated 3D PRISM crystal ---- */}
        <div
          className="relative mx-auto aspect-square w-full max-w-[28rem] animate-rise-slow"
          style={{ animationDelay: "0.2s" }}
        >
          {/* Static glow behind the crystal */}
          <div
            aria-hidden="true"
            className="absolute inset-[20%] rounded-full bg-[var(--color-ice)]/25 blur-[60px]"
          />
          {/* Animated WebP (2.1MB) with true alpha transparency and 60fps hardware acceleration */}
          <picture>
            <source srcSet="/logi-animated.webp" type="image/webp" />
            <source srcSet="/logi-animated.gif" type="image/gif" />
            <img
              src="/logi-animated.webp"
              alt="PRISM crystal"
              width={448}
              height={448}
              className="relative h-full w-full transform-gpu object-contain [will-change:transform]"
            />
          </picture>
        </div>
      </div>
    </section>
  );
}
