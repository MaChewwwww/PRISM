"use client";

import { useEffect, useRef } from "react";

const DOT_COUNT = 10;

/**
 * Blueish comet-tail that follows the cursor. A chain of dots each ease toward
 * the position of the one ahead, producing a soft trailing beam. Pointer-events
 * are disabled so it never blocks clicks. Skips touch devices and respects
 * prefers-reduced-motion. Automatically sleeps the RAF loop when cursor is idle.
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

    const points = dots.map(() => ({ x: 0, y: 0 }));
    const target = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let isRunning = false;
    let isMoving = false;
    let trailAlpha = 0;
    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let raf = 0;

    function tick() {
      let leadX = target.x;
      let leadY = target.y;
      let totalDelta = 0;

      // Ease trail alpha toward 1 while moving, toward 0 when stopped
      const targetAlpha = isMoving ? 1 : 0;
      trailAlpha += (targetAlpha - trailAlpha) * (isMoving ? 0.3 : 0.15);

      for (let i = 0; i < points.length; i += 1) {
        const p = points[i];
        const dx = leadX - p.x;
        const dy = leadY - p.y;
        p.x += dx * 0.35;
        p.y += dy * 0.35;
        totalDelta += Math.abs(dx) + Math.abs(dy);

        const dot = dots[i];
        const scale = Number(dot.dataset.scale);
        dot.style.transform = `translate3d(${p.x - 4}px, ${p.y - 4}px, 0) scale(${scale})`;
        dot.style.opacity = String(Math.max(0, trailAlpha * 0.8 * scale));
        leadX = p.x;
        leadY = p.y;
      }

      // If motion stopped and trail has faded out, put loop to sleep
      if (!isMoving && trailAlpha < 0.02 && totalDelta < 0.5) {
        trailAlpha = 0;
        for (let i = 0; i < dots.length; i += 1) {
          dots[i].style.opacity = "0";
        }
        isRunning = false;
        return;
      }

      raf = window.requestAnimationFrame(tick);
    }

    function onMove(event: MouseEvent) {
      target.x = event.clientX;
      target.y = event.clientY;
      isMoving = true;
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        isMoving = false;
      }, 100);

      if (!isRunning) {
        isRunning = true;
        raf = window.requestAnimationFrame(tick);
      }
    }

    function onLeave() {
      isMoving = false;
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);

    return () => {
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
      if (idleTimer) clearTimeout(idleTimer);
      window.cancelAnimationFrame(raf);
      dots.forEach((dot) => dot.remove());
    };
  }, []);

  return <div ref={containerRef} aria-hidden="true" />;
}
