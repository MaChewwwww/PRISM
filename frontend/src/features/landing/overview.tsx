import { Radar, GitBranch, ShieldCheck, Layers } from "lucide-react";

import { Reveal } from "@/features/landing/reveal";
import { SectionBackground } from "@/features/landing/section-background";

// Spectral perspective accents (DESIGN.md Section 3.3).
const FEATURES = [
  {
    icon: Radar,
    accent: "#38BDF8",
    title: "Reads the market as it moves",
    body: "Prism ingests filings, headlines, and price reactions the moment they happen, so a shift in sentiment never sits in a queue.",
  },
  {
    icon: GitBranch,
    accent: "#818CF8",
    title: "Holds more than one view",
    body: "Instead of collapsing news into a single score, Prism keeps the bull, bear, and neutral reads visible side by side.",
  },
  {
    icon: ShieldCheck,
    accent: "#10B981",
    title: "Shows its reasoning",
    body: "Every read links back to the source evidence it was built from, so you can check the reasoning, not just the output.",
  },
  {
    icon: Layers,
    accent: "#F59E0B",
    title: "Weighs risk, not just direction",
    body: "Confidence, volatility, and conflicting signals are surfaced together, so conviction and uncertainty are never confused.",
  },
];

export function Overview() {
  return (
    <section id="overview" className="relative overflow-hidden bg-[var(--color-bg)] py-28 md:py-36">
      <SectionBackground variant="a" />
      <div className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
          <Reveal as="div">
            <p className="font-mono text-[12px] font-semibold uppercase tracking-[0.2em] text-[var(--color-ice)]">
              What PRISM does
            </p>
            <h2 className="mt-3 font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
              Market noise, sorted into perspective.
            </h2>
            <p className="mt-5 max-w-sm text-balance leading-relaxed text-[var(--color-text-muted)]">
              Prism watches the same information every trading desk sees, and turns it into a
              structured, evidence-backed read before the story finishes developing.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FEATURES.map((feature, i) => (
              <Reveal
                key={feature.title}
                as="article"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group relative overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-6 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:border-t-white/25"
                style={{ "--card-accent": feature.accent } as React.CSSProperties}
              >
                {/* Ambient accent bloom on hover */}
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-40"
                  style={{ background: feature.accent }}
                />
                <span
                  aria-hidden="true"
                  className="grid h-10 w-10 place-items-center rounded-md border transition-transform duration-500 ease-[var(--ease-glass)] group-hover:-translate-y-0.5 group-hover:scale-105"
                  style={{
                    borderColor: `${feature.accent}55`,
                    background: `${feature.accent}1f`,
                    color: feature.accent,
                  }}
                >
                  <feature.icon className="h-5 w-5" strokeWidth={1.75} />
                </span>
                <h3 className="mt-5 text-[1.25rem] font-semibold tracking-tight text-[var(--color-text)]">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)]">
                  {feature.body}
                </p>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
