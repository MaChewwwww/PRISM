import { Radar, GitBranch, ShieldCheck, Layers } from "lucide-react";

import { Reveal } from "@/features/landing/reveal";
import { SectionBackground } from "@/features/landing/section-background";

// Spectral perspective accents (DESIGN.md Section 3.3).
const FEATURES = [
  {
    icon: Radar,
    accent: "#38BDF8",
    title: "Seven Specialist AI Perspectives",
    body: "News, Quantitative, Industry, SEC Fundamental, Macro, Reaction, and Decision agents independently analyze every market event with strict provenance.",
  },
  {
    icon: ShieldCheck,
    accent: "#547D83",
    title: "Adversarial Risk & Deterministic Gate",
    body: "AI produces proposals; deterministic P0–P5 code authorizes execution. Concentration limits, positive EV checks, and stop-losses fail closed.",
  },
  {
    icon: GitBranch,
    accent: "#818CF8",
    title: "ShadowFund Counterfactual Engine",
    body: "Simulates Cash, 0.5x Sizing, Contrarian, and Specialist alternatives concurrently on identical live market data without risking capital.",
  },
  {
    icon: Layers,
    accent: "#10B981",
    title: "Deep Alpaca Ecosystem Integration",
    body: "Powered by alpaca-py for live option chains and isolated Alpaca CLI order mutation over JSON stdin with durable cryptographic receipts.",
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
              One signal. Multiple perspectives. Governed execution.
            </h2>
            <p className="mt-5 max-w-sm text-balance leading-relaxed text-[var(--color-text-muted)]">
              A breaking headline is never a complete trade thesis. PRISM connects real-time catalyst ingestion, multi-agent debate, adversarial risk critique, and mathematical code authorization into an autonomous paper trading platform.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FEATURES.map((feature, i) => (
              <Reveal
                key={feature.title}
                as="article"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group relative overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-6 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:border-t-white/25"
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
