import { ArrowLeft, ShieldCheck, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryLineChart } from "@/components/product/story-charts";
import { DemoDataNotice, PageHeader, Section, StateBadge } from "@/components/product/workspace-ui";
import { getAlternativeSession } from "@/features/story/story-data";

function DeltaBadge({ delta }: { delta: string }) {
  const isPositive = delta.startsWith("+");
  const isNeutral = delta === "—" || delta === "$0.00";
  return (
    <span
      className="delta-badge"
      data-sign={isNeutral ? "neutral" : isPositive ? "positive" : "negative"}
      aria-label={`${isPositive ? "outperformed" : "underperformed"} active by ${delta}`}
    >
      {isNeutral ? null : isPositive ? (
        <TrendingUp aria-hidden="true" className="delta-badge-icon" />
      ) : (
        <TrendingDown aria-hidden="true" className="delta-badge-icon" />
      )}
      {delta}
    </span>
  );
}

export default async function AlternativeDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = getAlternativeSession(sessionId);
  if (!session) notFound();

  const shadowBranches = session.branches.filter((b) => b.id !== "actual");

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

      {/* Outcome comparison header */}
      <div className="alt-outcome-grid">
        <div className="alt-outcome-actual prism-glass-card">
          <span className="alt-outcome-label">Active Portfolio (Paper)</span>
          <span className="alt-outcome-pnl" aria-label={`Active outcome: ${session.actualPnl}`}>
            {session.actualPnl}
          </span>
          <span className="alt-outcome-sub">Governed paper execution · recorded outcome</span>
        </div>
        {shadowBranches.map((branch) => (
          <div key={branch.id} className="alt-outcome-shadow prism-glass-card">
            <span className="alt-outcome-label">{branch.label}</span>
            <span className="alt-outcome-pnl alt-outcome-pnl--shadow">{branch.pnl}</span>
            <div className="alt-outcome-delta-row">
              <span className="alt-outcome-sub">vs Active:</span>
              <DeltaBadge delta={branch.deltaVsActual} />
            </div>
          </div>
        ))}
      </div>

      <Section
        id="branch-path"
        title="Trajectory Comparison vs. Active Portfolio"
        description="Each line shows the cumulative P&L of one shadow branch relative to the same timeline. The teal Active Portfolio line is the reference you are comparing against."
      >
        <StoryLineChart
          title="Cumulative Decision Trajectories"
          description="Interactive trajectory view. Toggle shadow branches on or off to isolate any comparison."
          summary={
            session.bestBranch === "Active Portfolio (Paper)"
              ? `Active Portfolio finished ${session.bestDelta} ahead of all shadow alternatives`
              : `${session.bestBranch} finished ${session.bestDelta} relative to active path`
          }
          data={session.path}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Active Portfolio (Paper)", color: "#547D83" },
            {
              key: "alternative",
              label:
                session.alternativeLabel ??
                (session.bestBranch === "Active Portfolio (Paper)"
                  ? "Shadow: Unhedged Alternative"
                  : session.bestBranch),
              color: "#818CF8",
              dashed: true,
            },
            { key: "benchmark", label: "Shadow: Cash Baseline", color: "#94A3B8", dashed: true },
          ]}
        />
      </Section>

      <Section
        id="branch-matrix"
        title="Shadow Branch Results vs. Active Portfolio"
        description="Every branch ran under identical market conditions. The delta column shows directly how each outcome differed from what actually happened."
      >
        <div className="table-wrap prism-glass-card">
          <table>
            <caption>ShadowFund Branch Comparison vs. Active Portfolio</caption>
            <thead>
              <tr>
                <th>Branch</th>
                <th>Variation Tested</th>
                <th>Final P&amp;L</th>
                <th>vs Active (Δ)</th>
                <th>Max Drawdown</th>
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
                  <td className="font-mono tabular-nums">
                    <DeltaBadge delta={branch.deltaVsActual} />
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
        title="Simulation Constraints &amp; Model Boundaries"
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
