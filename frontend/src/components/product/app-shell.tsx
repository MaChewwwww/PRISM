"use client";

import { Menu, X } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

import { PrimaryNav } from "@/components/product/primary-nav";

/**
 * There is intentionally no `<header className="topbar">` in this shell.
 * Brand identity, environment tags, section links, and account actions all
 * live in the always-present, non-scrolling navigation rail (`PrimaryNav`).
 * Routes with a bespoke header (e.g. the Overview dashboard's
 * `.overview-header`) supply their own top-of-page controls rather than
 * duplicating a second header bar.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <button
        type="button"
        className="menu-button rail-menu-button"
        onClick={() => setMenuOpen((value) => !value)}
        aria-expanded={menuOpen}
        aria-controls="primary-navigation"
        aria-label={menuOpen ? "Close navigation" : "Open navigation"}
      >
        {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
      </button>
      <div className="shell-body">
        {menuOpen && (
          <button
            type="button"
            className="rail-scrim"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
          />
        )}
        <PrimaryNav open={menuOpen} onNavigate={() => setMenuOpen(false)} />
        <main id="main-content" className="workspace">
          {children}
        </main>
      </div>
    </div>
  );
}
