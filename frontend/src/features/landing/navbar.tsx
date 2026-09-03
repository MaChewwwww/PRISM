"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { buttonClasses } from "@/features/landing/button-classes";
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
          "flex w-full max-w-[1500px] items-center justify-between rounded-full border border-white/8 border-t-white/16 bg-linear-to-b from-white/[0.08] to-white/[0.02] px-5 py-2.5 backdrop-blur-xl transition-all duration-500 ease-[var(--ease-glass)]",
          scrolled
            ? "shadow-[0_8px_40px_-16px_rgba(0,0,0,0.7)] from-white/[0.1] to-white/[0.03]"
            : "shadow-[0_8px_32px_-16px_rgba(0,0,0,0.5)]",
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

        <Link href="/login" className={buttonClasses("glass", "px-5 py-2 text-xs md:text-sm")}>
          Log In
        </Link>
      </nav>
    </header>
  );
}
