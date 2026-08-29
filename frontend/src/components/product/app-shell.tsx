"use client";

import {
  BookOpenCheck,
  BriefcaseBusiness,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  Menu,
  Network,
  Newspaper,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";

import { SignOutButton } from "@/components/product/sign-out-button";

const navigation = [
  {
    label: "Understand",
    items: [
      { label: "Overview", icon: LayoutDashboard, href: "/" },
      { label: "Decision stories", icon: Network, href: "/stories" },
    ],
  },
  {
    label: "Compare",
    items: [
      { label: "Portfolio", icon: BriefcaseBusiness, href: "/portfolio" },
      { label: "Alternatives", icon: GitBranch, href: "/alternatives" },
    ],
  },
  {
    label: "Inspect",
    items: [
      { label: "News & catalysts", icon: Newspaper, href: "/news" },
      { label: "Agents & tools", icon: Sparkles, href: "/agents" },
      { label: "Rules", icon: BookOpenCheck, href: "/rules" },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  function isCurrent(href: string) {
    return href === "/" ? pathname === href : pathname.startsWith(href);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="topbar">
        <Link className="wordmark" href="/" aria-label="PRISM decision journal home">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.png"
            alt="PRISM"
            className="h-7 w-7 object-contain drop-shadow-[0_0_8px_rgba(84,125,131,0.5)]"
          />
          <strong>PRISM</strong>
          <small>Decision journal</small>
        </Link>
        <div className="topbar-actions">
          <div className="demo-tag">
            <FlaskConical aria-hidden="true" /> Demo narrative
          </div>
          <div className="environment-tag">
            <span aria-hidden="true" className="animate-prism-pulse" /> Active Paper
          </div>
          <SignOutButton />
          <button
            type="button"
            className="menu-button"
            onClick={() => setMenuOpen((value) => !value)}
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          >
            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
        </div>
      </header>
      <div className="shell-body">
        {menuOpen && (
          <button
            type="button"
            className="rail-scrim"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
          />
        )}
        <aside
          id="primary-navigation"
          className="rail"
          data-open={menuOpen || undefined}
          aria-label="Primary navigation"
        >
          <nav>
            {navigation.map((group) => (
              <div className="nav-group" key={group.label}>
                <p>{group.label}</p>
                {group.items.map(({ label, icon: Icon, href }) => (
                  <Link
                    key={href}
                    href={href}
                    aria-current={isCurrent(href) ? "page" : undefined}
                    onClick={() => setMenuOpen(false)}
                  >
                    <Icon aria-hidden="true" />
                    <span>{label}</span>
                  </Link>
                ))}
              </div>
            ))}
          </nav>
          <div className="rail-safety">
            <ShieldCheck aria-hidden="true" />
            <span>Active Paper Only · Shadow Portfolios Never Execute</span>
          </div>
        </aside>
        <main id="main-content" className="workspace">
          {children}
        </main>
      </div>
    </div>
  );
}
