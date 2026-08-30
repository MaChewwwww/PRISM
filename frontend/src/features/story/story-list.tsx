"use client";

import { AlertTriangle, ArrowUpRight, CircleDot, Diamond, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StateBadge } from "@/components/workspace/workspace-ui";
import { formatDate } from "@/features/story/formatters";
import type { StorySummary } from "@/features/story/presentation-api";

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
    <li className="relative pl-7 sm:pl-9">
      {/* Timeline rail: connecting line + node (DESIGN.md Section 7.1 chronology) */}
      <span
        aria-hidden="true"
        className="absolute left-[0.28rem] top-1.5 -bottom-6 w-px bg-white/8 sm:left-[0.4rem]"
      />
      <span
        aria-hidden="true"
        className={`absolute left-0 top-1.5 grid h-3 w-3 place-items-center rounded-full border transition-colors duration-200 ${
          active ? "border-[#547D83] bg-[#547D83]/20" : "border-white/16 bg-[#080B10]"
        }`}
      >
        <span
          className={`h-1 w-1 rounded-full transition-colors duration-200 ${
            active ? "bg-[#547D83]" : "bg-[#64748B]"
          }`}
        />
      </span>

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
            <time dateTime={story.occurredAt}>{formatDate(story.occurredAt)}</time>
            <span aria-hidden="true" className="text-white/20">
              |
            </span>
            <span className="font-semibold text-[#F8FAFC]">{story.symbol}</span>
            <span aria-hidden="true" className="text-white/20">
              |
            </span>
            <span>{story.category}</span>
          </div>

          {/* Card H3: 20px / 600 (DESIGN.md Section 4.2) */}
          <h3 className="mt-3 text-[18px] font-semibold leading-tight tracking-tight text-[#F8FAFC]">
            <Link
              href={`/stories/${story.id}`}
              className="rounded-sm outline-none transition-colors hover:text-[#B2D8DC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
            >
              {story.title}
            </Link>
          </h3>

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

export function StoryList({ stories }: { stories: StorySummary[] }) {
  if (stories.length === 0) {
    return (
      <div className="inline-empty">
        <strong>No decision stories in this range.</strong>
        <span>Choose a wider period or clear the outcome and symbol filters.</span>
      </div>
    );
  }

  return (
    <ol className="mt-2 grid list-none gap-5 p-0">
      {stories.map((story) => (
        <StoryCard key={story.id} story={story} />
      ))}
    </ol>
  );
}
