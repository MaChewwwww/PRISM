import { CalendarCheck, Clock3, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import {
  DemoDataNotice,
  PageHeader,
  Section,
  StateBadge,
} from "@/components/workspace/workspace-ui";
import { getGovernance, getWeeklySummary } from "@/features/story/presentation-api";

function formatEastern(value: string): string {
  return `${new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))} ET`;
}

export default async function RulesPage() {
  const [governance, summary] = await Promise.all([getGovernance(), getWeeklySummary()]);

  return (
    <>
      <PageHeader
        eyebrow="Active governance"
        title="Ruleset and AI Profile Boundaries"
        description="Inspect the BA-authorized ruleset and the active Balanced profile. This surface is read-only and creates no execution authority."
      >
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" /> Fails closed
        </div>
      </PageHeader>
      <DemoDataNotice />

      <Section
        id="hackathon-window"
        title="Hackathon operating window"
        description="The BA-authorized registry values are UTC; the operator view includes Eastern Time labels. The score is total account equity, not cash balance."
      >
        <div className="table-wrap prism-glass-card">
          <table>
            <caption>Read-only entry, scoring, and force-flatten controls</caption>
            <thead>
              <tr>
                <th>Control</th>
                <th>UTC registry value</th>
                <th>Operator view</th>
                <th>Operational meaning</th>
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
                <tr key={label}>
                  <th scope="row">{label}</th>
                  <td className="font-mono tabular-nums">{value}</td>
                  <td>{formatEastern(value)}</td>
                  <td>{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="inspector-note mt-3">
          <Clock3 aria-hidden="true" />
          <p>
            Effective maximum hold: {governance.hackathonWindow.effectiveMaxHoldTradingDays} trading
            days. A Sep-3-expiring contract must not be held into settlement; the 0-DTE block, DTE
            exit, and force-flatten are cumulative controls.
          </p>
        </div>
      </Section>

      <Link href="/weekly-summary" className="rules-callout">
        <span className="rules-callout-icon">
          <Sparkles aria-hidden="true" />
        </span>
        <div>
          <strong>
            {summary.suggestions.length} bounded profile recommendation
            {summary.suggestions.length === 1 ? "" : "s"}
          </strong>
          <span>
            Post-Analysis recommendations require deterministic validation and manual review.
          </span>
        </div>
        <span className="rules-callout-arrow" aria-hidden="true">
          -&gt;
        </span>
      </Link>

      <Section
        id="rule-semantics"
        title="Decision vocabulary"
        description="Individual rule outcomes and aggregate authorization outcomes are intentionally separate."
      >
        <div className="semantics-row">
          {(["PASS", "MODIFY", "FAIL"] as const).map((state) => (
            <div key={state}>
              <StateBadge state={state} />
              <h3>{state}</h3>
              <p>{governance.decisionSemantics[state]}</p>
            </div>
          ))}
        </div>
        <div className="semantics-row mt-3">
          {(["APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"] as const).map((state) => (
            <div key={state}>
              <StateBadge state={state} />
              <h3>{state.replaceAll("_", " ")}</h3>
              <p>{governance.decisionSemantics[state]}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="active-profile"
        title="Active Balanced Profile"
        description={`Ruleset ${governance.rulesetId}@${governance.rulesetVersion}. Values may vary only inside the approved bounds.`}
      >
        <div className="table-wrap prism-glass-card">
          <table>
            <caption>Read-only AI Profile parameters and deterministic bounds</caption>
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Active</th>
                <th>Minimum</th>
                <th>Maximum</th>
                <th>Unit</th>
                <th>Boundary</th>
              </tr>
            </thead>
            <tbody>
              {governance.profileParameters.map((parameter) => (
                <tr key={parameter.id}>
                  <th scope="row">
                    {parameter.name}
                    <span className="block text-xs font-normal text-slate-400">
                      {parameter.description}
                    </span>
                  </th>
                  <td className="font-mono tabular-nums">{parameter.activeValue}</td>
                  <td className="font-mono tabular-nums">{parameter.minimum}</td>
                  <td className="font-mono tabular-nums">{parameter.maximum}</td>
                  <td>{parameter.unit}</td>
                  <td>
                    <StateBadge state="enforced" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        id="version-history"
        title="Ruleset history"
        description="Activated rulesets are immutable and remain identifiable in every decision trace."
      >
        <ol className="version-list">
          {governance.versions.map((version) => (
            <li key={version.version}>
              <div>
                <strong>{version.version}</strong>
                <span>{version.summary}</span>
              </div>
              <StateBadge state={version.state} />
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="hard-controls"
        title="Deterministic controls"
        description="AI Profiles and Post-Analysis cannot weaken these BA-authorized or platform-level boundaries."
      >
        <ol className="hard-rule-list">
          {governance.hardRules.map((rule) => (
            <li key={rule.ruleId}>
              <span>{rule.priority}</span>
              <LockKeyhole aria-hidden="true" />
              <div>
                <h3>{rule.name}</h3>
                <p>{rule.explanation}</p>
                <code>{rule.activeValue}</code>
              </div>
              <StateBadge state="enforced" />
            </li>
          ))}
        </ol>
        <div className="inspector-note mt-3">
          <CalendarCheck aria-hidden="true" />
          <p>
            Profile recommendations are reviewed in{" "}
            <Link href="/weekly-summary">Weekly Summary</Link>. Automatic profile switching remains
            deferred.
          </p>
        </div>
      </Section>
    </>
  );
}
