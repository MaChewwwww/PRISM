import { Reveal } from "@/features/landing/reveal";

const STEPS = [
  {
    title: "Prism listens",
    body: "Filings, wire headlines, transcripts, and live price action are pulled in continuously across the names you track.",
  },
  {
    title: "Agents draft a read",
    body: "A panel of specialised agents each build an independent case — bullish, bearish, and neutral — grounded in the same source evidence.",
  },
  {
    title: "The panel is weighed",
    body: "Prism scores each read for confidence and conflict, so agreement and disagreement across the panel are both visible.",
  },
  {
    title: "You get the perspective, not just the answer",
    body: "The final view ships with its sources attached, ready to check, challenge, or act on in seconds.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative bg-[var(--color-bg-panel)] py-28 md:py-36">
      <div className="mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        <Reveal as="div" className="max-w-lg">
          <h2 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-5xl">
            How it works
          </h2>
          <p className="mt-5 leading-relaxed text-[var(--color-text-muted)]">
            Four steps, running continuously, from raw signal to a
            perspective you can act on.
          </p>
        </Reveal>

        <Reveal as="ol" className="group relative mt-16 space-y-14">
          <span
            aria-hidden="true"
            className="absolute left-[15px] top-2 hidden h-[calc(100%-2rem)] w-px origin-top scale-y-0 bg-gradient-to-b from-[var(--color-ice)] via-[var(--color-ice-dim)] to-transparent transition-transform duration-[1400ms] ease-[var(--ease-glass)] group-data-[visible=true]:scale-y-100 sm:block"
          />
          {STEPS.map((step, i) => (
            <li key={step.title} className="relative flex gap-6 sm:pl-0">
              <span
                className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--color-ice-dim)] bg-[var(--color-bg-panel)] text-sm text-[var(--color-ice)] transition-colors duration-500"
                style={{ transitionDelay: `${i * 120}ms` }}
              >
                {i + 1}
              </span>
              <div className="pt-0.5">
                <h3 className="text-lg font-medium tracking-tight text-[var(--color-text)]">
                  {step.title}
                </h3>
                <p className="mt-2 max-w-md leading-relaxed text-[var(--color-text-muted)]">
                  {step.body}
                </p>
              </div>
            </li>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
