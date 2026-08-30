import { ArrowLeft, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DateRangeControl } from "@/components/workspace/date-range-control";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
  StateBadge,
} from "@/components/workspace/workspace-ui";
import { formatDateTime, formatTokens } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { getAgent } from "@/features/story/presentation-api";
import { TryAgentButton, type AgentAction } from "@/features/agents/agent-playground-modal";

function mapAgentIdToAction(id: string): AgentAction {
  const lower = id.toLowerCase();
  if (lower.includes("decision") || lower.includes("trading") || lower.includes("cio"))
    return "decision";
  if (lower.includes("fundamental")) return "fundamental";
  if (lower.includes("quant")) return "quant";
  if (lower.includes("industry")) return "industry";
  if (lower.includes("macro")) return "macro";
  if (lower.includes("reaction")) return "reaction";
  if (lower.includes("news")) return "news";
  return "decision";
}

export default async function AgentDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ agentId: string }>;
  searchParams: Promise<SearchValues>;
}) {
  const { agentId } = await params;
  const agent = await getAgent(agentId);
  if (!agent) notFound();
  const range = readDateRange(await searchParams);
  const runs = agent.runs.filter(
    (run) => run.occurredAt.slice(0, 10) >= range.from && run.occurredAt.slice(0, 10) <= range.to,
  );
  const tokens = runs.reduce(
    (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
    0,
  );
  const averageDuration = runs.length
    ? Math.round(runs.reduce((total, run) => total + run.durationMs, 0) / runs.length)
    : 0;
  return (
    <>
      <Link className="back-link" href="/agents">
        <ArrowLeft aria-hidden="true" /> All agents and tools
      </Link>
      <PageHeader eyebrow="Agent detail" title={agent.name} description={agent.role}>
        <div className="flex items-center gap-3">
          <StateBadge state="decision support only" />
          <TryAgentButton
            agentId={mapAgentIdToAction(agentId)}
            label={`Try ${agent.name.split(" ")[0]}`}
          />
        </div>
      </PageHeader>

      <DemoDataNotice />
      <DateRangeControl range={range} />
      <MetricStrip
        metrics={[
          { label: "Cadence", value: agent.cadence, detail: "Illustrative trigger" },
          { label: "Runs", value: String(runs.length), detail: "In selected period" },
          { label: "Visible tokens", value: formatTokens(tokens), detail: "No hidden reasoning" },
          {
            label: "Average duration",
            value: runs.length ? `${averageDuration} ms` : "—",
            detail: "Fixture latency",
          },
        ]}
      />
      <div className="agent-context">
        <div>
          <p className="eyebrow">Responsibility</p>
          <h2>{agent.description}</h2>
        </div>
        <dl>
          <div>
            <dt>Model</dt>
            <dd>{agent.model}</dd>
          </div>
          <div>
            <dt>Prompt version</dt>
            <dd>{agent.promptVersion}</dd>
          </div>
        </dl>
      </div>
      <Section
        id="dependencies"
        title="Bounded dependencies"
        description="This agent sees only the context required for its responsibility."
      >
        <ul className="dependency-list">
          {agent.dependencies.map((dependency) => (
            <li key={dependency}>
              <CheckCircle2 aria-hidden="true" />
              {dependency}
            </li>
          ))}
        </ul>
      </Section>
      <Section
        id="run-history"
        title="Run history"
        description="Every result has an explicit trigger, terminal state, latency, token count, and concise visible summary."
      >
        {runs.length ? (
          <ol className="run-list">
            {runs.map((run) => (
              <li key={run.id}>
                <time dateTime={run.occurredAt}>{formatDateTime(run.occurredAt)}</time>
                <div>
                  <div>
                    <strong>{run.trigger}</strong>
                    <StateBadge state={run.status} />
                  </div>
                  <p>{run.summary}</p>
                </div>
                <dl>
                  <div>
                    <dt>Duration</dt>
                    <dd>{run.durationMs} ms</dd>
                  </div>
                  <div>
                    <dt>Input</dt>
                    <dd>{formatTokens(run.inputTokens)}</dd>
                  </div>
                  <div>
                    <dt>Output</dt>
                    <dd>{formatTokens(run.outputTokens)}</dd>
                  </div>
                  <div>
                    <dt>Cached</dt>
                    <dd>{formatTokens(run.cachedTokens)}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ol>
        ) : (
          <p className="inline-empty">No illustrative runs fall inside this date range.</p>
        )}
      </Section>
    </>
  );
}
