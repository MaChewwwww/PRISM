"use client";

import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  as?: ElementType;
  delay?: 1 | 2 | 3 | 4;
  className?: string;
}

/**
 * Wraps children in an element that fades/rises into place the first time
 * it crosses into the viewport. Respects prefers-reduced-motion via CSS
 * (see [data-reveal] rules in globals.css).
 */
export function Reveal({ children, as: Tag = "div", delay, className }: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // If IntersectionObserver is unavailable, just show the content.
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    // Reveal immediately if the element is already within the viewport at mount
    // (e.g. sections high on the page before the observer's first callback).
    const rect = node.getBoundingClientRect();
    const vh = window.innerHeight || document.documentElement.clientHeight;
    if (rect.top < vh && rect.bottom > 0) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as React.Ref<HTMLElement>}
      data-reveal=""
      data-reveal-delay={delay}
      data-visible={visible}
      className={className}
    >
      {children}
    </Tag>
  );
}
