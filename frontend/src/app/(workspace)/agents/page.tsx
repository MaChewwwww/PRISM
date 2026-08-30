import { ArrowUpRight, BarChart3, GitBranch, Sparkles, Wrench } from "lucide-react";
import Link from "next/link";

import { StoryBarChart } from "@/features/story/story-charts";
import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { formatTokens } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { loadAgentObservability } from "@/features/story/presentation-api";

const METRIC_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]";

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
  const failed = allRuns.filter((run) => run.status !== "complete").length;
  const tokenChart = observability.agents.map((agent) => ({
    label: agent.name.split(" ")[0],
    value: String(
      agent.runs.reduce(
        (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
        0,
      ),
    ),
  }));

  const metrics = [
    {
      label: "Agent definitions",
      value: String(observability.agents.length),
      detail: "Provider-neutral roles",
      tone: "text-[#F8FAFC]",
    },
    {
      label: "Runs in period",
      value: String(allRuns.length),
      detail: "Fixed illustrative history",
      tone: "text-[#F8FAFC]",
    },
    {
      label: "Visible tokens",
      value: formatTokens(totalTokens),
      detail: "Input + output + cached",
      tone: "text-[#F8FAFC]",
    },
    {
      label: "Degraded / failed",
      value: String(failed),
      detail: "Explicit terminal states",
      tone: failed > 0 ? "text-[#F59E0B]" : "text-[#00D084]",
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Agents and tools"
        title="Know what contributed to every decision"
        description="Inspect responsibilities, run cadence, models, prompt versions, token usage, read-only tools, and planned MCP surfaces."
      >
        <RangePresets range={range} />
      </PageHeader>

      {/* Metric cards */}
      <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className={METRIC_CARD}>
            <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
              {metric.label}
            </dt>
            <dd className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${metric.tone}`}>
              {metric.value}
            </dd>
            <p className="mt-1 text-[11px] text-[#64748B]">{metric.detail}</p>
          </div>
        ))}
      </dl>

      {/* Token usage */}
      <section aria-labelledby="agent-usage" className="mt-6">
        <SectionHeading
          id="agent-usage"
          icon={BarChart3}
          title="Token Usage by Agent"
          subtitle="Which roles consumed the illustrative model budget in this period?"
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <StoryBarChart
            title="Visible token consumption"
            description="Input, output, and cached tokens from fixed demo runs. No provider billing claim is made."
            summary={`${formatTokens(totalTokens)} visible tokens`}
            data={tokenChart}
          />
        </div>
      </section>

      {/* Authority pipeline */}
      <section aria-labelledby="authority-pipeline" className="mt-6">
        <SectionHeading
          id="authority-pipeline"
          icon={GitBranch}
          title="Authority Pipeline"
          subtitle="AI contributions stop before deterministic authorization; execution remains paper-only and disabled by default."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {observability.components.map((component) => (
            <div key={component.id} className={`${SECTION_CARD} p-5`}>
              <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#547D83]">
                Stage {component.stage}
              </span>
              <h3 className="mt-2 text-[15px] font-semibold text-[#F8FAFC]">{component.name}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-[#94A3B8]">
                {component.description}
              </p>
              <dl className="mt-4 space-y-2 border-t border-white/8 pt-3">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-[12px] text-[#64748B]">Authority</dt>
                  <dd className="text-[13px] text-[#CBD5E1]">{component.authority}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-[12px] text-[#64748B]">Kind</dt>
                  <dd className="text-[13px] text-[#CBD5E1]">
                    {component.kind.replaceAll("_", " ")}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      </section>

      {/* Agent registry */}
      <section aria-labelledby="agent-registry" className="mt-6">
        <SectionHeading
          id="agent-registry"
          icon={Sparkles}
          title="Specialists, Risk, and Post-Analysis"
          subtitle="Each AI role has bounded research, proposal, risk, or recommendation authority."
        />
        <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {observability.agents.map((agent) => {
            const tokens = agent.runs.reduce(
              (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
              0,
            );
            return (
              <li key={agent.id}>
                <Link
                  href={`/agents/${agent.id}`}
                  className={`group flex h-full flex-col gap-4 ${SECTION_CARD} p-5 outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
                        {agent.cadence}
                      </p>
                      <h3 className="mt-1 text-[16px] font-semibold text-[#F8FAFC] transition-colors group-hover:text-[#B2D8DC]">
                        {agent.name}
                      </h3>
                      <p className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
                        {agent.role}
                      </p>
                    </div>
                    <span
                      aria-hidden="true"
                      className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-white/8 text-[#64748B] transition-colors group-hover:border-[#547D83]/40 group-hover:text-[#B2D8DC]"
                    >
                      <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </span>
                  </div>

                  {agent.dependencies.length > 0 && (
                    <ul className="flex flex-wrap gap-1.5">
                      {agent.dependencies.map((dependency) => (
                        <li
                          key={dependency}
                          className="rounded border border-white/8 bg-white/5 px-2 py-0.5 text-[11px] text-[#94A3B8]"
                        >
                          {dependency}
                        </li>
                      ))}
                    </ul>
                  )}

                  <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-t border-white/8 pt-4 sm:grid-cols-4">
                    {[
                      { dt: "Model", dd: agent.model },
                      { dt: "Prompt", dd: agent.promptVersion },
                      { dt: "Runs", dd: String(agent.runs.length) },
                      { dt: "Tokens", dd: formatTokens(tokens) },
                    ].map((row) => (
                      <div key={row.dt}>
                        <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                          {row.dt}
                        </dt>
                        <dd className="mt-1 font-mono text-[13px] text-[#CBD5E1]">{row.dd}</dd>
                      </div>
                    ))}
                  </dl>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Tools inventory */}
      <section aria-labelledby="tool-inventory" className="mt-6">
        <SectionHeading
          id="tool-inventory"
          icon={Wrench}
          title="Tools, MCP, and Model Surfaces"
          subtitle="Used and planned dependencies are separated so a future integration is never mistaken for a recorded invocation."
        />
        <div className={`${SECTION_CARD} overflow-x-auto`}>
          <table className="w-full min-w-[48rem] border-collapse text-left">
            <caption className="sr-only">Illustrative runtime dependency inventory</caption>
            <thead>
              <tr className="border-b border-white/8">
                {["Name", "Kind", "State", "Calls", "Success", "Median latency", "Purpose"].map(
                  (label) => (
                    <th
                      key={label}
                      scope="col"
                      className="px-5 py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]"
                    >
                      {label}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {observability.tools.map((tool) => (
                <tr key={tool.id} className="not-last:border-b not-last:border-white/8">
                  <th scope="row" className="px-5 py-3.5 text-[14px] font-semibold text-[#F8FAFC]">
                    {tool.name}
                  </th>
                  <td className="px-5 py-3.5 text-[13px] text-[#94A3B8]">{tool.kind}</td>
                  <td className="px-5 py-3.5">
                    <StateBadge state={tool.state} />
                  </td>
                  <td className="px-5 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.calls}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.successRate}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.medianLatency}
                  </td>
                  <td className="px-5 py-3.5 text-[13px] text-[#94A3B8]">{tool.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
