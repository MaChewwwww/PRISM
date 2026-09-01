"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/features/landing/button";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "#overview", label: "Overview" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#about", label: "About" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 flex justify-center transition-all duration-500 ease-[var(--ease-glass)]",
        "px-4 pt-4",
      )}
    >
      <nav
        className={cn(
          "flex w-full max-w-[1500px] items-center justify-between rounded-full border px-5 py-2.5 transition-all duration-500 ease-[var(--ease-glass)]",
          scrolled
            ? "border-[var(--color-line)] bg-[#0a1011]/80 shadow-[0_8px_40px_-16px_rgba(0,0,0,0.6)] backdrop-blur-xl"
            : "border-transparent bg-transparent",
        )}
      >
        <a href="#top" className="flex items-center gap-2">
          <Image
            src="/logo.png"
            alt="PRISM"
            width={28}
            height={28}
            priority
            className="h-7 w-7 object-contain"
          />
          <span className="font-display text-lg tracking-tight text-[var(--color-text)]">
            PRISM
          </span>
        </a>

        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="group relative rounded-full px-4 py-2 text-sm text-[var(--color-text-muted)] transition-colors duration-300 hover:text-[var(--color-text)]"
              >
                {link.label}
                <span className="pointer-events-none absolute inset-x-4 -bottom-0.5 h-px scale-x-0 bg-[var(--color-ice)] transition-transform duration-300 ease-[var(--ease-glass)] group-hover:scale-x-100" />
              </a>
            </li>
          ))}
        </ul>

        <Button asChild variant="solid" className="px-4 py-2 text-xs md:px-5 md:text-sm">
          <Link href="/login">Log In</Link>
        </Button>
      </nav>
    </header>
  );
}
