import Link from "next/link";
import { CalendarCheck, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";

import { DemoDataNotice, PageHeader, Section, StateBadge } from "@/components/product/workspace-ui";
import { RuleStudio } from "@/features/rules/rule-studio";
import {
  configurableRules,
  hardRules,
  ruleVersions,
  getWeeklySummary,
} from "@/features/story/story-data";

export default function RulesPage() {
  const summary = getWeeklySummary();
  const suggestionCount = summary.suggestions.length;

  return (
    <>
      <PageHeader
        eyebrow="Active governance"
        title="Business Rules Configuration"
        description="Set the thresholds that govern every trade decision. Changes create a draft — no draft can execute until it passes deterministic validation and receives an explicit approval."
      >
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" /> Fails closed
        </div>
      </PageHeader>
      <DemoDataNotice />

      {/* AI callout */}
      <Link
        href="/weekly-summary"
        className="rules-callout"
        aria-label="View weekly AI calibration suggestions"
      >
        <span className="rules-callout-icon">
          <Sparkles aria-hidden="true" />
        </span>
        <div>
          <strong>
            {suggestionCount} AI calibration suggestion{suggestionCount !== 1 ? "s" : ""} from this
            week
          </strong>
          <span>
            Post-analysis identified potential improvements. View Weekly Summary to accept or
            dismiss.
          </span>
        </div>
        <span className="rules-callout-arrow" aria-hidden="true">
          →
        </span>
      </Link>

      {/* Rule semantics legend */}
      <Section
        id="rule-semantics"
        title="How rule decisions work"
        description="A modification creates a new candidate — it is not permission to mutate an authorized payload."
      >
        <div className="semantics-row">
          <div>
            <StateBadge state="PASS" />
            <h3>Continue unchanged</h3>
            <p>Every required configured check passed for the exact payload.</p>
          </div>
          <div>
            <StateBadge state="MODIFY" />
            <h3>Create a new candidate</h3>
            <p>
              The proposed payload is not executable and must be accepted, digested, and evaluated
              again.
            </p>
          </div>
          <div>
            <StateBadge state="FAIL" />
            <h3>Stop safely</h3>
            <p>A required condition failed or required configuration is missing.</p>
          </div>
        </div>
      </Section>

      {/* Configurable rules — primary action */}
      <RuleStudio rules={configurableRules} />

      {/* Version history */}
      <Section
        id="version-history"
        title="Version and approval history"
        description="Activated rulesets are immutable; this prototype only demonstrates the review structure."
      >
        <ol className="version-list">
          {ruleVersions.map((version) => (
            <li key={version.version}>
              <div>
                <strong>{version.version}</strong>
                <span>{version.summary}</span>
              </div>
              <time dateTime={version.changedAt}>{version.changedAt.slice(0, 10)}</time>
              <StateBadge state={version.state} />
            </li>
          ))}
        </ol>
      </Section>

      {/* Hard controls — collapsed reference */}
      <Section
        id="hard-controls"
        title="Platform constraints"
        description="These rules protect the authority boundary and cannot be weakened by any user, profile, agent, or draft."
      >
        <details className="hard-controls-details">
          <summary>
            <LockKeyhole aria-hidden="true" />
            Show {hardRules.length} immutable platform controls
          </summary>
          <ol className="hard-rule-list" style={{ marginTop: "1rem" }}>
            {hardRules.map((rule, index) => (
              <li key={rule.name}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <LockKeyhole aria-hidden="true" />
                <div>
                  <h3>{rule.name}</h3>
                  <p>{rule.explanation}</p>
                </div>
                <StateBadge state="enforced" />
              </li>
            ))}
          </ol>
        </details>
        <div className="inspector-note" style={{ marginTop: "0.75rem" }}>
          <CalendarCheck aria-hidden="true" />
          <p>
            AI-suggested rule calibrations live in{" "}
            <Link href="/weekly-summary" className="detail-link">
              Weekly Summary
            </Link>
            . They require explicit manual approval before staging.
          </p>
        </div>
      </Section>
    </>
  );
}
