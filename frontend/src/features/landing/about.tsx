import { Reveal } from "@/features/landing/reveal";
import { SectionBackground } from "@/features/landing/section-background";

const STATS = [
  { value: "24/7", label: "Continuous coverage across sessions and time zones" },
  { value: "3", label: "Independent reads weighed for every signal" },
  { value: "<60s", label: "From raw event to a sourced perspective" },
];

export function About() {
  return (
    <section id="about" className="relative overflow-hidden bg-[var(--color-bg)] py-28 md:py-36">
      <SectionBackground variant="a" />
      <div className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-1 gap-16 md:grid-cols-2 md:items-center">
          <Reveal as="div">
            <h2 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
              Built for the moment before the market decides.
            </h2>
            <p className="mt-6 leading-relaxed text-[var(--color-text-muted)]">
              Prism started from a simple frustration: by the time news is fully priced in, the
              useful window has closed. We built a panel of agents that read the same information
              analysts do, argue their cases openly, and hand you the disagreement along with the
              conclusion &mdash; so you&rsquo;re deciding with perspective, not a black-box score.
            </p>
            <p className="mt-4 leading-relaxed text-[var(--color-text-muted)]">
              Every output stays traceable to its source, because a signal you can&rsquo;t check
              isn&rsquo;t one you should trade on.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 md:gap-4">
            {STATS.map((stat, i) => (
              <Reveal
                key={stat.label}
                as="div"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.06] to-white/[0.02] p-6 backdrop-blur-xl transition-all duration-300 ease-[var(--ease-glass)] hover:-translate-y-1 hover:shadow-[0_0_28px_-6px_var(--color-ice)] sm:col-span-1"
              >
                <p className="font-display text-4xl tabular-nums text-[var(--color-ice)] transition-colors duration-500 group-hover:text-[var(--color-ice-soft)]">
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
