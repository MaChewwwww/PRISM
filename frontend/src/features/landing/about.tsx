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
    <section id="about" className="relative overflow-hidden bg-[var(--color-bg)] py-28 md:py-36">
      <SectionBackground variant="a" />
      <div className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-1 gap-16 md:grid-cols-2 md:items-center">
          <Reveal as="div">
            <h2 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
              Engineered for institutional-grade autonomy.
            </h2>
            <p className="mt-6 leading-relaxed text-[var(--color-text-muted)]">
              PRISM was designed for the Alpaca AI Trading Agents Hackathon to solve a critical flaw in modern algorithmic trading: trusting unconstrained black-box models with capital risk.
            </p>
            <p className="mt-4 leading-relaxed text-[var(--color-text-muted)]">
              Instead of giving an LLM execution keys, PRISM enforces strict separation between AI research and deterministic broker mutation. Every cycle produces an immutable Decision Story with cryptographic SHA-256 digests, mathematical rule traces, and verified paper execution receipts.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-4">
            {STATS.map((stat, i) => (
              <Reveal
                key={stat.label}
                as="div"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-6 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:shadow-[0_0_28px_-6px_var(--color-ice)] sm:col-span-1"
              >
                <p className="font-display text-3xl font-semibold tabular-nums text-[var(--color-ice)] transition-colors duration-500 group-hover:text-[var(--color-ice-soft)]">
                  {stat.value}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)]">
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
