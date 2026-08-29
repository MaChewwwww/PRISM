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
        eyebrow={`${session.symbol} · ShadowFund session`}
        title={session.title}
        description={session.summary}
      >
        <StateBadge state="simulated" />
      </PageHeader>
      <DemoDataNotice />
      <MetricStrip
        metrics={[
          { label: "Paper result", value: session.actualPnl, detail: "Illustrative" },
          { label: "Best branch", value: session.bestBranch, detail: "Simulated" },
          { label: "Comparison delta", value: session.bestDelta, detail: "Review signal only" },
          { label: "Data coverage", value: session.coverage, detail: "Fixture observations" },
        ]}
      />
      <Section
        id="branch-path"
        title="How the branches separated"
        description="The solid path is paper-shaped; the dashed path is simulated and cannot execute."
      >
        <StoryLineChart
          title="Cumulative branch result"
          description="Synthetic P&amp;L observations across one fixed evaluation window."
          summary={`${session.bestBranch} finished ${session.bestDelta} ahead`}
          data={session.path}
          valuePrefix="$"
          series={[
            { key: "actual", label: "Illustrative paper", color: "var(--primary)" },
            {
              key: "alternative",
              label: session.bestBranch,
              color: "var(--alternative)",
              dashed: true,
            },
            { key: "benchmark", label: "No action", color: "var(--benchmark)", dashed: true },
          ]}
        />
      </Section>
      <Section
        id="branch-matrix"
        title="Branch comparison"
        description="One controlled variation per row keeps the lesson interpretable."
      >
        <div className="table-wrap">
          <table>
            <caption>ShadowFund branch metrics</caption>
            <thead>
              <tr>
                <th>Branch</th>
                <th>Variation</th>
                <th>P&amp;L</th>
                <th>Drawdown</th>
                <th>Coverage</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {session.branches.map((branch) => (
                <tr key={branch.id}>
                  <th scope="row">{branch.label}</th>
                  <td>{branch.variation}</td>
                  <td>{branch.pnl}</td>
                  <td>{branch.drawdown}</td>
                  <td>{branch.coverage}</td>
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
        title="Simulation limitations"
        description="Missing or optimistic assumptions stay visible beside the result."
      >
        <ul className="limitation-list">
          {session.limitations.map((limitation) => (
            <li key={limitation}>
              <ShieldCheck aria-hidden="true" />
              <span>{limitation}</span>
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
