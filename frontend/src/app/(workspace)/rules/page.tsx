import { ArrowDownWideNarrow, GaugeCircle, Gavel, LockKeyhole } from "lucide-react";
import { Suspense } from "react";

import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { getGovernance } from "@/features/story/monitoring-api";
import { ProfileEditor } from "@/features/story/profile-editor";

const TH = "px-5 py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B]";
const TD = "px-5 py-3.5 text-[12px] text-[#CBD5E1]";
const TD_NUM = "px-5 py-3.5 font-mono text-[14px] tabular-nums text-[#CBD5E1]";

/** Order in which final executable size is constrained (BUSINESS_RULES.md / FRG-12). */
const SIZING_CAPS = [
  {
    label: "Profile target allocation",
    detail: "Tier 2 preference — the starting point, not a floor.",
  },
  { label: "Per-trade stop-risk cap", detail: "1.00% normal / 0.75% volatile of current equity." },
  { label: "Ticker / sector / cluster concentration", detail: "5.00% / 10.00% / 7.50% maximums." },
  { label: "Aggregate portfolio-risk cap", detail: "3.00% modeled hard-stop risk maximum." },
  { label: "Regime cap", detail: "VOLATILE caps size at 1.50% and risk at 0.75%." },
  { label: "Liquidity cap", detail: "Bid/ask spread must stay within 10.00% of premium." },
  { label: "Buying-power cap", detail: "At least a 5.00% cash / buying-power reserve remains." },
];

export default async function RulesPage() {
  const governance = await getGovernance();

  return (
    <>
      <PageHeader
        eyebrow="Active governance"
        title="Rules & AI Profile"
        description="See the rules and profile guiding decisions."
      ></PageHeader>

      {/* Ruleset identity cards */}
      <section aria-label="Active ruleset identity" className="mt-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            { label: "Ruleset status", value: governance.rulesetStatus },
            { label: "Active profile", value: governance.activeProfile },
            { label: "Execution mode", value: "Paper-only · disabled" },
          ].map((item) => (
            <div key={item.label} className={`${SECTION_CARD} p-5`}>
              <p className="font-mono text-[10px] uppercase tracking-[0.09em] text-[#64748B]">
                {item.label}
              </p>
              <p className="mt-2 font-mono text-[16px] font-semibold capitalize tabular-nums text-[#F8FAFC] break-words">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Tier 1 — Deterministic controls (locked/governed) */}
      <section aria-labelledby="hard-controls" className="mt-8">
        <SectionHeading
          id="hard-controls"
          icon={LockKeyhole}
          title="Deterministic Controls"
          subtitle="Rules that remain enforced across all AI profiles."
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <ul className="space-y-2">
            {governance.hardRules.map((rule) => (
              <li key={rule.ruleId} className="rounded-xl border border-white/8 bg-white/2 p-3.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[14px] font-semibold text-[#F8FAFC]">{rule.name}</span>
                  <span className="inline-flex shrink-0 items-center gap-1.5">
                    <StateBadge state="enforced" />
                    <LockKeyhole className="h-4 w-4 text-[#547D83]" aria-hidden="true" />
                  </span>
                </div>
                <p className="mt-0.5 text-[12px] leading-relaxed text-[#94A3B8]">
                  {rule.explanation}
                </p>
                <code className="mt-2 inline-block rounded border border-white/8 bg-white/5 px-2 py-0.5 font-mono text-[12px] text-[#CBD5E1]">
                  {rule.activeValue}
                </code>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Active profile (read-only summary) */}
      <section aria-labelledby="active-profile" className="mt-6">
        <SectionHeading
          id="active-profile"
          icon={Gavel}
          title="Active Balanced Profile"
          subtitle={"AI settings within approved limits"}
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
                    <strong className="block text-[14px] font-semibold text-[#F8FAFC]">
                      {parameter.name}
                    </strong>
                    <span className="mt-0.5 block !text-[10px] font-normal text-[#64748B]">
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

      {/* Configure AI profile (Tier 2, operator-configurable) */}
      <section aria-labelledby="configure-profile" className="mt-6">
        <Suspense fallback={null}>
          <ProfileEditor
            profileParameters={governance.profileParameters}
            profiles={governance.profiles}
          />
        </Suspense>
      </section>

      {/* Sizing resolution explainer (compact) — ties Tier 1 to Tier 2 */}
      <section aria-labelledby="sizing-resolution" className="mt-8">
        <SectionHeading
          id="sizing-resolution"
          icon={ArrowDownWideNarrow}
          title="Final Position Size"
          subtitle="See how the final position size is determined."
        />
        <div className={`${SECTION_CARD} p-5 sm:p-6`}>
          <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
            Final allocation is the <span className="font-semibold text-[#F8FAFC]">minimum</span> of
            the profile target and every hard cap below, then rounded down to a whole-contract size.
            A tighter cap always wins.
          </p>
          <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {SIZING_CAPS.map((cap) => (
              <div key={cap.label} className="rounded-xl border border-white/8 bg-white/2 p-3.5">
                <dt className="text-[13px] font-semibold text-[#F8FAFC]">{cap.label}</dt>
                <dd className="mt-0.5 text-[12px] leading-relaxed text-[#94A3B8]">{cap.detail}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Decision vocabulary */}
      <section aria-labelledby="rule-semantics" className="mt-8">
        <SectionHeading
          id="rule-semantics"
          icon={GaugeCircle}
          title="Decision Terms"
          subtitle="Understand individual rule checks and final authorization."
        />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {(
            ["PASS", "MODIFY", "FAIL", "APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"] as const
          ).map((state) => (
            <div key={state} className={`${SECTION_CARD} p-4`}>
              <StateBadge state={state} />
              <h3 className="mt-2.5 text-[13px] font-semibold text-[#F8FAFC]">
                {state.replaceAll("_", " ")}
              </h3>
              <p className="mt-1 text-[12px] leading-relaxed text-[#94A3B8]">
                {governance.decisionSemantics[state]}
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
