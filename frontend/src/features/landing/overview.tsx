import { GitBranch, Layers, Radar, ShieldCheck } from "lucide-react";

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
      <SectionBackground variant="a" grid={false} />
      <div className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        {/* ---- Centered heading block ---- */}
        <Reveal as="div" className="mx-auto max-w-8xl text-center">
          <p className="font-mono text-[16px] font-semibold uppercase tracking-[0.2em] text-[var(--color-ice)]">
            What PRISM does
          </p>
          <h2 className="mt-4 font-display text-4xl leading-[1.12] tracking-tight text-[var(--color-text)] md:text-[3.25rem]">
            One Signal. <span className="text-[var(--primary)]">Multiple Perspectives.</span> Better
            Decisions.
          </h2>
          <p className="mx-auto mt-6 max-w-8xl text-balance text-lg leading-relaxed text-[var(--color-text-muted)]">
            A breaking headline isn&rsquo;t a trade thesis. PRISM turns real-time catalysts into
            autonomous, multi-agent, risk-tested, <br />
            mathematically authorized paper trades.
          </p>
        </Reveal>

        {/* ---- Feature card row ---- */}
        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature, i) => (
            <Reveal
              key={feature.title}
              as="article"
              delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-7 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:border-t-white/25"
            >
              {/* Ambient accent bloom on hover */}
              <span
                aria-hidden="true"
                className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-40"
                style={{ background: feature.accent }}
              />

              {/* Glass icon tile */}
              <span
                aria-hidden="true"
                className="grid h-11 w-11 place-items-center rounded-md border border-white/10 border-t-white/20 bg-white/[0.04] backdrop-blur-xl transition-transform duration-500 ease-[var(--ease-glass)] group-hover:-translate-y-0.5 group-hover:scale-105"
                style={{
                  boxShadow: `inset 0 0 0 1px ${feature.accent}33`,
                  color: feature.accent,
                }}
              >
                <feature.icon className="h-5 w-5" strokeWidth={1.75} />
              </span>

              <h3 className="mt-10 text-[16px] font-semibold tracking-tight text-[var(--color-text)]">
                {feature.title}
              </h3>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--color-text-muted)]">
                {feature.body}
              </p>

              {/* Bottom divider line */}
              <span
                aria-hidden="true"
                className="mt-auto block h-px w-full bg-linear-to-r from-white/15 to-transparent"
                style={{ marginTop: "1.75rem" }}
              />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
