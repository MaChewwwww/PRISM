import { ArrowLeft, Check, GitCompareArrows, MessageSquareText, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryLineChart } from "@/components/product/story-charts";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  ProvenanceLabel,
  Section,
  StateBadge,
} from "@/components/product/workspace-ui";
import { formatDateTime, formatTokens } from "@/features/story/formatters";
import { getStory } from "@/features/story/story-data";

export default async function StoryDetailPage({
  params,
}: {
  params: Promise<{ storyId: string }>;
}) {
  const { storyId } = await params;
  const story = getStory(storyId);
  if (!story) notFound();
  const tokens = story.transcript.reduce(
    (total, step) => total + (step.inputTokens ?? 0) + (step.outputTokens ?? 0),
    0,
  );

  return (
    <>
      <Link className="back-link" href="/stories">
        <ArrowLeft aria-hidden="true" /> All decision stories
      </Link>
      <PageHeader
        eyebrow={`${story.symbol} · ${story.category}`}
        title={story.title}
        description={story.summary}
      >
        <StateBadge state={story.outcome} />
      </PageHeader>
      <DemoDataNotice />
      <MetricStrip
        metrics={[
          {
            label: "Rule Result",
            value: story.ruleResult,
            detail: "Authoritative deterministic trace",
          },
          { label: "Active Outcome", value: story.paperImpact, detail: "Paper execution P&L" },
          {
            label: "Best Shadow Path",
            value: story.bestAlternativeImpact,
            detail: "Counterfactual simulation",
          },
          {
            label: "Model Tokens",
            value: formatTokens(tokens),
            detail: "Input + Output + Cached",
          },
        ]}
      />

      <div className="story-layout">
        <article className="story-chapters space-y-8">
          {/* PART I: WHAT HAPPENED */}
          <div className="space-y-6">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#547D83]/15 border border-[#547D83]/30 w-fit">
              <span className="h-2 w-2 rounded-full bg-[#00D084]" />
              <span className="text-xs font-semibold uppercase tracking-wider text-[#B2D8DC]">
                Part I · What Happened (The Active Path)
              </span>
            </div>

            <Section
              id="chapter-catalyst"
              title="01 · Catalyst & Market Reaction Gap"
              description="Breaking news signal ingested, event classified, and observed price shock compared against historical analog expectations."
            >
              <div className="chapter-lead prism-glass-card">
                <div>
                  <span>Headline</span>
                  <strong>{story.catalyst.headline}</strong>
                </div>
                <div>
                  <span>Classification</span>
                  <strong>{story.catalyst.classification}</strong>
                </div>
                <div>
                  <span>Observed Move</span>
                  <strong className="text-[#38BDF8]">{story.catalyst.observedMove}</strong>
                </div>
                <div>
                  <span>Expected Move</span>
                  <strong className="text-slate-300">{story.catalyst.expectedMove}</strong>
                </div>
              </div>
              <StoryLineChart
                title="Catalyst Reaction Timeline"
                description="Observed price reaction against historical analog baseline and sector movement."
                summary={`${story.catalyst.observedMove} observed vs. ${story.catalyst.expectedMove} historical median`}
                data={story.marketPath}
                series={[
                  { key: "actual", label: "Observed Reaction", color: "#38BDF8" },
                  {
                    key: "alternative",
                    label: "Analog Expectation",
                    color: "#818CF8",
                    dashed: true,
                  },
                  {
                    key: "benchmark",
                    label: "Sector Movement",
                    color: "#64748B",
                    dashed: true,
                  },
                ]}
              />
            </Section>

            <Section
              id="chapter-tree"
              title="02 · Autonomous Agent Perspective Chain"
              description="How the decision evolved through sequential analytical angles: Market Context → Research → Proposal → Risk AI → Deterministic Rule Gate."
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
                      {step.kind === "tool-call" ? (
                        <GitCompareArrows aria-hidden="true" />
                      ) : step.kind === "rule-gate" ? (
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
                      {step.inputTokens !== undefined && (
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
                      <h3 className="text-sm font-medium text-white">{check.name}</h3>
                      <p className="text-xs text-slate-300 mt-0.5">{check.explanation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            <Section
              id="chapter-outcome"
              title="05 · Active Paper Execution Outcome"
              description="The authorized paper order submission, fill execution, and active P&L progression."
            >
              <div className="outcome-statement prism-glass-card p-4 border-l-4 border-l-[#00D084]">
                <Check aria-hidden="true" className="text-[#00D084]" />
                <div>
                  <span className="text-xs font-mono text-[#00D084] uppercase tracking-wider">
                    {story.paperOutcome.status}
                  </span>
                  <h3 className="text-base font-semibold text-white">
                    {story.paperOutcome.action}
                  </h3>
                  <p className="text-sm text-slate-300 mt-1">{story.paperOutcome.rationale}</p>
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
                  <caption>Active vs. Shadow Branch Performance Comparison</caption>
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
                        className={branch.id === "actual" ? "bg-[#547D83]/10 font-semibold" : ""}
                      >
                        <th scope="row">
                          {branch.label}
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

        <aside className="story-inspector" aria-label="Story evidence inspector">
          <p className="eyebrow">Evidence inspector</p>
          <h2>What this story rests on</h2>
          <ul>
            {story.evidence.map((item) => (
              <li key={item.label}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.source}</span>
                </div>
                <ProvenanceLabel provenance={item.provenance} />
              </li>
            ))}
          </ul>
          <div className="inspector-note">
            <ShieldCheck aria-hidden="true" />
            <p>
              All evidence is illustrative. No provider, brokerage account, MCP server, or LLM was
              contacted to render this story.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
