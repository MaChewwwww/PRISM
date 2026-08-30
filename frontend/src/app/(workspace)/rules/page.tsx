import {
  CalendarCheck,
  Clock3,
  GaugeCircle,
  Gavel,
  History,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { getGovernance, getWeeklySummary } from "@/features/story/presentation-api";

function formatEastern(value: string): string {
  return `${new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))} ET`;
}

const TH = "px-5 py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]";
const TD = "px-5 py-3.5 text-[14px] text-[#CBD5E1]";
const TD_NUM = "px-5 py-3.5 font-mono text-[14px] tabular-nums text-[#CBD5E1]";

export default async function RulesPage() {
  const [governance, summary] = await Promise.all([getGovernance(), getWeeklySummary()]);

  return (
    <>
      <PageHeader
        eyebrow="Active governance"
        title="Ruleset and AI Profile Boundaries"
        description="Inspect the BA-authorized ruleset and the active Balanced profile. This surface is read-only and creates no execution authority."
      >
        <div className="inline-flex items-center gap-1.5 rounded-full border border-[#00D084]/30 bg-[#00D084]/15 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[#00D084]">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Fails closed
        </div>
      </PageHeader>

      {/* Hackathon window */}
      <section aria-labelledby="hackathon-window" className="mt-6">
        <SectionHeading
          id="hackathon-window"
          icon={Clock3}
          title="Hackathon Operating Window"
          subtitle="Registry values are UTC; the operator view adds Eastern Time. The score is total account equity, not cash balance."
        />
        <div className={`${SECTION_CARD} overflow-x-auto`}>
          <table className="w-full min-w-[44rem] border-collapse text-left">
            <caption className="sr-only">
              Read-only entry, scoring, and force-flatten controls
            </caption>
            <thead>
              <tr className="border-b border-white/8">
                {["Control", "UTC registry value", "Operator view", "Operational meaning"].map(
                  (label) => (
                    <th key={label} scope="col" className={TH}>
                      {label}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {(
                [
                  [
                    "Trading start",
                    governance.hackathonWindow.tradingStartAt,
                    "First eligible entry time.",
                  ],
                  [
                    "New-entry cutoff",
                    governance.hackathonWindow.newEntryCutoffAt,
                    "Manage or exit existing positions only after this point.",
                  ],
                  [
                    "Official scoring point",
                    governance.hackathonWindow.officialScoringAt,
                    "Total account equity used for the official comparison.",
                  ],
                  [
                    "Force-flatten deadline",
                    governance.hackathonWindow.forceFlattenBy,
                    "Close all positions before settlement and scoring.",
                  ],
                  [
                    "Window outer boundary",
                    governance.hackathonWindow.windowOuterBoundaryAt,
                    "Window edge only; it does not extend scoring.",
                  ],
                ] as const
              ).map(([label, value, meaning]) => (
                <tr key={label} className="not-last:border-b not-last:border-white/8">
                  <th scope="row" className="px-5 py-3.5 text-[14px] font-semibold text-[#F8FAFC]">
                    {label}
                  </th>
                  <td className={TD_NUM}>{value}</td>
                  <td className={TD}>{formatEastern(value)}</td>
                  <td className="px-5 py-3.5 text-[13px] text-[#94A3B8]">{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-start gap-3 rounded-xl border border-[#547D83]/30 bg-[#547D83]/10 p-4">
          <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-[#B2D8DC]" aria-hidden="true" />
          <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
            Effective maximum hold: {governance.hackathonWindow.effectiveMaxHoldTradingDays} trading
            days. A Sep-3-expiring contract must not be held into settlement; the 0-DTE block, DTE
            exit, and force-flatten are cumulative controls.
          </p>
        </div>
      </section>

      {/* Weekly summary callout */}
      <Link
        href="/weekly-summary"
        className={`group mt-6 flex items-center gap-3 ${SECTION_CARD} p-4 outline-none transition-all duration-200 hover:border-[#818CF8]/40 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]`}
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <strong className="block text-[14px] font-semibold text-[#F8FAFC]">
            {summary.suggestions.length} bounded profile recommendation
            {summary.suggestions.length === 1 ? "" : "s"}
          </strong>
          <span className="text-[13px] text-[#94A3B8]">
            Post-Analysis recommendations require deterministic validation and manual review.
          </span>
        </div>
        <span
          aria-hidden="true"
          className="font-mono text-[#64748B] transition-transform group-hover:translate-x-0.5"
        >
          &rarr;
        </span>
      </Link>

      {/* Decision vocabulary */}
      <section aria-labelledby="rule-semantics" className="mt-6">
        <SectionHeading
          id="rule-semantics"
          icon={GaugeCircle}
          title="Decision Vocabulary"
          subtitle="Individual rule outcomes and aggregate authorization outcomes are intentionally separate."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {(["PASS", "MODIFY", "FAIL"] as const).map((state) => (
            <div key={state} className={`${SECTION_CARD} p-5`}>
              <StateBadge state={state} />
              <h3 className="mt-3 text-[15px] font-semibold text-[#F8FAFC]">{state}</h3>
              <p className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
                {governance.decisionSemantics[state]}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {(["APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"] as const).map((state) => (
            <div key={state} className={`${SECTION_CARD} p-5`}>
              <StateBadge state={state} />
              <h3 className="mt-3 text-[15px] font-semibold text-[#F8FAFC]">
                {state.replaceAll("_", " ")}
              </h3>
              <p className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
                {governance.decisionSemantics[state]}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Active profile */}
      <section aria-labelledby="active-profile" className="mt-6">
        <SectionHeading
          id="active-profile"
          icon={Gavel}
          title="Active Balanced Profile"
          subtitle={`Ruleset ${governance.rulesetId}@${governance.rulesetVersion}. Values may vary only inside the approved bounds.`}
        />
        <div className={`${SECTION_CARD} overflow-x-auto`}>
          <table className="w-full min-w-[44rem] border-collapse text-left">
            <caption className="sr-only">
              Read-only AI Profile parameters and deterministic bounds
            </caption>
            <thead>
              <tr className="border-b border-white/8">
                {["Parameter", "Active", "Minimum", "Maximum", "Unit", "Boundary"].map((label) => (
                  <th key={label} scope="col" className={TH}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {governance.profileParameters.map((parameter) => (
                <tr key={parameter.id} className="not-last:border-b not-last:border-white/8">
                  <th scope="row" className="px-5 py-3.5">
                    <span className="block text-[14px] font-semibold text-[#F8FAFC]">
                      {parameter.name}
                    </span>
                    <span className="mt-0.5 block text-[12px] font-normal text-[#64748B]">
                      {parameter.description}
                    </span>
                  </th>
                  <td className={TD_NUM}>{parameter.activeValue}</td>
                  <td className={TD_NUM}>{parameter.minimum}</td>
                  <td className={TD_NUM}>{parameter.maximum}</td>
                  <td className={TD}>{parameter.unit}</td>
                  <td className="px-5 py-3.5">
                    <StateBadge state="enforced" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Ruleset history */}
      <section aria-labelledby="version-history" className="mt-6">
        <SectionHeading
          id="version-history"
          icon={History}
          title="Ruleset History"
          subtitle="Activated rulesets are immutable and remain identifiable in every decision trace."
        />
        <ul className={`${SECTION_CARD} divide-y divide-white/8`}>
          {governance.versions.map((version) => (
            <li key={version.version} className="flex items-center justify-between gap-4 px-5 py-4">
              <div>
                <strong className="font-mono text-[14px] font-semibold text-[#F8FAFC]">
                  {version.version}
                </strong>
                <span className="mt-0.5 block text-[13px] text-[#94A3B8]">{version.summary}</span>
              </div>
              <StateBadge state={version.state} />
            </li>
          ))}
        </ul>
      </section>

      {/* Deterministic controls */}
      <section aria-labelledby="hard-controls" className="mt-6">
        <SectionHeading
          id="hard-controls"
          icon={LockKeyhole}
          title="Deterministic Controls"
          subtitle="AI Profiles and Post-Analysis cannot weaken these BA-authorized or platform-level boundaries."
        />
        <ul className="space-y-3">
          {governance.hardRules.map((rule) => (
            <li key={rule.ruleId} className={`${SECTION_CARD} flex items-start gap-4 p-5`}>
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-white/8 bg-white/5 font-mono text-[11px] font-bold text-[#B2D8DC]">
                {rule.priority}
              </span>
              <LockKeyhole className="mt-1 h-4 w-4 shrink-0 text-[#547D83]" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <h3 className="text-[15px] font-semibold text-[#F8FAFC]">{rule.name}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-[#94A3B8]">
                  {rule.explanation}
                </p>
                <code className="mt-2 inline-block rounded border border-white/8 bg-white/5 px-2 py-0.5 font-mono text-[12px] text-[#CBD5E1]">
                  {rule.activeValue}
                </code>
              </div>
              <StateBadge state="enforced" />
            </li>
          ))}
        </ul>
        <div className="mt-3 flex items-start gap-3 rounded-xl border border-[#547D83]/30 bg-[#547D83]/10 p-4">
          <CalendarCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#B2D8DC]" aria-hidden="true" />
          <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
            Profile recommendations are reviewed in{" "}
            <Link
              href="/weekly-summary"
              className="text-[#B2D8DC] underline-offset-2 hover:underline"
            >
              Weekly Summary
            </Link>
            . Automatic profile switching remains deferred.
          </p>
        </div>
      </section>
    </>
  );
}
