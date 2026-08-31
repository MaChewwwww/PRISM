import { CheckCircle2, ChevronLeft, ListChecks, Network } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
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

const METRIC_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl transition-all duration-200 hover:border-[#547D83]/40 hover:shadow-[0_0_24px_rgba(84,125,131,0.35)]";

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

  const metrics = [
    { label: "Cadence", value: agent.cadence, detail: "Illustrative trigger" },
    { label: "Runs", value: String(runs.length), detail: "In selected period" },
    { label: "Visible tokens", value: formatTokens(tokens), detail: "No hidden reasoning" },
    {
      label: "Average duration",
      value: runs.length ? `${averageDuration} ms` : "—",
      detail: "Fixture latency",
    },
  ];

  return (
    <div className="space-y-8">
      <Link
        href="/agents"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#64748B] outline-none transition-colors hover:text-[#CBD5E1] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
      >
        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
        All agents and tools
      </Link>

      <PageHeader eyebrow="Agent detail" title={agent.name} description={agent.role}>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <RangePresets range={range} />
          <TryAgentButton
            agentId={mapAgentIdToAction(agentId)}
            label={`Try ${agent.name.split(" ")[0]}`}
          />
        </div>
      </PageHeader>

      {/* Metric cards */}
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className={METRIC_CARD}>
            <dt className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
              {metric.label}
            </dt>
            <dd className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#F8FAFC]">
              {metric.value}
            </dd>
            <p className="mt-1 text-[11px] text-[#64748B]">{metric.detail}</p>
          </div>
        ))}
      </dl>

      {/* Responsibility + model context */}
      <div
        className={`${SECTION_CARD} grid grid-cols-1 gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]`}
      >
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#64748B]">
            Responsibility
          </p>
          <h2 className="mt-2 text-[16px] leading-relaxed font-medium text-[#F8FAFC]">
            {agent.description}
          </h2>
        </div>
        <dl className="grid grid-cols-2 gap-4 border-t border-white/8 pt-4 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6">
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
              Model
            </dt>
            <dd className="mt-1 font-mono text-[13px] text-[#CBD5E1]">{agent.model}</dd>
          </div>
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
              Prompt version
            </dt>
            <dd className="mt-1 font-mono text-[13px] text-[#CBD5E1]">{agent.promptVersion}</dd>
          </div>
        </dl>
      </div>

      {/* Bounded dependencies */}
      <section aria-labelledby="dependencies">
        <SectionHeading
          id="dependencies"
          icon={Network}
          title="Bounded Dependencies"
          subtitle="This agent sees only the context required for its responsibility."
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <ul className="flex flex-wrap gap-2">
            {agent.dependencies.map((dependency) => (
              <li
                key={dependency}
                className="inline-flex items-center gap-1.5 rounded-md border border-white/8 bg-white/5 px-2.5 py-1.5 text-[13px] text-[#CBD5E1]"
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-[#00D084]" aria-hidden="true" />
                {dependency}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Run history */}
      <section aria-labelledby="run-history">
        <SectionHeading
          id="run-history"
          icon={ListChecks}
          title="Run History"
          subtitle="Every result has an explicit trigger, terminal state, latency, token count, and visible summary."
        />
        {runs.length === 0 ? (
          <div className={`${SECTION_CARD} p-6`}>
            <p className="text-[13px] text-[#94A3B8]">
              No illustrative runs fall inside this date range.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {runs.map((run) => (
              <li key={run.id} className={`${SECTION_CARD} p-5 sm:p-6`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="text-[15px] font-semibold text-[#F8FAFC]">{run.trigger}</span>
                    <StateBadge state={run.status} />
                  </div>
                  <time
                    dateTime={run.occurredAt}
                    className="font-mono text-[12px] tabular-nums text-[#64748B]"
                  >
                    {formatDateTime(run.occurredAt)}
                  </time>
                </div>
                <p className="mt-2 text-[14px] leading-relaxed text-[#CBD5E1]">{run.summary}</p>
                <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-white/8 pt-4 sm:grid-cols-4">
                  {[
                    { dt: "Duration", dd: `${run.durationMs} ms` },
                    { dt: "Input", dd: formatTokens(run.inputTokens) },
                    { dt: "Output", dd: formatTokens(run.outputTokens) },
                    { dt: "Cached", dd: formatTokens(run.cachedTokens) },
                  ].map((row) => (
                    <div key={row.dt}>
                      <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                        {row.dt}
                      </dt>
                      <dd className="mt-1 font-mono text-[14px] tabular-nums text-[#CBD5E1]">
                        {row.dd}
                      </dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
