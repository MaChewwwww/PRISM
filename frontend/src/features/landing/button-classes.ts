import { cn } from "@/lib/utils";

export type ButtonVariant = "solid" | "ghost" | "glass";

/**
 * Shared PRISM CTA styling. Plain module (no "use client") so it can be used by
 * both server and client components. Applied directly to a Next.js <Link> for
 * reliable navigation, or by the <Button> client component for actions.
 */
export function buttonClasses(variant: ButtonVariant = "solid", className?: string) {
  return cn(
    "group relative inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold tracking-tight whitespace-nowrap",
    "transition-all duration-300 ease-[var(--ease-glass)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ice)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)] active:scale-[0.97]",
    variant === "glass" &&
      "border border-[var(--color-ice)]/40 border-t-white/25 bg-linear-to-b from-[var(--color-ice)]/30 to-[var(--color-ice)]/10 text-[var(--color-text)] backdrop-blur-xl shadow-[0_8px_32px_-8px_rgba(84,125,131,0.5)] hover:from-[var(--color-ice)]/45 hover:to-[var(--color-ice)]/20 hover:border-[var(--color-ice)]/60 hover:shadow-[0_0_36px_-4px_var(--color-ice)]",
    variant === "solid" &&
      "bg-[var(--color-ice)] text-[#06120f] hover:bg-[var(--color-ice-soft)] hover:shadow-[0_0_28px_-4px_var(--color-ice)]",
    variant === "ghost" &&
      "border border-white/10 border-t-white/20 bg-white/[0.04] text-[var(--color-text)] backdrop-blur-xl hover:border-[var(--color-ice)]/40 hover:bg-white/[0.07]",
    className,
  );
}
