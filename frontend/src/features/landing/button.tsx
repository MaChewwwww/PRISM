"use client";

import {
  cloneElement,
  forwardRef,
  isValidElement,
  type ButtonHTMLAttributes,
  type ReactElement,
} from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: "solid" | "ghost";
}

const CLASSES = (variant: "solid" | "ghost", className?: string) =>
  cn(
    "group relative inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium tracking-tight",
    "transition-all duration-300 ease-[var(--ease-glass)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ice)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)]",
    variant === "solid" &&
      "bg-[var(--color-ice)] text-[#06120f] hover:bg-[var(--color-ice-soft)] hover:shadow-[0_0_28px_-4px_var(--color-ice)] active:scale-[0.97]",
    variant === "ghost" &&
      "border border-[var(--color-line)] text-[var(--color-text)] hover:border-[var(--color-ice-dim)] hover:bg-white/[0.03] active:scale-[0.97]",
    className,
  );

/**
 * Landing button. When `asChild` is set it merges its styling onto the single
 * child element (e.g. an anchor) instead of rendering a <button>, matching the
 * common Slot pattern without pulling in an extra dependency.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "solid", asChild = false, children, ...props }, ref) => {
    const merged = CLASSES(variant, className);

    if (asChild && isValidElement(children)) {
      const child = children as ReactElement<{ className?: string }>;
      return cloneElement(child, {
        className: cn(merged, child.props.className),
        ...props,
      });
    }

    return (
      <button ref={ref} className={merged} {...props}>
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
