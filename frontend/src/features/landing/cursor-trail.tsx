"use client";

import { useEffect, useRef } from "react";

const DOT_COUNT = 16;

/**
 * Blueish comet-tail that follows the cursor. A chain of dots each ease toward
 * the position of the one ahead, producing a soft trailing beam. Pointer-events
 * are disabled so it never blocks clicks. Skips touch devices and respects
 * prefers-reduced-motion.
 */
export function CursorTrail() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fine = window.matchMedia("(pointer: fine)").matches;
    if (reduce || !fine) return;

    const container = containerRef.current;
    if (!container) return;

    const dots: HTMLSpanElement[] = [];
    for (let i = 0; i < DOT_COUNT; i += 1) {
      const dot = document.createElement("span");
      dot.className = "cursor-trail-dot";
      const scale = 1 - i / (DOT_COUNT * 1.2);
      dot.dataset.scale = String(scale);
      dot.style.opacity = "0";
      container.appendChild(dot);
      dots.push(dot);
    }

    // Each dot tracks an x/y that chases the point ahead of it.
    const points = dots.map(() => ({ x: 0, y: 0 }));
    const target = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let active = false;
    let raf = 0;

    function onMove(event: MouseEvent) {
      target.x = event.clientX;
      target.y = event.clientY;
      active = true;
    }

    function tick() {
      let leadX = target.x;
      let leadY = target.y;
      for (let i = 0; i < points.length; i += 1) {
        const p = points[i];
        p.x += (leadX - p.x) * 0.35;
        p.y += (leadY - p.y) * 0.35;
        const dot = dots[i];
        const scale = Number(dot.dataset.scale);
        dot.style.transform = `translate(${p.x - 5}px, ${p.y - 5}px) scale(${scale})`;
        dot.style.opacity = active ? String(0.85 * scale) : "0";
        leadX = p.x;
        leadY = p.y;
      }
      raf = window.requestAnimationFrame(tick);
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    raf = window.requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.cancelAnimationFrame(raf);
      dots.forEach((dot) => dot.remove());
    };
  }, []);

  return <div ref={containerRef} aria-hidden="true" />;
}
