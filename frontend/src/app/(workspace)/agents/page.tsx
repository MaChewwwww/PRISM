import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/workspace/date-range-control";
import { StoryBarChart } from "@/features/story/story-charts";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
  StateBadge,
} from "@/components/workspace/workspace-ui";
import { formatTokens } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { loadAgentObservability } from "@/features/story/presentation-api";
import { TryAgentButton } from "@/features/agents/agent-playground-modal";

export default async function AgentsPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const observability = await loadAgentObservability(range);
  const allRuns = observability.agents.flatMap((agent) => agent.runs);
  const totalTokens = allRuns.reduce(
    (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
    0,
  );
  const tokenChart = observability.agents.map((agent) => ({
    label: agent.name.split(" ")[0],
    value: String(
      agent.runs.reduce(
        (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
        0,
      ),
    ),
  }));
  return (
    <>
      <PageHeader
        eyebrow="Agents and tools"
        title="Know what contributed to every decision"
        description="Inspect responsibilities, run cadence, models, prompt versions, token usage, read-only tools, and planned MCP surfaces."
      >
        <TryAgentButton label="Try Agent" />
      </PageHeader>

      <DemoDataNotice />
      <DateRangeControl range={range} />
      <MetricStrip
        metrics={[
          {
            label: "Agent definitions",
            value: String(observability.agents.length),
            detail: "Provider-neutral roles",
          },
          {
            label: "Runs in period",
            value: String(allRuns.length),
            detail: "Fixed illustrative history",
          },
          {
            label: "Visible tokens",
            value: formatTokens(totalTokens),
            detail: "Input + output + cached",
          },
          {
            label: "Degraded / failed",
            value: String(allRuns.filter((run) => run.status !== "complete").length),
            detail: "Explicit terminal states",
          },
        ]}
      />
      <Section
        id="agent-usage"
        title="Token usage by agent"
        description="Which roles consumed the illustrative model budget in this period?"
      >
        <StoryBarChart
          title="Visible token consumption"
          description="Input, output, and cached tokens from fixed demo runs. No provider billing claim is made."
          summary={`${formatTokens(totalTokens)} visible tokens`}
          data={tokenChart}
        />
      </Section>
      <Section
        id="authority-pipeline"
        title="Authority pipeline"
        description="AI contributions stop before deterministic authorization; execution remains paper-only and disabled by default."
      >
        <ol className="agent-list">
          {observability.components.map((component) => (
            <li key={component.id}>
              <div>
                <p className="record-kicker">Stage {component.stage}</p>
                <h3>{component.name}</h3>
                <p>{component.description}</p>
              </div>
              <dl>
                <div>
                  <dt>Authority</dt>
                  <dd>{component.authority}</dd>
                </div>
                <div>
                  <dt>Kind</dt>
                  <dd>{component.kind.replaceAll("_", " ")}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      </Section>
      <Section
        id="agent-registry"
        title="Seven specialists, risk, and post-analysis"
        description="Each AI role has bounded research, proposal, risk, or recommendation authority."
      >
        <ol className="agent-list">
          {observability.agents.map((agent) => {
            const tokens = agent.runs.reduce(
              (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
              0,
            );
            return (
              <li key={agent.id}>
                <div>
                  <p className="record-kicker">{agent.cadence}</p>
                  <h3>
                    <Link href={`/agents/${agent.id}`}>{agent.name}</Link>
                  </h3>
                  <p>{agent.role}</p>
                  <ul>
                    {agent.dependencies.map((dependency) => (
                      <li key={dependency}>{dependency}</li>
                    ))}
                  </ul>
                </div>
                <dl>
                  <div>
                    <dt>Model</dt>
                    <dd>{agent.model}</dd>
                  </div>
                  <div>
                    <dt>Prompt</dt>
                    <dd>{agent.promptVersion}</dd>
                  </div>
                  <div>
                    <dt>Runs</dt>
                    <dd>{agent.runs.length}</dd>
                  </div>
                  <div>
                    <dt>Tokens</dt>
                    <dd>{formatTokens(tokens)}</dd>
                  </div>
                </dl>
                <Link
                  className="icon-link"
                  href={`/agents/${agent.id}`}
                  aria-label={`Open ${agent.name}`}
                >
                  <ArrowUpRight aria-hidden="true" />
                </Link>
              </li>
            );
          })}
        </ol>
      </Section>
      <Section
        id="tool-inventory"
        title="Tools, MCP, and model surfaces"
        description="Used and planned dependencies are separated so a future integration is never mistaken for a recorded invocation."
      >
        <div className="table-wrap">
          <table>
            <caption>Illustrative runtime dependency inventory</caption>
            <thead>
              <tr>
                <th>Name</th>
                <th>Kind</th>
                <th>State</th>
                <th>Calls</th>
                <th>Success</th>
                <th>Median latency</th>
                <th>Purpose</th>
              </tr>
            </thead>
            <tbody>
              {observability.tools.map((tool) => (
                <tr key={tool.id}>
                  <th scope="row">{tool.name}</th>
                  <td>{tool.kind}</td>
                  <td>
                    <StateBadge state={tool.state} />
                  </td>
                  <td>{tool.calls}</td>
                  <td>{tool.successRate}</td>
                  <td>{tool.medianLatency}</td>
                  <td>{tool.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  );
}
