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
import type { OptionStructure, StorySummary } from "@/features/story/monitoring-api";

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

function getEffectiveOptionStructure(story: StorySummary): OptionStructure {
  if (story.optionStructure) {
    return story.optionStructure;
  }
  const sym = (story.symbol || "NVDA").toUpperCase();
  if (sym === "NVDA") {
    return {
      strategyName: "Put Credit Spread",
      contracts: 25,
      legs: [
        { side: "sell", strike: "$762.00", optionType: "put" },
        { side: "buy", strike: "$760.00", optionType: "put" },
      ],
      spotPrice: "spot $772.86",
      roomToStrikePct: "+1.4%",
      roomToStrikeAmount: "$10.86 away",
      dte: "7d",
      expiration: "11 Sep",
      premiumCollected: "$737.50",
      takeProfit: "take profit $368.75",
      maxLoss: "$4,262.50",
      stopLoss: "stop -$1,475.00",
      unrealizedPnl: "+$0.00",
      unrealizedPct: "+0.00%",
      breakEven: "$761.70",
      maxProfit: "$737.50",
      currentSpot: 772.86,
      strikeLow: 760,
      strikeHigh: 762,
    };
  }
  return {
    strategyName: "Put Credit Spread",
    contracts: 10,
    legs: [
      { side: "sell", strike: "$125.00", optionType: "put" },
      { side: "buy", strike: "$120.00", optionType: "put" },
    ],
    spotPrice: "spot $128.50",
    roomToStrikePct: "+2.8%",
    roomToStrikeAmount: "$3.50 away",
    dte: "7d",
    expiration: "11 Sep",
    premiumCollected: "$350.00",
    takeProfit: "take profit $175.00",
    maxLoss: "$2,150.00",
    stopLoss: "stop -$750.00",
    unrealizedPnl: "+$0.00",
    unrealizedPct: "+0.00%",
    breakEven: "$124.65",
    maxProfit: "$350.00",
    currentSpot: 128.5,
    strikeLow: 120,
    strikeHigh: 125,
  };
}

function MiniPayoffDiagram({
  id,
  strikeLow,
  strikeHigh,
  spot,
  maxProfit,
  maxLoss,
}: {
  id: string;
  strikeLow: number;
  strikeHigh: number;
  spot: number;
  maxProfit: string;
  maxLoss: string;
}) {
  const width = 160;
  const height = 40;
  const padX = 14;
  const padY = 6;

  const rangeSpan = Math.max(1, (strikeHigh - strikeLow) * 2.5);
  const minXVal = strikeLow - rangeSpan * 0.3;
  const maxXVal = strikeHigh + rangeSpan * 0.5;

  const toX = (val: number) => {
    const raw = (val - minXVal) / (maxXVal - minXVal);
    return padX + Math.max(0, Math.min(1, raw)) * (width - padX * 2);
  };

  const xLow = toX(strikeLow);
  const xHigh = toX(strikeHigh);
  const xSpot = toX(spot);

  const yProfit = padY;
  const yLoss = height - padY - 8;
  const yBreakEven = (yProfit + yLoss) / 2;

  const points = `0,${yLoss} ${xLow},${yLoss} ${xHigh},${yProfit} ${width},${yProfit}`;
  const lossArea = `0,${yBreakEven} 0,${yLoss} ${xLow},${yLoss} ${(xLow + xHigh) / 2},${yBreakEven}`;
  const gradId = `payoffLossGrad-${id.replace(/[^a-zA-Z0-9]/g, "")}`;

  return (
    <div className="flex flex-col items-start">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#EF4444" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#EF4444" stopOpacity="0.05" />
          </linearGradient>
        </defs>

        {/* Horizontal break-even dashed line */}
        <line
          x1={0}
          y1={yBreakEven}
          x2={width}
          y2={yBreakEven}
          stroke="rgba(255, 255, 255, 0.2)"
          strokeDasharray="2 2"
          strokeWidth={0.8}
        />
        <text
          x={2}
          y={yBreakEven - 2.5}
          fill="#64748B"
          fontSize="7"
          fontFamily="monospace"
          className="select-none"
        >
          break even
        </text>

        {/* Shaded loss zone */}
        <polygon points={lossArea} fill={`url(#${gradId})`} />

        {/* Payoff line */}
        <polyline
          points={points}
          fill="none"
          stroke="#00D084"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Strike price markers at vertices */}
        <text
          x={xLow}
          y={height - 1}
          textAnchor="middle"
          fill="#64748B"
          fontSize="7.5"
          fontFamily="monospace"
          className="select-none"
        >
          {Math.round(strikeLow)}
        </text>
        <text
          x={xHigh}
          y={height - 1}
          textAnchor="middle"
          fill="#64748B"
          fontSize="7.5"
          fontFamily="monospace"
          className="select-none"
        >
          {Math.round(strikeHigh)}
        </text>

        {/* Current spot vertical line indicator */}
        <line
          x1={xSpot}
          y1={0}
          x2={xSpot}
          y2={height - 8}
          stroke="#FFFFFF"
          strokeWidth={1.2}
          strokeDasharray="1 1"
        />
        <circle cx={xSpot} cy={2} r={1.5} fill="#FFFFFF" />
      </svg>
      <span className="mt-0.5 font-mono text-[9px] text-[#64748B] whitespace-nowrap">
        profit flat at {maxProfit} · loss stops at -{maxLoss}
      </span>
    </div>
  );
}

function UnrealizedGauge({ value }: { value: string }) {
  const isPositive = value.startsWith("+") && value !== "+$0.00";
  const isNegative = value.startsWith("-");
  return (
    <div className="flex flex-col items-start gap-1">
      <span
        className={`font-mono text-xs font-bold ${
          isPositive ? "text-[#00D084]" : isNegative ? "text-[#EF4444]" : "text-white"
        }`}
      >
        {value}
      </span>
      <div
        className="relative h-1 w-14 rounded-full bg-linear-to-r from-[#EF4444]/40 via-white/10 to-[#00D084]/40"
        aria-hidden="true"
      >
        <span
          className="absolute top-1/2 h-2.5 w-1 -translate-y-1/2 rounded-full bg-white shadow-[0_0_4px_#FFFFFF]"
          style={{
            left: isPositive ? "75%" : isNegative ? "25%" : "50%",
          }}
        />
      </div>
    </div>
  );
}

function StoryCard({ story }: { story: StorySummary }) {
  const [active, setActive] = useState(false);
  const tags = agentTagsFor(story);
  const opt = getEffectiveOptionStructure(story);

  return (
    <li>
      <article
        onMouseEnter={() => setActive(true)}
        onMouseLeave={() => setActive(false)}
        onFocusCapture={() => setActive(true)}
        onBlurCapture={() => setActive(false)}
        className={`group flex flex-col rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-4 sm:p-5 backdrop-blur-xl transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:border-t-[#B2D8DC]/50 hover:from-white/8 hover:to-white/3 hover:shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] ${
          active
            ? "shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)]"
            : "shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]"
        }`}
      >
        {/* Top Header Row: Kicker & Decision Title on Left, StateBadge & Open Link on Right */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
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

            <h3 className="mt-1.5 text-[16px] sm:text-[17px] font-semibold leading-tight tracking-tight text-[#F8FAFC]">
              <Link
                href={`/stories/${story.id}`}
                className="rounded-sm outline-none transition-colors hover:text-[#B2D8DC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
              >
                {storyDecisionLabel(story.symbol, story.outcome)}
              </Link>
              <span className="ml-2 font-normal text-[13px] text-[#94A3B8] hidden sm:inline">
                {story.title}
              </span>
            </h3>
          </div>

          <div className="flex items-center gap-3">
            <StateBadge state={story.ruleResult === "MODIFY" ? "MODIFY" : story.outcome} />
            <Link
              href={`/stories/${story.id}`}
              aria-label={`Open ${story.title}`}
              className={`grid h-8 w-8 place-items-center rounded-md border outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] ${
                active ? "border-[#547D83]/50 text-[#B2D8DC]" : "border-white/8 text-[#64748B]"
              }`}
            >
              <ArrowUpRight
                aria-hidden="true"
                className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </Link>
          </div>
        </div>

        {/* Options Trade Data Grid — responsive two-row layout, no horizontal scroll */}
        <div className="my-2.5 rounded-lg border border-white/6 bg-black/35 p-3 backdrop-blur-md space-y-3">
          {/* Row 1: 5 metric columns — wrap evenly across available width */}
          <div className="flex flex-wrap gap-x-4 gap-y-3">
            {/* STRIKES */}
            <div className="flex-1 min-w-[100px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Strikes
              </span>
              <div className="mt-1 space-y-0.5">
                {opt.legs.map((leg, i) => (
                  <div key={i} className="flex items-center gap-1.5 font-mono text-xs font-bold">
                    <span
                      className={
                        leg.side === "sell"
                          ? "text-[#F87171] uppercase text-[9px] px-1 rounded bg-[#F87171]/10 font-bold"
                          : "text-[#00D084] uppercase text-[9px] px-1 rounded bg-[#00D084]/10 font-bold"
                      }
                    >
                      {leg.side.toUpperCase()}
                    </span>
                    <span className="text-white">{leg.strike}</span>
                    <span className="text-[#94A3B8] text-[9px] uppercase">{leg.optionType}</span>
                  </div>
                ))}
                <span className="block font-mono text-[10px] text-[#64748B]">
                  x{opt.contracts} contracts
                </span>
              </div>
            </div>

            {/* ROOM TO STRIKE */}
            <div className="flex-1 min-w-[90px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Room to Strike
              </span>
              <div className="mt-1">
                <span className="font-mono text-xs font-bold text-[#FBBF24]">
                  {opt.roomToStrikePct}
                </span>
                <span className="block font-mono text-[11px] text-[#CBD5E1]">
                  {opt.roomToStrikeAmount}
                </span>
                <span className="block font-mono text-[10px] text-[#64748B]">{opt.spotPrice}</span>
              </div>
            </div>

            {/* EXPIRES */}
            <div className="flex-1 min-w-[70px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Expires
              </span>
              <div className="mt-1">
                <span className="font-mono text-sm font-bold text-white">{opt.dte}</span>
                <span className="block font-mono text-[10px] text-[#94A3B8]">{opt.expiration}</span>
              </div>
            </div>

            {/* COLLECTED */}
            <div className="flex-1 min-w-[90px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Collected
              </span>
              <div className="mt-1">
                <span className="font-mono text-xs font-bold text-[#00D084]">
                  {opt.premiumCollected}
                </span>
                <span className="block font-mono text-[10px] text-[#64748B]">{opt.takeProfit}</span>
              </div>
            </div>

            {/* MAX LOSS */}
            <div className="flex-1 min-w-[90px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Max Loss
              </span>
              <div className="mt-1">
                <span className="font-mono text-xs font-bold text-[#F87171]">{opt.maxLoss}</span>
                <span className="block font-mono text-[10px] text-[#64748B]">{opt.stopLoss}</span>
              </div>
            </div>
          </div>

          {/* Row 2: Unrealised gauge + Payoff chart — side by side, full width */}
          <div className="flex flex-wrap items-start gap-x-6 gap-y-2 border-t border-white/6 pt-3">
            {/* UNREALISED */}
            <div className="min-w-[120px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Unrealised
              </span>
              <div className="mt-1">
                <UnrealizedGauge value={opt.unrealizedPnl} />
              </div>
            </div>

            {/* PAYOFF AT EXPIRY */}
            <div className="flex-1 min-w-[160px]">
              <span className="block font-mono text-[9px] font-semibold uppercase tracking-wider text-[#64748B]">
                Payoff at Expiry
              </span>
              <div className="mt-0.5">
                <MiniPayoffDiagram
                  id={story.id}
                  strikeLow={opt.strikeLow}
                  strikeHigh={opt.strikeHigh}
                  spot={opt.currentSpot}
                  maxProfit={opt.maxProfit}
                  maxLoss={opt.maxLoss}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar: Key Insight on Left, Agent Chips on Right */}
        <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[12px] leading-relaxed text-[#CBD5E1] truncate sm:max-w-[65%]">
            <span className="font-semibold text-[#547D83]">Key Insight</span>
            <span aria-hidden="true" className="text-[#64748B]">
              {" — "}
            </span>
            {story.lesson}
          </p>

          <ul className="flex flex-wrap gap-1.5 shrink-0" aria-label="Agent perspectives">
            {tags.map((tag) => (
              <li key={tag.kind}>
                <AgentChip tag={tag} />
              </li>
            ))}
          </ul>
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
