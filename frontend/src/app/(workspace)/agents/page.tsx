import {
  ArrowRight,
  BarChart3,
  Bot,
  GitBranch,
  GitCompareArrows,
  Gavel,
  type LucideIcon,
  Send,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";
import Link from "next/link";

import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { formatTokens } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { loadAgentObservability } from "@/features/story/presentation-api";
import { TokenUsageChart } from "@/features/agents/token-usage-chart";
import { TryAgentButton } from "@/features/agents/agent-playground-modal";

const METRIC_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]";

/** Icon per authority-pipeline component kind. */
const COMPONENT_ICON: Record<string, LucideIcon> = {
  risk_ai: ShieldAlert,
  deterministic: Gavel,
  paper_execution: Send,
  shadowfund: GitCompareArrows,
  post_analysis: Sparkles,
};

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
  const tokenSeries = observability.agents.map((agent) => ({
    name: agent.name,
    role: agent.role,
    runs: agent.runs.map((run) => ({
      occurredAt: run.occurredAt,
      inputTokens: run.inputTokens,
      outputTokens: run.outputTokens,
      cachedTokens: run.cachedTokens,
    })),
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
      />

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
        <div className="mb-4">
          <h2
            id="agent-usage"
            className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
          >
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/40 bg-[#547D83]/20 text-[#B2D8DC]">
              <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
            Token Usage by Agent
          </h2>
          <p className="mt-1 text-[12px] text-[#64748B]">
            Which roles consumed the illustrative model budget in this period? Adjust the range to
            refilter just this chart.
          </p>
        </div>
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <TokenUsageChart agents={tokenSeries} anchor={range.to} />
        </div>
      </section>

      {/* Agent registry */}
      <section aria-labelledby="agent-registry" className="mt-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2
              id="agent-registry"
              className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/40 bg-[#547D83]/20 text-[#B2D8DC]">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              Specialists, Risk, and Post-Analysis
            </h2>
            <p className="mt-1 text-[12px] text-[#64748B]">
              Each AI role has bounded research, proposal, risk, or recommendation authority.
            </p>
          </div>
          <TryAgentButton label="Try Agent" />
        </div>
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {observability.agents.map((agent) => {
            const tokens = agent.runs.reduce(
              (total, run) => total + run.inputTokens + run.outputTokens + run.cachedTokens,
              0,
            );
            return (
              <li key={agent.id} className="flex">
                <Link
                  href={`/agents/${agent.id}`}
                  className={`group flex w-full flex-col gap-4 ${SECTION_CARD} p-5 outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]`}
                >
                  {/* Identity: avatar with status dot + name + role */}
                  <div className="flex items-start gap-3">
                    <span aria-hidden="true" className="relative shrink-0">
                      <span className="grid h-10 w-10 place-items-center rounded-lg border border-[#547D83]/40 bg-[#547D83]/15 text-[#B2D8DC]">
                        <Bot className="h-5 w-5" />
                      </span>
                      <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#0B0F14] bg-[#00D084]" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-[16px] font-semibold text-[#F8FAFC] transition-colors group-hover:text-[#B2D8DC]">
                        {agent.name}
                      </h3>
                      <p className="mt-0.5 text-[12px] capitalize text-[#94A3B8]">
                        {agent.authority} agent
                      </p>
                    </div>
                  </div>

                  {/* Role description */}
                  <p className="text-[13px] leading-relaxed text-[#94A3B8]">{agent.role}</p>

                  {/* Stats: runs + tokens */}
                  <dl className="mt-auto space-y-2 border-t border-white/8 pt-3">
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-[12px] text-[#64748B]">Runs</dt>
                      <dd className="font-mono text-[13px] font-semibold tabular-nums text-[#CBD5E1]">
                        {agent.runs.length}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-[12px] text-[#64748B]">Tokens</dt>
                      <dd className="font-mono text-[13px] font-semibold tabular-nums text-[#CBD5E1]">
                        {formatTokens(tokens)}
                      </dd>
                    </div>
                  </dl>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Authority pipeline */}
      <section aria-labelledby="authority-pipeline" className="mt-6">
        <SectionHeading
          id="authority-pipeline"
          icon={GitBranch}
          title="Authority Pipeline"
          subtitle="AI contributions stop before deterministic authorization; execution remains paper-only and disabled by default."
        />
        <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
          {observability.components.map((component, index) => {
            const Icon = COMPONENT_ICON[component.kind] ?? GitBranch;
            return (
              <div key={component.id} className="flex items-stretch gap-3 lg:flex-1">
                <div className={`${SECTION_CARD} flex flex-1 flex-col p-5`}>
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 shrink-0 text-[#547D83]" aria-hidden="true" />
                    <h3 className="text-[15px] font-semibold text-[#F8FAFC]">{component.name}</h3>
                  </div>
                  <p className="mt-3 flex-1 text-[13px] leading-relaxed text-[#94A3B8]">
                    {component.description}
                  </p>
                  <dl className="mt-4 space-y-2 border-t border-white/8 pt-3">
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-[11px] text-[#64748B]">Authority</dt>
                      <dd className="text-right text-[12px] text-[#CBD5E1]">{component.authority}</dd>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-[11px] text-[#64748B]">Kind</dt>
                      <dd className="text-right text-[12px] text-[#CBD5E1]">
                        {component.kind.replaceAll("_", " ")}
                      </dd>
                    </div>
                  </dl>
                </div>
                {index < observability.components.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="hidden shrink-0 items-center self-center text-[#547D83]/50 lg:flex"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </span>
                )}
              </div>
            );
          })}
        </div>
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
          <table className="w-full min-w-[48rem] table-fixed border-collapse text-left">
            <caption className="sr-only">Illustrative runtime dependency inventory</caption>
            <thead>
              <tr className="border-b border-white/8">
                {["Name", "Kind", "State", "Calls", "Success", "Median latency", "Purpose"].map(
                  (label) => (
                    <th
                      key={label}
                      scope="col"
                      className="w-[14.28%] px-4 py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]"
                    >
                      {label}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {observability.tools.map((tool) => (
                <tr key={tool.id} className="not-last:border-b not-last:border-white/8 align-top">
                  <th
                    scope="row"
                    className="w-[14.28%] break-words px-4 py-3.5 text-[14px] font-semibold text-[#F8FAFC]"
                  >
                    {tool.name}
                  </th>
                  <td className="w-[14.28%] break-words px-4 py-3.5 text-[13px] text-[#94A3B8]">
                    {tool.kind}
                  </td>
                  <td className="w-[14.28%] px-4 py-3.5">
                    <StateBadge state={tool.state} />
                  </td>
                  <td className="w-[14.28%] px-4 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.calls}
                  </td>
                  <td className="w-[14.28%] px-4 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.successRate}
                  </td>
                  <td className="w-[14.28%] px-4 py-3.5 font-mono text-[13px] tabular-nums text-[#CBD5E1]">
                    {tool.medianLatency}
                  </td>
                  <td className="w-[14.28%] break-words px-4 py-3.5 text-[13px] text-[#94A3B8]">
                    {tool.purpose}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
