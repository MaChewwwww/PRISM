import {
  ChevronLeft,
  GitCompareArrows,
  ShieldCheck,
  Table2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryBranchChart } from "@/features/story/story-branch-chart";
import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { getAlternativeSession } from "@/features/story/presentation-api";

function deltaTone(delta: string): { color: string; sign: "positive" | "negative" | "neutral" } {
  if (delta === "—" || delta === "$0.00") return { color: "#94A3B8", sign: "neutral" };
  if (delta.startsWith("+")) return { color: "#00D084", sign: "positive" };
  return { color: "#FF6B6B", sign: "negative" };
}

function DeltaBadge({ delta }: { delta: string }) {
  const { color, sign } = deltaTone(delta);
  return (
    <span
      className="inline-flex items-center gap-1 font-mono text-[13px] font-semibold tabular-nums"
      style={{ color }}
      aria-label={`${sign === "positive" ? "outperformed" : sign === "negative" ? "underperformed" : "matched"} the chosen path by ${delta}`}
    >
      {sign === "positive" ? (
        <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
      ) : sign === "negative" ? (
        <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
      ) : null}
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
  const session = await getAlternativeSession(sessionId);
  if (!session) notFound();

  const shadowBranches = session.branches.filter((branch) => !branch.chosenPath);
  const activePathLabel = "Chosen Path";

  return (
    <div className="space-y-8">
      <Link
        href="/alternatives"
        className="inline-flex items-center gap-1.5 text-[12px] text-[#64748B] outline-none transition-colors hover:text-[#CBD5E1] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
      >
        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
        All alternatives
      </Link>

      <PageHeader
        eyebrow={`${session.symbol} · ShadowFund Multiverse Session`}
        title={session.title}
        description={session.summary}
      >
        <StateBadge state="simulated" />
      </PageHeader>

      {/* Outcome comparison cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className={`${SECTION_CARD} border-l-2 border-l-[#547D83] p-5`}>
          <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
            {activePathLabel}
          </span>
          <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#00D084]">
            {session.chosenPathPnl}
          </p>
          <p className="mt-1 text-[11px] text-[#64748B]">Recorded or virtual-only baseline</p>
        </div>
        {shadowBranches.map((branch) => (
          <div key={branch.id} className={`${SECTION_CARD} p-5`}>
            <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#64748B]">
              {branch.label}
            </span>
            <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-[#818CF8]">
              {branch.pnl}
            </p>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-[#64748B]">
              <span>vs chosen:</span>
              <DeltaBadge delta={branch.deltaVsChosen} />
            </div>
          </div>
        ))}
      </div>

      {/* Trajectory chart */}
      <section aria-labelledby="branch-path">
        <SectionHeading
          id="branch-path"
          icon={GitCompareArrows}
          title="Trajectory Comparison vs. Chosen Path"
          subtitle="Each line is a persisted non-executable branch on the same market-observation timeline."
          accent="#818CF8"
        />
        <StoryBranchChart data={session.path} />
      </section>

      {/* Branch matrix */}
      <section aria-labelledby="branch-matrix">
        <SectionHeading
          id="branch-matrix"
          icon={Table2}
          title="Shadow Branch Results vs. Chosen Path"
          subtitle="Every branch uses the same observations. Delta shows how each virtual path differs from the chosen path."
          accent="#818CF8"
        />
        <div className={`${SECTION_CARD} overflow-x-auto`}>
          <table className="w-full min-w-[52rem] border-collapse text-left">
            <caption className="sr-only">
              ShadowFund branch comparison versus the chosen path
            </caption>
            <thead>
              <tr className="border-b border-white/8">
                {[
                  "Branch",
                  "Variation Tested",
                  "Final P&L",
                  "vs Chosen (Δ)",
                  "Max Drawdown",
                  "Coverage",
                  "State",
                ].map((label) => (
                  <th
                    key={label}
                    scope="col"
                    className="px-5 py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {session.branches.map((branch) => {
                const isActive = branch.chosenPath;
                return (
                  <tr
                    key={branch.id}
                    className="not-last:border-b not-last:border-white/8"
                    style={isActive ? { background: "rgba(84,125,131,0.1)" } : undefined}
                  >
                    <th
                      scope="row"
                      className="px-5 py-3.5 text-[14px] font-semibold text-[#F8FAFC]"
                    >
                      {branch.label === "Illustrative governed path"
                        ? activePathLabel
                        : branch.label}
                    </th>
                    <td className="px-5 py-3.5 text-[13px] text-[#94A3B8]">{branch.variation}</td>
                    <td className="px-5 py-3.5 font-mono text-[14px] font-semibold tabular-nums text-[#00D084]">
                      {branch.pnl}
                    </td>
                    <td className="px-5 py-3.5">
                      <DeltaBadge delta={branch.deltaVsChosen} />
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[14px] tabular-nums text-[#FF6B6B]">
                      {branch.drawdown}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[14px] tabular-nums text-[#CBD5E1]">
                      {branch.coverage}
                    </td>
                    <td className="px-5 py-3.5">
                      <StateBadge state={branch.status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Limitations */}
      <section aria-labelledby="limitations">
        <SectionHeading
          id="limitations"
          icon={ShieldCheck}
          title="Simulation Constraints & Model Boundaries"
          subtitle="Explicit assumptions and limitations preserved for audit integrity."
          accent="#818CF8"
        />
        <ul className="space-y-3">
          {session.limitations.map((limitation) => (
            <li key={limitation} className={`${SECTION_CARD} flex items-start gap-3 p-4`}>
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#818CF8]" aria-hidden="true" />
              <span className="text-[14px] leading-relaxed text-[#CBD5E1]">{limitation}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex items-start gap-3 rounded-xl border border-[#818CF8]/30 bg-[#818CF8]/10 p-4">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#C7D2FE]" aria-hidden="true" />
          <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
            These branches can supply evidence for review. They cannot submit, amend, cancel, or
            authorize an order.
          </p>
        </div>
      </section>
    </div>
  );
}
