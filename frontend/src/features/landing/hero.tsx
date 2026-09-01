import { ArrowRight } from "lucide-react";
import Image from "next/image";
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

// Refraction beams fanning out from the crystal.
const FAN_BEAMS = [
  { rot: "18deg", w: "3px", h: "150%", delay: "0s", opacity: 0.5 },
  { rot: "34deg", w: "2px", h: "135%", delay: "1.1s", opacity: 0.4 },
  { rot: "6deg", w: "4px", h: "160%", delay: "0.5s", opacity: 0.55 },
  { rot: "50deg", w: "2px", h: "120%", delay: "1.8s", opacity: 0.35 },
  { rot: "-8deg", w: "2px", h: "130%", delay: "0.9s", opacity: 0.4 },
];

export function Hero() {
  return (
    <section
      id="top"
      className="relative flex h-[100svh] max-h-[100svh] flex-col overflow-hidden bg-[var(--color-bg)] pt-20"
    >
      {/* ---- Animated ambient background ---- */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Aurora blobs */}
        <div className="absolute right-[6%] top-[14%] h-[600px] w-[600px] animate-aurora-a rounded-full bg-[var(--color-ice)]/[0.20] blur-[130px]" />
        <div className="absolute left-[2%] top-[40%] h-[440px] w-[440px] animate-aurora-b rounded-full bg-[#818CF8]/[0.12] blur-[140px]" />
        <div className="absolute bottom-[6%] left-[38%] h-[380px] w-[380px] animate-aurora-a rounded-full bg-[#38BDF8]/[0.10] blur-[140px]" />

        {/* Big moving beams of light sweeping across the whole background */}
        <div
          className="absolute -top-[20%] left-0 h-[160%] w-[26%] animate-beam-sweep bg-linear-to-b from-transparent via-white/[0.12] to-transparent blur-2xl"
          style={{ "--sweep-rot": "-24deg" } as React.CSSProperties}
        />
        <div
          className="absolute -top-[20%] left-0 h-[160%] w-[18%] animate-beam-sweep bg-linear-to-b from-transparent via-[var(--color-ice)]/[0.14] to-transparent blur-2xl"
          style={{ "--sweep-rot": "-24deg", animationDelay: "5.5s" } as React.CSSProperties}
        />

        {/* Perspective grid floor — visible teal */}
        <div className="absolute inset-x-0 bottom-0 h-[62%] [perspective:640px]">
          <div
            className="absolute inset-0 origin-bottom animate-drift [transform:rotateX(60deg)]"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(84,125,131,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(84,125,131,0.5) 1px, transparent 1px)",
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
            className="absolute animate-twinkle rounded-full bg-white shadow-[0_0_10px_2px_rgba(255,255,255,0.85)]"
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
        <div className="relative z-10">
          <h1
            className="text-shine font-display text-[clamp(4rem,12vw,9rem)] leading-[0.86] tracking-tight"
            style={{ filter: "drop-shadow(0 0 80px rgba(84,125,131,0.35))" }}
          >
            PRISM
          </h1>

          <p
            className="mt-5 w-fit animate-rise-slow rounded-full border border-white/10 border-t-white/20 bg-white/[0.05] px-5 py-2 text-sm text-[var(--color-text)] backdrop-blur-xl"
            style={{ animationDelay: "0.1s" }}
          >
            One signal. Multiple perspectives. Clearer decisions.
          </p>

          <p
            className="mt-6 max-w-lg animate-rise-slow text-balance text-lg leading-relaxed text-[var(--color-text-muted)]"
            style={{ animationDelay: "0.18s" }}
          >
            Autonomous market intelligence that turns news and market reactions into
            evidence-driven, risk-aware perspective.
          </p>

          <div
            className="mt-8 flex flex-wrap items-center gap-4 animate-rise-slow"
            style={{ animationDelay: "0.28s" }}
          >
            <Link
              href="/login"
              className={buttonClasses("glass", "min-w-[15rem] overflow-hidden px-8 py-3.5 text-base")}
            >
              <span>Explore Prism</span>
              <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 left-0 w-1/3 animate-sheen bg-white/40 blur-md"
              />
            </Link>
          </div>
        </div>

        {/* ---- BIG animated PRISM logo with refraction beams ---- */}
        <div
          className="relative mx-auto aspect-square w-full max-w-[42rem] animate-rise-slow lg:w-[108%] lg:-translate-x-[4%] [perspective:1200px]"
          style={{ animationDelay: "0.2s" }}
        >
          {/* Core breathing glow */}
          <div
            aria-hidden="true"
            className="absolute inset-[26%] animate-glow-breathe rounded-full bg-[var(--color-ice)]/50 blur-[100px]"
          />

          {/* Refraction beams fanning out from the crystal center */}
          <div aria-hidden="true" className="absolute inset-0 grid place-items-center">
            {FAN_BEAMS.map((b, i) => (
              <span
                key={i}
                className="absolute origin-bottom animate-beam-fan bg-linear-to-t from-white/60 via-white/10 to-transparent blur-md"
                style={
                  {
                    width: b.w,
                    height: b.h,
                    bottom: "50%",
                    opacity: b.opacity,
                    "--beam-rot": b.rot,
                    animationDelay: b.delay,
                  } as React.CSSProperties
                }
              />
            ))}
          </div>

          {/* Conic shimmer ring — tighter around the crystal */}
          <div
            aria-hidden="true"
            className="absolute inset-[20%] animate-shimmer-conic rounded-full opacity-70"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, rgba(143,179,184,0.4) 40deg, transparent 120deg, transparent 240deg, rgba(84,125,131,0.35) 300deg, transparent 360deg)",
              maskImage:
                "radial-gradient(circle, transparent 60%, black 62%, black 80%, transparent 82%)",
              WebkitMaskImage:
                "radial-gradient(circle, transparent 60%, black 62%, black 80%, transparent 82%)",
            }}
          />

          {/* Rotating halo rings — smaller */}
          <div
            aria-hidden="true"
            className="absolute inset-[18%] animate-spin-slow rounded-full border border-dashed border-[var(--color-ice)]/30"
          />
          <div
            aria-hidden="true"
            className="absolute inset-[28%] animate-spin-rev rounded-full border border-[var(--color-ice)]/20"
          />

          {/* The logo: floats + gently tilts, big teal drop-glow */}
          <div className="relative z-10 flex h-full w-full animate-float-y items-center justify-center [transform-style:preserve-3d]">
            <Image
              src="/logo.png"
              alt="PRISM crystal"
              width={720}
              height={720}
              priority
              className="h-full w-full animate-facet object-contain drop-shadow-[0_40px_100px_rgba(84,125,131,0.6)]"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
