import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { buttonClasses } from "@/features/landing/button-classes";
import { Reveal } from "@/features/landing/reveal";

export function Footer() {
  return (
    <footer className="relative flex min-h-[50svh] flex-col overflow-hidden bg-[var(--color-bg)]">
      {/* ---- Perspective grid floor ---- */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 [perspective:720px]">
          <div
            className="absolute inset-0 origin-bottom"
            style={{
              transform: "rotateX(62deg) scale(1.6)",
              backgroundImage:
                "linear-gradient(to right, rgba(84,125,131,0.35) 1px, transparent 1px), linear-gradient(to bottom, rgba(84,125,131,0.35) 1px, transparent 1px)",
              backgroundSize: "56px 56px",
              maskImage: "radial-gradient(ellipse 70% 80% at 50% 50%, black 20%, transparent 80%)",
              WebkitMaskImage:
                "radial-gradient(ellipse 70% 80% at 50% 50%, black 20%, transparent 80%)",
            }}
          />
        </div>
      </div>

      {/* ---- Centered CTA ---- */}
      <Reveal
        as="div"
        className="relative mx-auto flex w-full max-w-[1500px] flex-1 flex-col items-center justify-center px-6 py-20 text-center sm:px-10 lg:px-14"
      >
        <h2 className="font-display text-3xl tracking-tight md:text-[2.75rem]">
          <span className="text-[var(--color-text)]">See the market in </span>
          <span className="text-[var(--color-text-muted)]">more than one dimension.</span>
        </h2>
        <p className="mt-4 text-base text-[var(--color-text-muted)] md:text-lg">
          One signal. <span className="text-[var(--primary)]">Multiple perspectives.</span> Clearer
          decisions.
        </p>
        <div className="mt-8 flex justify-center">
          <Link
            href="/login"
            className={buttonClasses("solid", "min-w-[11rem] px-7 py-3 text-base")}
          >
            <span>Sign Up</span>
            <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
          </Link>
        </div>
      </Reveal>

      {/* ---- Copyright ---- */}
      <div className="relative mx-auto w-full max-w-[1500px] px-6 pb-8 text-center text-xs text-[var(--color-text-muted)] sm:px-10 lg:px-14">
        <p>© {new Date().getFullYear()} Prism. All Rights Reserved.</p>
      </div>
    </footer>
  );
}
