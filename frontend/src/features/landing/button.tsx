"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";

import { buttonClasses, type ButtonVariant } from "@/features/landing/button-classes";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

/** Plain <button> for non-navigation actions. For navigation use a Link with buttonClasses(). */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "solid", ...props }, ref) => (
    <button ref={ref} className={buttonClasses(variant, className)} {...props} />
  ),
);
Button.displayName = "Button";
