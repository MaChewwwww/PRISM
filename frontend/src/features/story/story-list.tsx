"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Diamond,
  type LucideIcon,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { StateBadge } from "@/components/workspace/workspace-ui";
import { formatDateTime, storyDecisionLabel } from "@/features/story/formatters";
import type { StorySummary } from "@/features/story/monitoring-api";

const PAGE_SIZE = 8;

/** Lowercased haystack of the searchable fields for a decision story. */
function storyHaystack(story: StorySummary): string {
  return [
    story.symbol,
    story.title,
    story.summary,
    story.category,
    story.lesson,
    storyDecisionLabel(story.symbol, story.outcome),
    formatDateTime(story.occurredAt),
    story.occurredAt,
  ]
    .join(" ")
    .toLowerCase();
}

/**
 * Agent perspective chips follow DESIGN.md Section 6.3 (Agent Perspective Chips
 * & Status Tags) and the prismatic spectral tokens in Section 3.3: Research
 * (Ice Cyan), Proposal / Trading Decision (Emerald-Mint), Risk (Amber), and the
 * deterministic Rules Gate (Mineral Teal). Which perspectives appear is derived
 * from the recorded rule-gate result, presented in canonical authority order
 * (Research -> Proposal -> Risk -> Gate; DESIGN.md Section 7.1).
 */
type AgentKind = "research" | "proposal" | "risk" | "gate";

type AgentTag = {
  kind: AgentKind;
  label: string;
  icon: LucideIcon;
  /** Tailwind classes taken verbatim from DESIGN.md Section 6.3 chip variants. */
  chipClass: string;
  dotClass: string;
};

const AGENT_TAGS: Record<AgentKind, AgentTag> = {
  research: {
    kind: "research",
    label: "Research",
    icon: Diamond,
    chipClass: "bg-[#38BDF8]/15 text-[#38BDF8] border-[#38BDF8]/30",
    dotClass: "text-[#38BDF8]",
  },
  proposal: {
    kind: "proposal",
    label: "Proposal",
    icon: Diamond,
    chipClass: "bg-[#10B981]/15 text-[#10B981] border-[#10B981]/30",
    dotClass: "text-[#10B981]",
  },
  risk: {
    kind: "risk",
    label: "Risk",
    icon: AlertTriangle,
    chipClass: "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30",
    dotClass: "text-[#F59E0B]",
  },
  gate: {
    kind: "gate",
    label: "Gate",
    icon: CircleDot,
    chipClass: "bg-[#547D83]/20 text-[#B2D8DC] border-[#547D83]/40",
    dotClass: "text-[#547D83]",
  },
};

function agentTagsFor(story: StorySummary): AgentTag[] {
  const kinds: AgentKind[] = ["research"];
  switch (story.ruleResult) {
    case "PASS":
    case "MODIFY":
      kinds.push("proposal", "gate");
      break;
    case "FAIL":
      kinds.push("proposal", "risk");
      break;
    case "NOT_EVALUATED":
    default:
      kinds.push("risk");
      break;
  }
  return kinds.map((kind) => AGENT_TAGS[kind]);
}

function AgentChip({ tag }: { tag: AgentTag }) {
  const Icon = tag.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-semibold ${tag.chipClass}`}
    >
      <Icon aria-hidden="true" className={`h-3 w-3 ${tag.dotClass}`} strokeWidth={2.5} />
      {tag.label}
    </span>
  );
}

function StoryCard({ story }: { story: StorySummary }) {
  const [active, setActive] = useState(false);
  const tags = agentTagsFor(story);

  return (
    <li>
      {/*
        Major decision-story module: DESIGN.md Section 5.2 interactive glass
        recipe (rounded-xl, layered fill, specular top border, teal hover border,
        translateY(-2px)) rendered via Tailwind arbitrary values matching the doc.
      */}
      <article
        onMouseEnter={() => setActive(true)}
        onMouseLeave={() => setActive(false)}
        onFocusCapture={() => setActive(true)}
        onBlurCapture={() => setActive(false)}
        className={`group grid grid-cols-1 gap-x-8 gap-y-4 rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:border-t-[#B2D8DC]/50 hover:from-white/8 hover:to-white/3 hover:shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] sm:grid-cols-[minmax(0,1fr)_auto] sm:p-6 ${
          active
            ? "shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)]"
            : "shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]"
        }`}
      >
        {/* Left column: kicker, title, insight, agent chips */}
        <div className="min-w-0">
          {/* Caption / Meta: 12px, 500, tracking 0.02em (DESIGN.md Section 4.2) */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
            <time dateTime={story.occurredAt}>{formatDateTime(story.occurredAt)}</time>
            <span aria-hidden="true" className="text-white/20">
              |
            </span>
            <span className="font-semibold text-[#F8FAFC]">{story.symbol}</span>
            <span aria-hidden="true" className="text-white/20">
              |
            </span>
            <span>{story.category}</span>
          </div>

          {/* Card H3: plain decision label (DESIGN.md Section 4.2) */}
          <h3 className="mt-3 text-[18px] font-semibold leading-tight tracking-tight text-[#F8FAFC]">
            <Link
              href={`/stories/${story.id}`}
              className="rounded-sm outline-none transition-colors hover:text-[#B2D8DC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
            >
              {storyDecisionLabel(story.symbol, story.outcome)}
            </Link>
          </h3>

          {/* Analytical title kept as a secondary line */}
          <p className="mt-1 text-[13px] leading-snug text-[#94A3B8]">{story.title}</p>

          {/* Body Regular: 14px (DESIGN.md Section 4.2) */}
          <p className="mt-2 max-w-208 text-[12px] leading-relaxed text-[#CBD5E1]">
            <span className="font-semibold text-[#547D83]">Key Insight</span>
            <span aria-hidden="true" className="text-[#64748B]">
              {" — "}
            </span>
            {story.lesson}
          </p>

          <ul className="mt-4 flex flex-wrap gap-2" aria-label="Agent perspectives">
            {tags.map((tag) => (
              <li key={tag.kind}>
                <AgentChip tag={tag} />
              </li>
            ))}
          </ul>
        </div>

        {/* Right column: status pill, outcome figures, open link */}
        <div className="flex flex-col items-start gap-4 sm:items-end sm:text-right">
          <StateBadge state={story.ruleResult === "MODIFY" ? "MODIFY" : story.outcome} />

          {/* Financial figures: mono tabular-nums (DESIGN.md Section 3, 4.2) */}
          <dl className="w-full space-y-1.5 sm:w-auto">
            <div className="flex items-center justify-between gap-8 sm:justify-end">
              <dt className="font-mono text-[10px] text-[#64748B]">Active Outcome</dt>
              <dd className="m-0 font-mono text-[12px] font-semibold tabular-nums text-[#00D084]">
                {story.chosenPathImpact}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-8 sm:justify-end">
              <dt className="font-mono text-[10px] text-[#64748B]">Best Shadow Path</dt>
              <dd className="m-0 font-mono text-[12px] font-semibold tabular-nums text-[#818CF8]">
                {story.bestAlternativeImpact}
              </dd>
            </div>
          </dl>

          <Link
            href={`/stories/${story.id}`}
            aria-label={`Open ${story.title}`}
            className={`grid h-9 w-9 place-items-center rounded-md border outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] ${
              active ? "border-[#547D83]/50 text-[#B2D8DC]" : "border-white/8 text-[#64748B]"
            }`}
          >
            <ArrowUpRight
              aria-hidden="true"
              className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            />
          </Link>
        </div>
      </article>
    </li>
  );
}

export function StoryList({
  stories,
  heading,
  rangeControl,
}: {
  stories: StorySummary[];
  heading?: ReactNode;
  rangeControl?: ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return stories;
    const terms = trimmed.split(/\s+/);
    return stories.filter((story) => {
      const haystack = storyHaystack(story);
      return terms.every((term) => haystack.includes(term));
    });
  }, [query, stories]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function updateQuery(value: string) {
    setQuery(value);
    setPage(1);
  }

  function goToPage(next: number) {
    setPage(next);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  return (
    <>
      {/* Toolbar row: heading (left), search + range picker (right) */}
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {heading && <div className="min-w-0 shrink-0">{heading}</div>}
        <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center lg:justify-end">
          <div className="relative w-full sm:max-w-xs">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(event) => updateQuery(event.target.value)}
              placeholder="Search decision, company, date, time"
              aria-label="Search decision stories"
              className="w-full rounded-md border border-white/8 bg-white/2 py-2 pl-9 pr-9 text-[13px] text-[#F8FAFC] outline-none transition-colors placeholder:text-[#64748B] focus-visible:border-[#547D83]/50 focus-visible:ring-2 focus-visible:ring-[#547D83]/40"
            />
            {query && (
              <button
                type="button"
                onClick={() => updateQuery("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-md text-[#64748B] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
          </div>
          {rangeControl && <div className="shrink-0">{rangeControl}</div>}
        </div>
      </div>

      {stories.length === 0 ? (
        <div className="inline-empty">
          <strong>No decision stories in this range.</strong>
          <span>Choose a wider period or clear the outcome and symbol filters.</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="inline-empty">
          <strong>No decision stories match &ldquo;{query}&rdquo;.</strong>
          <span>Try a different company, date, or time.</span>
        </div>
      ) : (
        <>
          <ol className="grid list-none gap-5 p-0">
            {pageItems.map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </ol>

          {filtered.length > PAGE_SIZE && (
            <nav
              className="mt-5 flex items-center justify-between gap-3"
              aria-label="Decision stories pagination"
            >
              <span className="font-mono text-[11px] text-[#64748B]">
                Page {safePage} of {totalPages} · {filtered.length} decisions
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => goToPage(Math.max(1, safePage - 1))}
                  disabled={safePage <= 1}
                  className="inline-flex items-center gap-1 rounded-md border border-white/8 bg-white/5 px-3 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
                </button>
                <button
                  type="button"
                  onClick={() => goToPage(Math.min(totalPages, safePage + 1))}
                  disabled={safePage >= totalPages}
                  className="inline-flex items-center gap-1 rounded-md border border-white/8 bg-white/5 px-3 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </nav>
          )}
        </>
      )}
    </>
  );
}
