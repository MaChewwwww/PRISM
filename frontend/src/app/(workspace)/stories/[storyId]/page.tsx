import {
  ChevronLeft,
  FileCheck,
  Gavel,
  GitBranch,
  GitCompareArrows,
  Layers,
  Newspaper,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentPerspectiveChain } from "@/features/story/agent-perspective-chain";
import { StoryBranchChart } from "@/features/story/story-branch-chart";
import { StoryCatalystChart } from "@/features/story/story-catalyst-chart";
import { StateBadge } from "@/components/workspace/workspace-ui";
import { formatDateTime, formatTokens, storyDecisionLabel } from "@/features/story/formatters";
import { getStory, type StoryDetail } from "@/features/story/presentation-api";

const RULE_RESULT_TONE: Record<string, string> = {
  PASS: "text-[#00D084]",
  MODIFY: "text-[#F59E0B]",
  FAIL: "text-[#FF6B6B]",
  NOT_EVALUATED: "text-[#547D83]",
};

// Governance gate semantic colors (DESIGN.md Section 3.6 status palette).
const GATE_TONE: Record<string, string> = {
  PASS: "#00D084",
  MODIFY: "#F59E0B",
  FAIL: "#FF6B6B",
  NOT_EVALUATED: "#64748B",
};

/** Format the paper outcome status, e.g. "illustrative_only" -> "FILLED · PAPER ACCOUNT". */
function formatOutcomeStatus(status: string): string {
  const normalized = status.toLowerCase();
  const filled =
    normalized.includes("no_trade") || normalized.includes("reject") ? "NO FILL" : "FILLED";
  return `${filled} · PAPER ACCOUNT`;
}

// Aggregate gate outcome label derived from the recorded rule result.
function aggregateGateLabel(ruleResult: string): string {
  switch (ruleResult) {
    case "PASS":
      return "APPROVED";
    case "MODIFY":
      return "MODIFIED_PENDING_ACCEPTANCE";
    case "FAIL":
      return "REJECTED";
    case "NO_TRADE":
      return "NO_TRADE";
    default:
      return ruleResult;
  }
}

/** Human-readable story identifier, e.g. "ACME-EARNINGS-GAP". */
function formatStoryId(id: string): string {
  return id.toUpperCase();
}

/**
 * Extract the Risk AI critique from the transcript. Uses the recorded Risk step
 * summary as the challenge and its evidence references as the evidence list,
 * with graceful fallbacks when the story did not reach a risk review.
 */
function buildRiskCritique(story: StoryDetail): { challenge: string; evidence: string[] } {
  const riskStep = story.transcript.find((step) => step.actor.toLowerCase().includes("risk"));
  return {
    challenge:
      riskStep?.summary ??
      "No adversarial risk critique was recorded for this decision — the pipeline stopped before the Risk AI stage.",
    evidence: riskStep?.evidenceRefs ?? [],
  };
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
  const riskCritique = buildRiskCritique(story);

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
            {storyDecisionLabel(story.symbol, story.outcome)}
            <span className="rounded-full border border-[#547D83]/40 bg-[#547D83]/20 px-2.5 py-0.5 text-[11px] font-semibold text-[#B2D8DC]">
              {story.category}
            </span>
          </h1>
          <StateBadge state={story.ruleResult === "MODIFY" ? "MODIFY" : story.outcome} />
        </div>

        {/* Analytical title kept as a secondary line */}
        <p className="mt-2 text-[15px] font-medium leading-snug text-[#CBD5E1]">{story.title}</p>

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
          <div className="border-b border-white/8 pb-4">
            <h2
              id="chapter-catalyst"
              className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
                <Newspaper className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              Catalyst &amp; Market Reaction Gap
            </h2>
            <p className="mt-1 text-[12px] text-[#64748B]">
              Observed vs analog expectation over the event window.
            </p>
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

        {/* SECTION 02 — Decision Pipeline */}
        <section aria-labelledby="chapter-pipeline" className="space-y-6">
          <div className="border-b border-white/8 pb-4">
            <h2
              id="chapter-pipeline"
              className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
                <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              Decision Pipeline
            </h2>
            <p className="mt-1 text-[12px] text-[#64748B]">
              The recorded path this decision actually took. Degraded or no-trade stories stop
              earlier &mdash; nodes past the stop point show as not run.
            </p>
          </div>

          <DecisionPipeline nodes={story.decisionTree} />
        </section>

        {/* PART I: WHAT HAPPENED (continued) */}
        <div className="space-y-6">
          <section aria-labelledby="chapter-tree" className="space-y-5">
            <div className="border-b border-white/8 pb-4">
              <h2
                id="chapter-tree"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
                  <Layers className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Autonomous Agent Perspective Chain
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                Seven specialists, one vetted candidate action.
              </p>
            </div>

            <AgentPerspectiveChain
              storyId={story.id}
              synthesis={{
                action: story.illustrativeOutcome.action,
                structure: story.illustrativeOutcome.action,
                notional: story.chosenPathImpact,
                consensus: "3 / 7 aligned",
                note: story.illustrativeOutcome.rationale,
              }}
            />
          </section>

          {/* SECTION 05 — Risk AI Critique */}
          <section aria-labelledby="chapter-risk-critique" className="space-y-5">
            <div className="border-b border-white/8 pb-4">
              <h2
                id="chapter-risk-critique"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#F59E0B]/30 bg-[#F59E0B]/15 text-[#F59E0B]">
                  <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Risk AI Critique
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                The adversarial challenge raised before deterministic authorization.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              {/* Challenge card */}
              <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl sm:p-6">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
                  Challenge
                </p>
                <p className="mt-2 text-[14px] leading-relaxed text-[#CBD5E1]">
                  {riskCritique.challenge}
                </p>
                <p className="mt-5 border-t border-white/8 pt-4 text-[12px] italic leading-relaxed text-[#64748B]">
                  AI-assisted risk followed by deterministic authority.
                </p>
              </div>

              {/* Evidence card */}
              <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl sm:p-6">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
                  Evidence
                </p>
                {riskCritique.evidence.length > 0 ? (
                  <ul className="mt-3 space-y-2">
                    {riskCritique.evidence.map((item) => (
                      <li key={item} className="flex items-start gap-2.5">
                        <span
                          aria-hidden="true"
                          className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#F59E0B]"
                        />
                        <span className="text-[13px] leading-relaxed text-[#CBD5E1]">{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-[13px] leading-relaxed text-[#64748B]">
                    No evidence references were recorded for this critique.
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* SECTION 06 — Deterministic Governance Gate */}
          <section aria-labelledby="chapter-rules" className="space-y-5">
            <div className="border-b border-white/8 pb-4">
              <h2
                id="chapter-rules"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
                  <Gavel className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Deterministic Governance Gate
              </h2>
              <p className="mt-1 max-w-3xl text-[12px] text-[#64748B]">
                Evaluates the exact candidate payload against hard safety constraints, grouped by
                priority tier.
              </p>
            </div>

            <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl sm:p-6">
              {/* Aggregate outcome + legend */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <span
                  className="rounded-md px-2.5 py-1 font-mono text-[11px] font-bold uppercase tracking-wide"
                  style={{
                    color: GATE_TONE[story.ruleResult] ?? "#64748B",
                    background: `${GATE_TONE[story.ruleResult] ?? "#64748B"}26`,
                  }}
                >
                  {aggregateGateLabel(story.ruleResult)}
                </span>
                <span className="text-[12px] text-[#94A3B8]">Aggregate outcome</span>
              </div>

              {/* Rule table */}
              <div className="mt-5 border-t border-white/8">
                <div className="grid grid-cols-[2.5rem_5rem_minmax(0,1fr)] gap-4 border-b border-white/8 py-3 font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B] sm:grid-cols-[2.5rem_5rem_10rem_minmax(0,1.8fr)]">
                  <span>Priority</span>
                  <span>Status</span>
                  <span className="hidden sm:block">Rule ID</span>
                  <span>Explanation</span>
                </div>
                {story.ruleChecks.map((check) => (
                  <div
                    key={check.name}
                    className="grid grid-cols-[2.5rem_5rem_minmax(0,1fr)] items-start gap-4 py-3.5 not-last:border-b not-last:border-white/8 sm:grid-cols-[2.5rem_5rem_10rem_minmax(0,1.8fr)]"
                  >
                    <span className="font-mono text-[13px] font-semibold text-[#F8FAFC]">
                      {check.priority}
                    </span>
                    <span>
                      <span
                        className="inline-block rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide"
                        style={{
                          color: GATE_TONE[check.result],
                          background: `${GATE_TONE[check.result]}26`,
                        }}
                      >
                        {check.result}
                      </span>
                    </span>
                    <span className="hidden font-mono text-[13px] break-words text-[#CBD5E1] sm:block">
                      {check.ruleId}
                    </span>
                    <span className="text-[13px] leading-relaxed text-[#94A3B8]">
                      <strong className="font-semibold text-[#F8FAFC]">{check.name}.</strong>{" "}
                      {check.explanation}
                      <span className="mt-1 block font-mono text-[11px] text-[#64748B] sm:hidden">
                        {check.ruleId}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* SECTION 07 — Paper Execution Outcome */}
          <section aria-labelledby="chapter-outcome" className="space-y-5">
            <div className="border-b border-white/8 pb-4">
              <h2
                id="chapter-outcome"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/30 bg-[#547D83]/15 text-[#B2D8DC]">
                  <FileCheck className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Paper Execution Outcome
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                The governed result recorded on the paper account
              </p>
            </div>

            <div className="space-y-4">
              {/* Outcome row */}
              <div className="grid grid-cols-1 gap-4 rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.3fr)] sm:p-6">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
                    Action
                  </p>
                  <p className="mt-2 text-[14px] font-semibold text-[#F8FAFC]">
                    {story.illustrativeOutcome.action}
                  </p>
                </div>
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
                    Status
                  </p>
                  <p className="mt-2 font-mono text-[13px] font-semibold uppercase tracking-wide text-[#00D084]">
                    {formatOutcomeStatus(story.illustrativeOutcome.status)}
                  </p>
                </div>
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
                    Rationale
                  </p>
                  <p className="mt-2 text-[13px] leading-relaxed text-[#94A3B8]">
                    {story.illustrativeOutcome.rationale}
                  </p>
                </div>
              </div>

              {/* Paper-only disclaimer */}
              <div className="flex items-start gap-3 rounded-xl border border-[#547D83]/30 bg-[#547D83]/10 p-4">
                <ShieldCheck
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#B2D8DC]"
                  aria-hidden="true"
                />
                <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
                  <strong className="font-semibold text-[#F8FAFC]">Paper only.</strong> This
                  represents a governed outcome and is not an authorization or broker receipt.
                </p>
              </div>
            </div>
          </section>
        </div>

        {/* SECTION 08 — ShadowFund Counterfactual Matrix & Lessons */}
        <section aria-labelledby="chapter-lessons" className="space-y-5">
          <div className="border-b border-white/8 pb-4">
            <h2
              id="chapter-lessons"
              className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#818CF8]">
                <GitCompareArrows className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              ShadowFund Counterfactual Matrix &amp; Lessons
            </h2>
            <p className="mt-1 text-[12px] text-[#64748B]">What every branch would have done.</p>
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
              const isActive = branch.branchKey === "chosen";
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
      </article>
    </div>
  );
}

type DecisionNode = StoryDetail["decisionTree"][number];

type PipelineState = "complete" | "modify" | "stopped" | "not-run";

type PipelineStage = {
  id: string;
  title: string;
  statusLabel: string;
  detail: string;
  state: PipelineState;
};

// The raw decision tree may carry many nodes (seven specialists + risk, rules,
// paper, shadowfund). The pipeline collapses them into five canonical stages,
// with the seven specialists grouped into a single "Research" step.
const CANONICAL_STAGES = [
  {
    key: "catalyst",
    title: "Catalyst",
    detail: "Earnings print classified, reaction gap measured.",
  },
  { key: "research", title: "Research", detail: "7 specialist agents evaluated independently." },
  { key: "proposal", title: "Proposal", detail: "Bounded call spread synthesized from consensus." },
  { key: "risk", title: "Risk", detail: "Risk AI challenge raised and logged." },
  { key: "rules", title: "Rules", detail: "Governance gate evaluated the exact payload." },
] as const;

// Raw node ids the API emits, grouped to each canonical stage.
const SPECIALIST_IDS = [
  "news-intelligence",
  "quantitative-analysis",
  "industry-intelligence",
  "fundamental-analysis",
  "macroeconomic-analysis",
  "market-reaction-mispricing",
];
const STAGE_NODE_IDS: Record<string, string[]> = {
  catalyst: ["catalyst", "news-intelligence"],
  research: SPECIALIST_IDS,
  proposal: ["proposal", "trading-decision"],
  risk: ["risk", "risk-management"],
  rules: ["rules", "rules-engine"],
};

const STOP_STATUSES = new Set([
  "fail",
  "no_trade",
  "degraded",
  "incomplete",
  "not_run",
  "not_evaluated",
]);

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function statusLabelFor(state: PipelineState, rawStatus: string): string {
  switch (state) {
    case "complete":
      return "Complete";
    case "modify":
      return "Modify";
    case "not-run":
      return "Not run";
    case "stopped":
      return titleCase(rawStatus.replaceAll("_", " "));
  }
}

/** Reduce the raw nodes belonging to one stage into a single pipeline state. */
function stageStateFrom(statuses: string[]): { state: PipelineState; raw: string } {
  if (statuses.length === 0) return { state: "not-run", raw: "not_run" };
  // If every node for the stage never ran, the stage did not run.
  if (statuses.every((s) => s === "not_run")) return { state: "not-run", raw: "not_run" };
  // A terminal-stop status anywhere in the stage marks it as stopped.
  const stop = statuses.find((s) => STOP_STATUSES.has(s) && s !== "not_run");
  if (stop) return { state: "stopped", raw: stop };
  if (statuses.includes("modify")) return { state: "modify", raw: "modify" };
  return { state: "complete", raw: "complete" };
}

/**
 * Collapse the raw decision tree into the five canonical pipeline stages. Each
 * stage's state is derived from the recorded status of the node(s) it maps to,
 * so degraded or no-trade stories still surface a "Not run" / terminal stage.
 */
function buildPipeline(nodes: DecisionNode[]): PipelineStage[] {
  const byId = new Map(nodes.map((node) => [node.id.toLowerCase(), node]));
  return CANONICAL_STAGES.map((stage) => {
    const statuses = STAGE_NODE_IDS[stage.key]
      .map((id) => byId.get(id))
      .filter((node): node is DecisionNode => node !== undefined)
      .map((node) => (node.status ?? "").toLowerCase());
    const { state, raw } = stageStateFrom(statuses);
    return {
      id: stage.key,
      title: stage.title,
      statusLabel: statusLabelFor(state, raw),
      detail: stage.detail,
      state,
    };
  });
}

// Spectral tone per pipeline state (DESIGN.md Section 3.6 semantic status).
const STATE_TONE: Record<PipelineState, string> = {
  complete: "#00D084",
  modify: "#F59E0B",
  stopped: "#FF6B6B",
  "not-run": "#64748B",
};

function PipelineNode({ stage }: { stage: PipelineStage }) {
  const tone = STATE_TONE[stage.state];
  const isRun = stage.state !== "not-run";
  return (
    <div className="flex flex-1 flex-col items-center px-2 text-center">
      <span
        aria-hidden="true"
        className="grid h-9 w-9 place-items-center rounded-full border-2 transition-colors"
        style={{
          borderColor: isRun ? tone : "rgba(255,255,255,0.12)",
          background: isRun ? `${tone}1f` : "transparent",
        }}
      >
        <span className="h-2 w-2 rounded-full" style={{ background: isRun ? tone : "#64748B" }} />
      </span>
      <span
        className="mt-3 text-[14px] font-semibold"
        style={{ color: isRun ? "#F8FAFC" : "#64748B" }}
      >
        {stage.title}
      </span>
      <span className="mt-1 font-mono text-[11px] font-semibold" style={{ color: tone }}>
        {stage.statusLabel}
      </span>
      <span className="mt-2 text-[12px] leading-relaxed text-[#94A3B8]">{stage.detail}</span>
    </div>
  );
}

function DecisionPipeline({ nodes }: { nodes: DecisionNode[] }) {
  const stages = buildPipeline(nodes);

  return (
    <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-6 backdrop-blur-xl sm:p-8">
      <ol className="flex flex-col gap-8 sm:flex-row sm:items-start sm:gap-0">
        {stages.map((stage, index) => (
          <li key={stage.id} className="flex flex-1 items-start">
            <PipelineNode stage={stage} />
            {index < stages.length - 1 && (
              <span
                aria-hidden="true"
                className="mt-[1.05rem] hidden h-px flex-1 sm:block"
                style={{ background: "rgba(255,255,255,0.1)" }}
              />
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
