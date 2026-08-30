import {
  Check,
  ChevronLeft,
  GitCompareArrows,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentPerspectiveChain } from "@/features/story/agent-perspective-chain";
import { StoryBranchChart } from "@/features/story/story-branch-chart";
import { StoryCatalystChart } from "@/features/story/story-catalyst-chart";
import { StateBadge } from "@/components/workspace/workspace-ui";
import { formatDateTime, formatTokens } from "@/features/story/formatters";
import { getStory } from "@/features/story/presentation-api";

const RULE_RESULT_TONE: Record<string, string> = {
  PASS: "text-[#00D084]",
  MODIFY: "text-[#F59E0B]",
  FAIL: "text-[#FF6B6B]",
  NOT_EVALUATED: "text-[#547D83]",
};

/** Human-readable story identifier, e.g. "ACME-EARNINGS-GAP". */
function formatStoryId(id: string): string {
  return id.toUpperCase();
}

/** Kicker timestamp in Eastern Time, e.g. "Aug 27, 2026 · 10:05 AM ET". */
function formatKickerTimestamp(value: string): string {
  const date = new Date(value);
  const day = new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "America/New_York",
  }).format(date);
  const time = new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
  }).format(date);
  return `${day} · ${time} ET`;
}

export default async function StoryDetailPage({
  params,
}: {
  params: Promise<{ storyId: string }>;
}) {
  const { storyId } = await params;
  const story = await getStory(storyId);
  if (!story) notFound();
  const tokens = story.transcript.reduce(
    (total, step) => total + (step.inputTokens ?? 0) + (step.outputTokens ?? 0),
    0,
  );
  const ruleTone = RULE_RESULT_TONE[story.ruleResult] ?? "text-[#F8FAFC]";

  return (
    <div className="space-y-8">
      {/* Back link */}
      <Link
        href="/stories"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#64748B] outline-none transition-colors hover:text-[#CBD5E1] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
      >
        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
        All decision stories
      </Link>

      {/* Title row + kicker + summary + key takeaway */}
      <header className="mt-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[clamp(1.5rem,3vw,2rem)] font-semibold leading-tight tracking-tight text-[#F8FAFC]">
            {story.title}
            <span className="rounded-full border border-[#547D83]/40 bg-[#547D83]/20 px-2.5 py-0.5 text-[11px] font-semibold text-[#B2D8DC]">
              {story.category}
            </span>
          </h1>
          <StateBadge state={story.ruleResult === "MODIFY" ? "MODIFY" : story.outcome} />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[12px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
          <span className="font-semibold text-[#CBD5E1]">{story.symbol}</span>
          <span aria-hidden="true">&middot;</span>
          <time dateTime={story.occurredAt}>{formatKickerTimestamp(story.occurredAt)}</time>
          <span aria-hidden="true">&middot;</span>
          <span>Story ID: {formatStoryId(story.id)}</span>
        </div>

        <p className="mt-4 max-w-3xl text-[14px] leading-relaxed text-[#CBD5E1]">{story.summary}</p>

        <div className="mt-4 border-l-2 border-[#547D83] pl-3 text-[13px] leading-relaxed text-[#94A3B8]">
          <span className="font-semibold text-[#B2D8DC]">Key takeaway</span> &mdash; {story.lesson}
        </div>
      </header>

      {/* Metric cards — individual glass cards matching the Synthesis panel
          (DESIGN.md Section 5.2 glass; Section 3.6 semantic tones) */}
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Rule Result
          </dt>
          <dd className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${ruleTone}`}>
            {story.ruleResult}
          </dd>
        </div>
        <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Chosen Outcome
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#00D084]">
            {story.chosenPathImpact}
          </dd>
        </div>
        <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Best Shadow Path
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#818CF8]">
            {story.bestAlternativeImpact}
          </dd>
        </div>
        <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Model Tokens
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#F8FAFC]">
            {formatTokens(tokens)}
          </dd>
        </div>
      </dl>

      <article className="space-y-12">
        {/* SECTION 01 — Catalyst & Market Reaction Gap */}
        <section aria-labelledby="chapter-catalyst" className="space-y-5">
          <div className="flex items-start justify-between gap-6 border-b border-white/8 pb-4">
            <span className="font-mono text-2xl font-semibold tabular-nums text-[#547D83]">01</span>
            <div className="text-right">
              <h2
                id="chapter-catalyst"
                className="text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                Catalyst &amp; Market Reaction Gap
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                Observed vs analog expectation over the event window.
              </p>
            </div>
          </div>

          <StoryCatalystChart
            data={story.marketPath}
            catalyst={{
              headline: story.catalyst.headline,
              source: `${story.catalyst.source} · ${formatDateTime(story.catalyst.publishedAt)}`,
              classification: story.catalyst.classification,
              observedMove: story.catalyst.observedMove,
              expectedMove: story.catalyst.expectedMove,
            }}
            note="EPS beat, guidance light — gap up then fade begins."
          />
        </section>

        {/* PART I: WHAT HAPPENED (continued) */}
        <div className="space-y-6">
          <section aria-labelledby="chapter-tree" className="space-y-5">
            <div className="flex items-start justify-between gap-6 border-b border-white/8 pb-4">
              <span className="font-mono text-2xl font-semibold tabular-nums text-[#547D83]">
                02 <span className="text-[#64748B]">&rarr;</span> 03
              </span>
              <div className="text-right">
                <h2
                  id="chapter-tree"
                  className="text-lg font-semibold tracking-tight text-[#F8FAFC]"
                >
                  Autonomous Agent Perspective Chain &rarr; Synthesis
                </h2>
                <p className="mt-1 text-[12px] text-[#64748B]">
                  Seven specialists, one vetted candidate action.
                </p>
              </div>
            </div>

            <AgentPerspectiveChain
              storyId={story.id}
              synthesis={{
                action: story.illustrativeOutcome.action,
                structure: story.illustrativeOutcome.action,
                notional: story.chosenPathImpact,
                consensus: "3 / 7 aligned",
                authority: "Authority: proposal only",
                note: story.illustrativeOutcome.rationale,
              }}
            />
          </section>

          <Section
            id="chapter-transcript"
            title="03 · Transparent Agent Rationales & Tool Invocations"
            description="Structured outputs, model metadata, latency, and prompt versions for complete reproducibility."
          >
            <ol className="transcript">
              {story.transcript.map((step) => (
                <li
                  key={step.id}
                  className="prism-glass-card p-4 mb-3 transition-all hover:border-white/20"
                >
                  <div className="transcript-icon" data-kind={step.kind}>
                    {step.kind === "tool_call" ? (
                      <GitCompareArrows aria-hidden="true" />
                    ) : step.kind === "rule_gate" ? (
                      <ShieldCheck aria-hidden="true" />
                    ) : (
                      <MessageSquareText aria-hidden="true" />
                    )}
                  </div>
                  <div className="transcript-copy">
                    <div>
                      <span className="font-semibold text-white">{step.actor}</span>
                      <time dateTime={step.occurredAt}>{formatDateTime(step.occurredAt)}</time>
                    </div>
                    <h3>{step.title}</h3>
                    <p className="text-slate-300 text-sm">{step.summary}</p>
                    <ul className="flex flex-wrap gap-1.5 mt-2">
                      {step.evidenceRefs.map((ref) => (
                        <li
                          key={ref}
                          className="text-xs px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300"
                        >
                          {ref}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <dl>
                    {step.model && (
                      <div>
                        <dt>Model</dt>
                        <dd className="font-mono text-xs">{step.model}</dd>
                      </div>
                    )}
                    {step.promptVersion && (
                      <div>
                        <dt>Prompt</dt>
                        <dd className="font-mono text-xs">{step.promptVersion}</dd>
                      </div>
                    )}
                    {step.inputTokens != null && (
                      <div>
                        <dt>Tokens</dt>
                        <dd className="font-mono text-xs">
                          {formatTokens(step.inputTokens + (step.outputTokens ?? 0))}
                        </dd>
                      </div>
                    )}
                    {step.latencyMs !== undefined && (
                      <div>
                        <dt>Latency</dt>
                        <dd className="font-mono text-xs">{step.latencyMs} ms</dd>
                      </div>
                    )}
                  </dl>
                </li>
              ))}
            </ol>
          </Section>

          <Section
            id="chapter-rules"
            title="04 · Deterministic Governance Gate"
            description="AI judgment ends here. Deterministic rules evaluate the exact candidate payload against hard safety constraints."
          >
            <div className="rule-trace space-y-2">
              {story.ruleChecks.map((check) => (
                <div key={check.name} className="prism-glass-card p-3 flex items-start gap-3">
                  <StateBadge state={check.result} />
                  <div>
                    <p className="font-mono text-[0.68rem] text-[#547D83]">
                      {check.priority} · {check.ruleId} · {check.reasonCode}
                    </p>
                    <h3 className="text-sm font-medium text-white">{check.name}</h3>
                    <p className="text-xs text-slate-300 mt-0.5">{check.explanation}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section
            id="chapter-outcome"
            title="05 · Active Portfolio Governed Outcome"
            description="The current backend portfolio view is not an authorization or broker receipt."
          >
            <div className="outcome-statement prism-glass-card p-4 border-l-4 border-l-[#00D084]">
              <Check aria-hidden="true" className="text-[#00D084]" />
              <div>
                <span className="text-xs font-mono text-[#00D084] uppercase tracking-wider">
                  {story.illustrativeOutcome.status}
                </span>
                <h3 className="text-base font-semibold text-white">
                  {story.illustrativeOutcome.action}
                </h3>
                <p className="text-sm text-slate-300 mt-1">{story.illustrativeOutcome.rationale}</p>
              </div>
            </div>
          </Section>
        </div>

        {/* PART II: WHAT COULD HAVE HAPPENED */}
        <div className="space-y-6 pt-6 border-t border-white/15">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#818CF8]/15 border border-[#818CF8]/30 w-fit">
            <span className="h-2 w-2 rounded-full bg-[#818CF8]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#C7D2FE]">
              Part II · What Could Have Happened (The Shadow Multiverse)
            </span>
          </div>

          <section aria-labelledby="chapter-lessons" className="space-y-5">
            <div className="flex items-start justify-between gap-6 border-b border-white/8 pb-4">
              <span className="font-mono text-2xl font-semibold tabular-nums text-[#818CF8]">
                07
              </span>
              <div className="text-right">
                <h2
                  id="chapter-lessons"
                  className="text-lg font-semibold tracking-tight text-[#F8FAFC]"
                >
                  ShadowFund Counterfactual Matrix &amp; Lessons
                </h2>
                <p className="mt-1 text-[12px] text-[#64748B]">
                  What every branch would have done.
                </p>
              </div>
            </div>

            <StoryBranchChart data={story.marketPath} />

            {/* Branch comparison table */}
            <div className="overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl">
              <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1.4fr)_minmax(0,0.8fr)_minmax(0,0.8fr)] gap-4 border-b border-white/8 px-5 py-3 font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                <span>Branch</span>
                <span>Controlled Variation</span>
                <span className="text-right">P&amp;L</span>
                <span className="text-right">Drawdown</span>
              </div>
              {story.alternatives.map((branch) => {
                const name =
                  branch.label === "Illustrative governed path" ? "Active Portfolio" : branch.label;
                const isActive = branch.id === "chosen";
                return (
                  <div
                    key={branch.id}
                    className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1.4fr)_minmax(0,0.8fr)_minmax(0,0.8fr)] items-center gap-4 px-5 py-3.5 not-last:border-b not-last:border-white/8"
                    style={isActive ? { background: "rgba(84,125,131,0.1)" } : undefined}
                  >
                    <span className="text-[13px] font-semibold text-[#F8FAFC]">{name}</span>
                    <span className="text-[13px] text-[#94A3B8]">{branch.variation}</span>
                    <span className="text-right font-mono text-[13px] font-semibold tabular-nums text-[#00D084]">
                      {branch.pnl}
                    </span>
                    <span className="text-right font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                      {branch.drawdown}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Lessons panel */}
            <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl">
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[#818CF8]">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                Lessons
              </div>
              <ul className="mt-3 space-y-2.5">
                {story.lessons.map((lesson) => (
                  <li key={lesson} className="flex items-start gap-2.5">
                    <span
                      aria-hidden="true"
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#818CF8]"
                    />
                    <p className="m-0 text-[13px] leading-relaxed text-[#CBD5E1]">{lesson}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>
      </article>
    </div>
  );
}

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="content-section">
      <div className="content-section-heading">
        <h2 id={id}>{title}</h2>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}
