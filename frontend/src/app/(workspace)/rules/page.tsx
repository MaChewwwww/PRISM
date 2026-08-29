import { LockKeyhole, ShieldCheck } from "lucide-react";

import { DemoDataNotice, PageHeader, Section, StateBadge } from "@/components/product/workspace-ui";
import { RuleStudio } from "@/features/rules/rule-studio";
import { configurableRules, hardRules, ruleVersions } from "@/features/story/story-data";

export default function RulesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Deterministic rules"
        title="Understand the guardrails before changing a draft"
        description="Platform controls stay immutable. BA-owned business fields remain TBD until an approved ruleset supplies values and ranges."
      >
        <div className="mode-stamp">
          <ShieldCheck aria-hidden="true" /> Fails closed
        </div>
      </PageHeader>
      <DemoDataNotice />
      <Section
        id="hard-controls"
        title="Platform hard controls"
        description="These rules protect the authority boundary and cannot be weakened by a user, profile, agent, or demo draft."
      >
        <ol className="hard-rule-list">
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
      </Section>
      <Section
        id="rule-semantics"
        title="How rule decisions work"
        description="A modification is a new candidate, not permission to mutate an authorized payload."
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
      <RuleStudio rules={configurableRules} />
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
    </>
  );
}
