import { ArrowLeft, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryLineChart } from "@/components/product/story-charts";
import {
  DemoDataNotice,
  MetricStrip,
  PageHeader,
  Section,
  StateBadge,
} from "@/components/product/workspace-ui";
import { getAlternativeSession } from "@/features/story/story-data";

export default async function AlternativeDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = getAlternativeSession(sessionId);
  if (!session) notFound();
  return (
    <>
      <Link className="back-link" href="/alternatives">
        <ArrowLeft aria-hidden="true" /> All alternatives
      </Link>
      <PageHeader
        eyebrow={`${session.symbol} · ShadowFund Multiverse Session`}
        title={session.title}
        description={session.summary}
      >
        <StateBadge state="simulated" />
      </PageHeader>
      <DemoDataNotice />
      <MetricStrip
        metrics={[
          { label: "Active Outcome", value: session.actualPnl, detail: "Paper execution P&L" },
          { label: "Best Shadow Path", value: session.bestBranch, detail: "Simulated alternative" },
          {
            label: "Counterfactual Delta",
            value: session.bestDelta,
            detail: "Active vs. Shadow delta",
          },
          {
            label: "Data Coverage",
            value: session.coverage,
            detail: "Fixture observation density",
          },
        ]}
      />
      <Section
        id="branch-path"
        title="How the Alternative Trajectories Diverged"
        description="Solid mineral teal is our Active Portfolio; dashed amethyst is the leading Shadow counterfactual; dashed slate is Cash Baseline."
      >
        <StoryLineChart
          title="Cumulative Decision Trajectories"
          description="P&amp;L progression across identical market conditions and timestamps."
          summary={`${session.bestBranch} finished ${session.bestDelta} relative to active path`}
          data={session.path}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Active Portfolio (Paper)", color: "#547D83" },
            {
              key: "alternative",
              label: session.bestBranch,
              color: "#818CF8",
              dashed: true,
            },
            { key: "benchmark", label: "Shadow: Cash Baseline", color: "#64748B", dashed: true },
          ]}
        />
      </Section>
      <Section
        id="branch-matrix"
        title="Shadow Portfolio Decision Matrix"
        description="Each branch isolates one controlled parameter to attribute alpha and risk."
      >
        <div className="table-wrap prism-glass-card">
          <table>
            <caption>ShadowFund Branch Metrics &amp; Comparison</caption>
            <thead>
              <tr>
                <th>Branch</th>
                <th>Variation Tested</th>
                <th>P&amp;L</th>
                <th>Drawdown</th>
                <th>Coverage</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {session.branches.map((branch) => (
                <tr
                  key={branch.id}
                  className={branch.id === "actual" ? "bg-[#547D83]/10 font-semibold" : ""}
                >
                  <th scope="row">{branch.label}</th>
                  <td>{branch.variation}</td>
                  <td className="font-mono tabular-nums font-semibold text-[#00D084]">
                    {branch.pnl}
                  </td>
                  <td className="font-mono tabular-nums text-[#FF6B6B]">{branch.drawdown}</td>
                  <td className="font-mono tabular-nums">{branch.coverage}</td>
                  <td>
                    <StateBadge state={branch.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <Section
        id="limitations"
        title="Simulation Constraints & Model Boundaries"
        description="Explicit assumptions and limitations preserved for audit integrity."
      >
        <ul className="limitation-list space-y-2">
          {session.limitations.map((limitation) => (
            <li key={limitation} className="prism-glass-card p-3 flex items-center gap-3">
              <ShieldCheck aria-hidden="true" className="text-[#818CF8]" />
              <span className="text-sm text-slate-200">{limitation}</span>
            </li>
          ))}
        </ul>
        <div className="inspector-note">
          <ShieldCheck aria-hidden="true" />
          <p>
            These branches can supply evidence for review. They cannot submit, amend, cancel, or
            authorize an order.
          </p>
        </div>
      </Section>
    </>
  );
}
