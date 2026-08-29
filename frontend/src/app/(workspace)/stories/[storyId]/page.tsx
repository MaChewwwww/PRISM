import { ArrowLeft, Check, GitCompareArrows, MessageSquareText, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryCatalystChart } from "@/components/product/story-catalyst-chart";
import { StateBadge } from "@/components/product/workspace-ui";
import { formatDate, formatDateTime, formatTokens } from "@/features/story/formatters";
import { getStory } from "@/features/story/presentation-api";

const RULE_RESULT_TONE: Record<string, string> = {
  PASS: "text-[#00D084]",
  MODIFY: "text-[#F59E0B]",
  FAIL: "text-[#FF6B6B]",
  NOT_EVALUATED: "text-[#547D83]",
};

function shortStoryId(id: string): string {
  const tail = id.replace(/[^a-z0-9]/gi, "").slice(-2);
  return `story #${tail || id.slice(0, 4)}`;
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
    <div className="space-y-10">
      {/* Top row: back link + status pill */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/stories"
          className="inline-flex items-center gap-2 rounded-full border border-white/8 bg-white/5 px-3.5 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Decision Stories
        </Link>
        <StateBadge state={story.ruleResult === "MODIFY" ? "MODIFY" : story.outcome} />
      </div>

      {/* Title + kicker */}
      <header>
        <h1 className="text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-tight tracking-tight text-[#F8FAFC]">
          {story.title}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[12px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
          <span className="font-semibold text-[#CBD5E1]">{story.symbol}</span>
          <span aria-hidden="true" className="text-white/20">
            |
          </span>
          <time dateTime={story.occurredAt}>{formatDate(story.occurredAt)}</time>
          <span aria-hidden="true" className="text-white/20">
            |
          </span>
          <span>{shortStoryId(story.id)}</span>
        </div>
      </header>

      {/* Metric strip (DESIGN.md Section 5.2 glass; Section 3.6 semantic tones) */}
      <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-white/8 border-t-white/16 bg-white/8 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-[#0B0F14] p-5">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Rule Result
          </dt>
          <dd className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${ruleTone}`}>
            {story.ruleResult}
          </dd>
        </div>
        <div className="bg-[#0B0F14] p-5">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Chosen Outcome
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#00D084]">
            {story.chosenPathImpact}
          </dd>
        </div>
        <div className="bg-[#0B0F14] p-5">
          <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            Best Shadow Path
          </dt>
          <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#818CF8]">
            {story.bestAlternativeImpact}
          </dd>
        </div>
        <div className="bg-[#0B0F14] p-5">
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
          <Section
            id="chapter-tree"
            title="02 · Autonomous Agent Perspective Chain"
            description="Seven specialist perspectives feed Trading Decision, then Risk Management and the deterministic Rules Engine."
          >
            <ol className="decision-tree">
              {story.decisionTree.map((node, index) => (
                <li
                  key={node.id}
                  className="prism-glass-card p-4 my-2 transition-all hover:border-[#547D83]/40"
                >
                  <span className="tree-line" aria-hidden="true" />
                  <div className="tree-node-index font-mono">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-[#547D83]">
                      {node.actor}
                    </p>
                    <h3 className="text-base font-medium text-white">{node.label}</h3>
                    <span className="text-sm text-slate-300">{node.detail}</span>
                  </div>
                  <StateBadge state={node.status} />
                </li>
              ))}
            </ol>
          </Section>

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

          <Section
            id="chapter-lessons"
            title="06 · ShadowFund Counterfactual Matrix & Lessons"
            description="Simulated parallel paths evaluated under identical market conditions to measure Counterfactual Alpha and Decision Regret."
          >
            <div className="branch-table table-wrap prism-glass-card">
              <table>
                <caption>Active Portfolio path vs. ShadowFund branch comparison</caption>
                <thead>
                  <tr>
                    <th>Branch</th>
                    <th>Controlled Variation</th>
                    <th>P&amp;L</th>
                    <th>Drawdown</th>
                    <th>Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {story.alternatives.map((branch) => (
                    <tr
                      key={branch.id}
                      className={branch.id === "chosen" ? "bg-[#547D83]/10 font-semibold" : ""}
                    >
                      <th scope="row">
                        {branch.label === "Illustrative governed path"
                          ? "Active Portfolio"
                          : branch.label}
                        <span className="text-xs font-mono block text-slate-400 font-normal">
                          {branch.status}
                        </span>
                      </th>
                      <td>{branch.variation}</td>
                      <td className="font-mono tabular-nums font-semibold text-[#00D084]">
                        {branch.pnl}
                      </td>
                      <td className="font-mono tabular-nums text-[#FF6B6B]">{branch.drawdown}</td>
                      <td className="font-mono tabular-nums">{branch.coverage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ol className="lesson-list mt-4 space-y-2">
              {story.lessons.map((lesson, index) => (
                <li key={lesson} className="prism-glass-card p-3 flex items-start gap-3">
                  <span className="font-mono text-[#818CF8] font-bold">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <p className="text-sm text-slate-200">{lesson}</p>
                </li>
              ))}
            </ol>
          </Section>
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
