import Image from "next/image";
import Link from "next/link";

import { Button } from "@/features/landing/button";
import { Reveal } from "@/features/landing/reveal";

export function Footer() {
  return (
    <footer className="relative border-t border-[var(--color-line)] bg-[var(--color-bg-panel)]">
      <Reveal as="div" className="mx-auto max-w-[1500px] px-6 py-24 text-center sm:px-10 lg:px-14">
        <h2 className="font-display text-3xl tracking-tight text-[var(--color-text)] md:text-4xl">
          See the market in more than one dimension.
        </h2>
        <div className="mt-8 flex justify-center">
          <Button asChild variant="solid">
            <Link href="/login">Log In</Link>
          </Button>
        </div>
      </Reveal>

      <div className="mx-auto flex max-w-[1500px] flex-col items-center justify-between gap-4 border-t border-[var(--color-line)] px-6 py-8 text-sm text-[var(--color-text-muted)] sm:flex-row sm:px-10 lg:px-14">
        <div className="flex items-center gap-2">
          <Image
            src="/logo.png"
            alt="PRISM"
            width={24}
            height={24}
            className="h-6 w-6 object-contain"
          />
          <span className="font-display text-base text-[var(--color-text)]">PRISM</span>
        </div>
        <p>© {new Date().getFullYear()} Prism. All rights reserved.</p>
      </div>
    </footer>
  );
}
