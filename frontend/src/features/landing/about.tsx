import { Reveal } from "@/features/landing/reveal";
import { SectionBackground } from "@/features/landing/section-background";

const STATS = [
  { value: "7", label: "Specialist AI perspectives evaluating every market catalyst" },
  { value: "100%", label: "Deterministic code authorization across P0–P5 rules" },
  { value: "232", label: "Continuous autonomous cycles recorded in production" },
  { value: "+$151.71", label: "Net realized return finishing in 100% cash defense" },
];

export function About() {
  return (
    <section
      id="about"
      className="relative flex min-h-[100svh] items-center overflow-hidden bg-[var(--color-bg)] py-24"
    >
      <SectionBackground variant="a" grid={false} />
      <div className="relative mx-auto w-full max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-1 gap-16 md:grid-cols-[1fr_1.15fr] md:items-center lg:gap-24">
          <Reveal as="div">
            <p className="font-mono text-[16px] font-semibold uppercase tracking-[0.2em] text-[var(--color-ice-soft)]">
              About PRISM
            </p>
            <h2 className="mt-3 font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
              Engineered for institutional-grade autonomy.
            </h2>
            <p className="mt-6 leading-relaxed text-[var(--color-text-muted)]">
              PRISM was designed for the Alpaca AI Trading Agents Hackathon to solve a critical flaw
              in modern algorithmic trading: trusting unconstrained black-box models with capital
              risk.
            </p>
            <p className="mt-4 leading-relaxed text-[var(--color-text-muted)]">
              Instead of giving an LLM execution keys, PRISM enforces strict separation between AI
              research and deterministic broker mutation. Every cycle produces an immutable Decision
              Story with cryptographic SHA-256 digests, mathematical rule traces, and verified paper
              execution receipts.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {STATS.map((stat, i) => (
              <Reveal
                key={stat.label}
                as="div"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group flex min-h-[9.5rem] flex-col justify-center rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-7 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:shadow-[0_0_28px_-6px_var(--color-ice)]"
              >
                <p className="font-display text-4xl font-semibold tabular-nums text-[var(--color-ice)] transition-colors duration-500 group-hover:text-[var(--color-ice-soft)]">
                  {stat.value}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-muted)]">
                  {stat.label}
                </p>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
