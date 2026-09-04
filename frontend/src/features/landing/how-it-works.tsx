"use client";

import { useEffect, useRef, useState } from "react";

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

// Vertical placement of each node as a fraction of the timeline band (0 = top,
// 1 = bottom). Produces the zigzag: low, high, low, high.
const NODE_Y = [0.62, 0.28, 0.72, 0.18];

// The four intro lines revealed in strict sequence.
const INTRO_LINES = [
  { kind: "eyebrow" as const, text: "How it works" },
  {
    kind: "lead" as const,
    text: "Four governed stages, running continuously, from raw market signal to disciplined",
  },
  {
    kind: "lead" as const,
    text: "execution and counterfactual learning.",
  },
];

/**
 * Reveals its children one line at a time once the section scrolls into view.
 * Each line only starts after the previous one has finished, using a fixed
 * cadence that matches the CSS transition duration.
 */
function useSequentialReveal(total: number, stepMs = 520) {
  const [shown, setShown] = useState(0);
  const ref = useRef<HTMLDivElement | null>(null);
  const started = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const begin = () => {
      if (started.current) return;
      started.current = true;
      if (prefersReduced) {
        setShown(total);
        return;
      }
      let i = 0;
      const tick = () => {
        i += 1;
        setShown(i);
        if (i < total) window.setTimeout(tick, stepMs);
      };
      window.setTimeout(tick, 120);
    };

    if (typeof IntersectionObserver === "undefined") {
      begin();
      return;
    }
    const rect = node.getBoundingClientRect();
    const vh = window.innerHeight || document.documentElement.clientHeight;
    if (rect.top < vh && rect.bottom > 0) {
      begin();
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          begin();
          observer.disconnect();
        }
      },
      { threshold: 0.2, rootMargin: "0px 0px -10% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [total, stepMs]);

  return { ref, shown };
}

export function HowItWorks() {
  const { ref, shown } = useSequentialReveal(INTRO_LINES.length + STEPS.length);

  return (
    <section
      id="how-it-works"
      className="relative overflow-hidden bg-[var(--color-bg-panel)] py-28 md:py-36"
    >
      <SectionBackground variant="b" grid={false} />
      <div ref={ref} className="relative mx-auto max-w-[1500px] px-6 sm:px-10 lg:px-14">
        {/* ---- Sequentially revealed intro ---- */}
        <div className="max-w-6xl">
          <p
            className="font-mono text-[16px] font-semibold uppercase tracking-[0.2em] text-[var(--color-ice-soft)] transition-all duration-500 ease-[var(--ease-glass)]"
            style={{
              opacity: shown >= 1 ? 1 : 0,
              transform: shown >= 1 ? "translateY(0)" : "translateY(14px)",
            }}
          >
            {INTRO_LINES[0].text}
          </p>
          <p className="mt-3 text-lg leading-relaxed text-[var(--color-text-muted)] md:text-xl">
            <span
              className="block transition-all duration-500 ease-[var(--ease-glass)]"
              style={{
                opacity: shown >= 2 ? 1 : 0,
                transform: shown >= 2 ? "translateY(0)" : "translateY(14px)",
              }}
            >
              {INTRO_LINES[1].text}
            </span>
            <span
              className="block transition-all duration-500 ease-[var(--ease-glass)]"
              style={{
                opacity: shown >= 3 ? 1 : 0,
                transform: shown >= 3 ? "translateY(0)" : "translateY(14px)",
              }}
            >
              {INTRO_LINES[2].text}
            </span>
          </p>
        </div>

        {/* ---- Zigzag timeline ---- */}
        <div className="relative mt-6 hidden lg:block">
          <ZigzagTimeline shownFrom={INTRO_LINES.length} shown={shown} />
        </div>

        {/* ---- Stacked fallback for tablet / mobile ---- */}
        <ol className="mt-16 grid grid-cols-1 gap-10 sm:grid-cols-2 lg:hidden">
          {STEPS.map((step, i) => {
            const visible = shown >= INTRO_LINES.length + i + 1;
            return (
              <li
                key={step.title}
                className="relative pl-16 transition-all duration-500 ease-[var(--ease-glass)]"
                style={{
                  opacity: visible ? 1 : 0,
                  transform: visible ? "translateY(0)" : "translateY(16px)",
                }}
              >
                <span className="absolute left-0 top-0 grid h-11 w-11 place-items-center rounded-full border border-[var(--color-ice-dim)] bg-[var(--color-ice)]/[0.14] font-mono text-base font-semibold text-[var(--color-ice-soft)]">
                  {i + 1}
                </span>
                <h3 className="text-[18px] font-semibold tracking-tight text-[var(--primary)]">
                  {step.title}
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-muted)]">
                  {step.body}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

/**
 * The desktop zigzag: numbered nodes positioned high/low across a band, joined
 * by thin diagonal connectors, each with a caption below/beside it.
 */
function ZigzagTimeline({ shownFrom, shown }: { shownFrom: number; shown: number }) {
  const bandHeight = 240; // px band the nodes travel within
  const captionSpace = 190; // room below the band for the longest caption
  const nodeSize = 64;

  return (
    <div className="relative">
      {/* Connector lines (SVG, behind nodes) */}
      <svg
        aria-hidden="true"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="absolute inset-x-0 top-0 h-[240px] w-full"
      >
        {STEPS.slice(0, -1).map((_, i) => {
          const x1 = ((i + 0.5) / STEPS.length) * 100;
          const x2 = ((i + 1.5) / STEPS.length) * 100;
          const y1 = NODE_Y[i] * 100;
          const y2 = NODE_Y[i + 1] * 100;
          const lineVisible = shown >= shownFrom + i + 2;
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="var(--color-ice-dim)"
              strokeWidth={0.35}
              vectorEffect="non-scaling-stroke"
              style={{
                opacity: lineVisible ? 1 : 0,
                transition: "opacity 0.5s var(--ease-glass)",
              }}
            />
          );
        })}
      </svg>

      {/* Nodes + captions */}
      <div className="relative" style={{ height: bandHeight + captionSpace }}>
        {STEPS.map((step, i) => {
          const visible = shown >= shownFrom + i + 1;
          const leftPct = ((i + 0.5) / STEPS.length) * 100;
          const topPx = NODE_Y[i] * bandHeight - nodeSize / 2;
          return (
            <div
              key={step.title}
              className="absolute w-[22%] transition-all duration-500 ease-[var(--ease-glass)]"
              style={{
                left: `${leftPct}%`,
                top: topPx,
                transform: `translateX(-50%) translateY(${visible ? 0 : 16}px)`,
                opacity: visible ? 1 : 0,
              }}
            >
              {/* Node circle */}
              <div className="mx-auto grid place-items-center">
                <span
                  className="grid place-items-center rounded-full border border-[var(--color-ice-dim)] bg-[var(--color-bg-raised)] font-mono text-lg font-semibold text-[var(--color-ice-soft)] shadow-[0_8px_30px_-12px_rgba(0,0,0,0.8)]"
                  style={{ height: nodeSize, width: nodeSize }}
                >
                  {i + 1}
                </span>
              </div>
              {/* Caption */}
              <div className="mt-4">
                <h3 className="text-[0.95rem] font-semibold tracking-tight text-[var(--primary)]">
                  {step.title}
                </h3>
                <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--color-text-muted)]">
                  {step.body}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
