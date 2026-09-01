import { Radar, GitBranch, ShieldCheck, Layers } from "lucide-react";
import { Reveal } from "@/features/landing/reveal";

const FEATURES = [
  {
    icon: Radar,
    title: "Reads the market as it moves",
    body: "Prism ingests filings, headlines, and price reactions the moment they happen, so a shift in sentiment never sits in a queue.",
  },
  {
    icon: GitBranch,
    title: "Holds more than one view",
    body: "Instead of collapsing news into a single score, Prism keeps the bull, bear, and neutral reads visible side by side.",
  },
  {
    icon: ShieldCheck,
    title: "Shows its reasoning",
    body: "Every read links back to the source evidence it was built from, so you can check the reasoning, not just the output.",
  },
  {
    icon: Layers,
    title: "Weighs risk, not just direction",
    body: "Confidence, volatility, and conflicting signals are surfaced together, so conviction and uncertainty are never confused.",
  },
];

export function Overview() {
  return (
    <section id="overview" className="relative bg-[var(--color-bg)] py-28 md:py-36">
      <div className="mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-[0.8fr_1.2fr] md:gap-16">
          <Reveal as="div">
            <h2 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
              Market noise, sorted into perspective.
            </h2>
            <p className="mt-5 max-w-sm text-balance leading-relaxed text-[var(--color-text-muted)]">
              Prism watches the same information every trading desk sees, and
              turns it into a structured, evidence-backed read before the
              story finishes developing.
            </p>
          </Reveal>

          <div className="grid grid-cols-1 gap-px overflow-hidden rounded-3xl border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-2">
            {FEATURES.map((feature, i) => (
              <Reveal
                key={feature.title}
                as="article"
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="group relative bg-[var(--color-bg-panel)] p-8 transition-colors duration-500 hover:bg-[var(--color-bg-raised)]"
              >
                <feature.icon
                  className="h-6 w-6 text-[var(--color-ice)] transition-transform duration-500 ease-[var(--ease-glass)] group-hover:-translate-y-0.5 group-hover:scale-110"
                  strokeWidth={1.5}
                />
                <h3 className="mt-5 text-lg font-medium tracking-tight text-[var(--color-text)]">
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
