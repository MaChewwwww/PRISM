import { ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";

import { DisabledAction, StateBadge } from "@/components/product/workspace-ui";
import type { WeeklySummary } from "@/features/story/presentation-api";

export function WeeklySummaryClient({ summary }: { summary: WeeklySummary }) {
  const confidenceOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...summary.suggestions].sort(
    (a, b) => (confidenceOrder[a.confidence] ?? 3) - (confidenceOrder[b.confidence] ?? 3),
  );

  return (
    <div className="weekly-summary-body">
      <div className="calibration-mode-header">
        <div>
          <p className="eyebrow">Manual Prescriptive mode</p>
          <h2>Recommendations awaiting operator review</h2>
          <p className="weekly-mode-description">
            Automatic switching is deferred. Nothing on this screen changes the active profile.
          </p>
        </div>
        <StateBadge state="manual review" />
      </div>

      <div className="calibration-mode-notice" role="note">
        <ShieldCheck aria-hidden="true" />
        <p>
          <strong>Deterministic boundary:</strong> only approved AI Profile fields may be proposed,
          and each value must remain inside the BA-authorized range.
        </p>
      </div>

      <div className="suggestion-list" aria-label="AI Profile recommendations">
        {sorted.map((suggestion) => (
          <article key={suggestion.id} className="suggestion-card">
            <div className="suggestion-card-header">
              <div className="suggestion-meta">
                <span className="suggestion-rule-name">{suggestion.parameterName}</span>
                <span
                  className="suggestion-confidence"
                  data-level={suggestion.confidence}
                  aria-label={`${suggestion.confidence} confidence`}
                >
                  {suggestion.confidence}
                </span>
              </div>
              <span className="suggestion-accepted-label">
                <CheckCircle2 aria-hidden="true" /> Within authorized bounds
              </span>
            </div>

            <div className="suggestion-value-row">
              <div className="suggestion-value-block">
                <span className="suggestion-value-label">Current</span>
                <span className="suggestion-value suggestion-value--current">
                  {suggestion.currentValue}
                </span>
              </div>
              <ArrowRight aria-hidden="true" className="suggestion-arrow" />
              <div className="suggestion-value-block">
                <span className="suggestion-value-label">Recommended</span>
                <span className="suggestion-value suggestion-value--proposed">
                  {suggestion.suggestedValue}
                </span>
              </div>
            </div>

            <dl className="key-value-list mt-3">
              <div>
                <dt>Authorized range</dt>
                <dd className="font-mono tabular-nums">
                  {suggestion.allowedMinimum} to {suggestion.allowedMaximum}
                </dd>
              </div>
              <div>
                <dt>Validation state</dt>
                <dd>{suggestion.validationState.replaceAll("_", " ")}</dd>
              </div>
            </dl>
            <p className="suggestion-rationale">{suggestion.rationale}</p>
          </article>
        ))}
      </div>

      <section className="staged-changes" aria-labelledby="manual-review-title">
        <div className="staged-header">
          <h2 id="manual-review-title">Manual activation boundary</h2>
        </div>
        <p className="mb-3 text-sm text-slate-300">
          The skeleton exposes review evidence only. It does not persist, approve, schedule, or
          activate a profile.
        </p>
        <DisabledAction
          label="Validate and activate profile"
          reason="Profile persistence, deterministic validation, and approval APIs are outside this aligned-skeleton pass."
        />
      </section>
    </div>
  );
}
