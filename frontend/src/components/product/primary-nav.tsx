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
import Link from "next/link";
import { usePathname } from "next/navigation";

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
      { label: "Market Tracker", icon: LineChart, href: "/market-tracker" },
      { label: "Agents & tools", icon: Sparkles, href: "/agents" },
      { label: "Rules", icon: BookOpenCheck, href: "/rules" },
    ],
  },
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

  function isCurrent(href: string) {
    return href === "/" ? pathname === href : pathname.startsWith(href);
  }

  return (
    <aside
      id="primary-navigation"
      className="rail"
      data-open={open || undefined}
      aria-label="Primary navigation"
    >
      <Link className="wordmark" href="/" aria-label="PRISM decision journal home">
        <span aria-hidden="true">PR</span>
        <strong>PRISM</strong>
        <small>Decision journal</small>
      </Link>
      <nav>
        {navigation.map((group) => (
          <div className="nav-group" key={group.label}>
            <p>{group.label}</p>
            {group.items.map(({ label, icon: Icon, href }) => (
              <Link
                key={href}
                href={href}
                aria-current={isCurrent(href) ? "page" : undefined}
                onClick={onNavigate}
              >
                <Icon aria-hidden="true" />
                <span>{label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="rail-footer">
        <SignOutButton />
      </div>
    </aside>
  );
}
