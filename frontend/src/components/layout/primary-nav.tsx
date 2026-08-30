"use client";

import {
  BookOpenCheck,
  BriefcaseBusiness,
  GitBranch,
  LayoutDashboard,
  LineChart,
  Network,
  Newspaper,
  Sparkles,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { SignOutButton } from "@/components/layout/sign-out-button";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, href: "/" },
  { label: "Decision stories", icon: Network, href: "/stories" },
  { label: "Portfolio", icon: BriefcaseBusiness, href: "/portfolio" },
  { label: "Shadow Portfolio", icon: GitBranch, href: "/alternatives" },
  { label: "News & catalysts", icon: Newspaper, href: "/news" },
  { label: "Market Tracker", icon: LineChart, href: "/market-tracker" },
  { label: "Agents & tools", icon: Sparkles, href: "/agents" },
  { label: "Rules", icon: BookOpenCheck, href: "/rules" },
];

export type PrimaryNavProps = {
  /** Whether the rail is open on mobile (off-canvas drawer). */
  open?: boolean;
  /** Called after a navigation link is activated (used to close the mobile drawer). */
  onNavigate?: () => void;
};

/**
 * PRISM primary navigation rail. It is fixed to the viewport (see `.rail` in
 * globals.css) so it never scrolls with page content. Brand mark, section
 * links, and the sign-out action all live here — there is no separate topbar.
 */
export function PrimaryNav({ open, onNavigate }: PrimaryNavProps) {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);

  function isCurrent(href: string) {
    return href === "/" ? pathname === href : pathname.startsWith(href);
  }

  function collapse() {
    setExpanded(false);
    // Drop focus so a link that kept focus after a click cannot re-expand the rail.
    if (typeof document !== "undefined" && document.activeElement instanceof HTMLElement) {
      const active = document.activeElement;
      if (active.closest(".rail")) active.blur();
    }
  }

  return (
    <aside
      id="primary-navigation"
      className="rail"
      data-open={open || undefined}
      data-expanded={expanded || undefined}
      aria-label="Primary navigation"
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={collapse}
      onFocusCapture={() => setExpanded(true)}
      onBlurCapture={(event) => {
        // Collapse only when focus leaves the rail entirely.
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setExpanded(false);
        }
      }}
    >
      <Link className="wordmark" href="/" aria-label="PRISM home">
        <span aria-hidden="true">
          <Image src="/logo.png" alt="" width={32} height={32} priority />
        </span>
        <strong>PRISM</strong>
      </Link>
      <nav>
        <div className="nav-group">
          {navigation.map(({ label, icon: Icon, href }) => (
            <Link
              key={href}
              href={href}
              aria-current={isCurrent(href) ? "page" : undefined}
              onClick={onNavigate}
            >
              <Icon aria-hidden="true" />
              <span className="nav-label text-[13px]">{label}</span>
            </Link>
          ))}
        </div>
      </nav>
      <div className="rail-footer">
        <SignOutButton />
      </div>
    </aside>
  );
}
