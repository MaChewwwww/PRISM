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
          { label: "Rule result", value: story.ruleResult, detail: "Deterministic fixture trace" },
          { label: "Paper result", value: story.paperImpact, detail: "Illustrative only" },
          {
            label: "Best alternative",
            value: story.bestAlternativeImpact,
            detail: "Simulated, non-executable",
          },
          {
            label: "Visible model tokens",
            value: formatTokens(tokens),
            detail: "No hidden reasoning stored",
          },
        ]}
      />

      <div className="story-layout">
        <article className="story-chapters">
          <Section
            id="chapter-catalyst"
            title="01 · Catalyst and market reaction"
            description="What changed, when it was observed, and how the synthetic move compared with its analog range."
          >
            <div className="chapter-lead">
              <div>
                <span>Headline</span>
                <strong>{story.catalyst.headline}</strong>
              </div>
              <div>
                <span>Classification</span>
                <strong>{story.catalyst.classification}</strong>
              </div>
              <div>
                <span>Observed</span>
                <strong>{story.catalyst.observedMove}</strong>
              </div>
              <div>
                <span>Expected</span>
                <strong>{story.catalyst.expectedMove}</strong>
              </div>
            </div>
            <StoryLineChart
              title="Reaction path"
              description="Indexed synthetic movement around the fictional catalyst."
              summary={`${story.catalyst.observedMove} observed versus ${story.catalyst.expectedMove} expected`}
              data={story.marketPath}
              series={[
                { key: "actual", label: "Observed fixture", color: "var(--primary)" },
                {
                  key: "alternative",
                  label: "Analog expectation",
                  color: "var(--alternative)",
                  dashed: true,
                },
                {
                  key: "benchmark",
                  label: "Sector fixture",
                  color: "var(--benchmark)",
                  dashed: true,
                },
              ]}
            />
          </Section>

          <Section
            id="chapter-tree"
            title="02 · Agent decision tree"
            description="How the record progressed—and where authority changed—from untrusted evidence to deterministic governance."
          >
            <ol className="decision-tree">
              {story.decisionTree.map((node, index) => (
                <li key={node.id}>
                  <span className="tree-line" aria-hidden="true" />
                  <div className="tree-node-index">{String(index + 1).padStart(2, "0")}</div>
                  <div>
                    <p>{node.actor}</p>
                    <h3>{node.label}</h3>
                    <span>{node.detail}</span>
                  </div>
                  <StateBadge state={node.status} />
                </li>
              ))}
            </ol>
          </Section>

          <Section
            id="chapter-transcript"
            title="03 · Sanitized conversation and tools"
            description="Concise rationale, evidence, model metadata, and tool activity—never hidden chain-of-thought or sensitive payloads."
          >
            <ol className="transcript">
              {story.transcript.map((step) => (
                <li key={step.id}>
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
                      <span>{step.actor}</span>
                      <time dateTime={step.occurredAt}>{formatDateTime(step.occurredAt)}</time>
                    </div>
                    <h3>{step.title}</h3>
                    <p>{step.summary}</p>
                    <ul>
                      {step.evidenceRefs.map((ref) => (
                        <li key={ref}>{ref}</li>
                      ))}
                    </ul>
                  </div>
                  <dl>
                    {step.model && (
                      <div>
                        <dt>Model</dt>
                        <dd>{step.model}</dd>
                      </div>
                    )}
                    {step.promptVersion && (
                      <div>
                        <dt>Prompt</dt>
                        <dd>{step.promptVersion}</dd>
                      </div>
                    )}
                    {step.inputTokens !== undefined && (
                      <div>
                        <dt>Tokens</dt>
                        <dd>{formatTokens(step.inputTokens + (step.outputTokens ?? 0))}</dd>
                      </div>
                    )}
                    {step.latencyMs !== undefined && (
                      <div>
                        <dt>Latency</dt>
                        <dd>{step.latencyMs} ms</dd>
                      </div>
                    )}
                  </dl>
                </li>
              ))}
            </ol>
          </Section>

          <Section
            id="chapter-rules"
            title="04 · Deterministic rule gate"
            description="Agent judgment stops here. Only explicit deterministic checks can permit progression."
          >
            <div className="rule-trace">
              {story.ruleChecks.map((check) => (
                <div key={check.name}>
                  <StateBadge state={check.result} />
                  <div>
                    <h3>{check.name}</h3>
                    <p>{check.explanation}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section
            id="chapter-outcome"
            title="05 · What happened next"
            description="The recorded fictional paper outcome, including stopped and no-trade paths."
          >
            <div className="outcome-statement">
              <Check aria-hidden="true" />
              <div>
                <span>{story.paperOutcome.status}</span>
                <h3>{story.paperOutcome.action}</h3>
                <p>{story.paperOutcome.rationale}</p>
              </div>
            </div>
          </Section>

          <Section
            id="chapter-lessons"
            title="06 · Alternatives and lessons"
            description="Counterfactual evidence asks what could improve; it never rewrites history or becomes an order."
          >
            <div className="branch-table table-wrap">
              <table>
                <caption>Actual-shaped and simulated branch comparison</caption>
                <thead>
                  <tr>
                    <th>Branch</th>
                    <th>Controlled variation</th>
                    <th>P&amp;L</th>
                    <th>Drawdown</th>
                    <th>Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {story.alternatives.map((branch) => (
                    <tr key={branch.id}>
                      <th scope="row">
                        {branch.label}
                        <span>{branch.status}</span>
                      </th>
                      <td>{branch.variation}</td>
                      <td>{branch.pnl}</td>
                      <td>{branch.drawdown}</td>
                      <td>{branch.coverage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ol className="lesson-list">
              {story.lessons.map((lesson, index) => (
                <li key={lesson}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <p>{lesson}</p>
                </li>
              ))}
            </ol>
          </Section>
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
              All evidence is fictional. No provider, brokerage account, MCP server, or LLM was
              contacted to render this story.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
