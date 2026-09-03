import { Reveal } from "@/features/landing/reveal";
import { SectionBackground } from "@/features/landing/section-background";

const STEPS = [
  {
    title: "Real-Time Catalyst Ingestion",
    body: "Alpaca News and market quote feeds are ingested with SHA-256 deduplication and evaluated for source credibility, decay, and price impact.",
  },
  {
    title: "Multi-Perspective AI Debate",
    body: "Seven specialist AI agents independently analyze the catalyst across quantitative momentum, SEC balance sheets, supply chains, and macro regimes.",
  },
  {
    title: "Adversarial Risk & Code Gate",
    body: "An adversarial Risk Critic stress-tests the trade before deterministic P0–P5 code verifies position sizing, positive EV, and liquidity boundaries.",
  },
  {
    title: "Execution & ShadowFund Audit",
    body: "Approved orders are submitted via isolated Alpaca CLI paper gateways, while ShadowFund concurrently evaluates rejected alternatives.",
  },
];

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative overflow-hidden bg-[var(--color-bg-panel)] py-28 md:py-36"
    >
      <SectionBackground variant="b" />
      <div className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <Reveal as="div" className="max-w-xl">
          <h2 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
            How it works
          </h2>
          <p className="mt-5 leading-relaxed text-[var(--color-text-muted)]">
            Four governed stages, running continuously, from raw market signal to disciplined
            execution and counterfactual learning.
          </p>
        </Reveal>

        <ol className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <Reveal
              key={step.title}
              as="li"
              delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-6 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:shadow-[0_0_28px_-6px_var(--color-ice)]"
            >
              {/* Connector arrow between steps on wide screens */}
              {i < STEPS.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute right-[-11px] top-1/2 z-10 hidden h-5 w-5 -translate-y-1/2 place-items-center text-[var(--color-ice-dim)] lg:grid"
                >
                  ›
                </span>
              )}
              <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--color-ice-dim)] bg-[var(--color-ice)]/[0.12] font-mono text-sm font-semibold text-[var(--color-ice)]">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-5 text-[1.25rem] font-semibold tracking-tight text-[var(--color-text)]">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)]">
                {step.body}
              </p>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
