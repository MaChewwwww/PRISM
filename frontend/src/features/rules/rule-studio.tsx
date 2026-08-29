"use client";

import { RotateCcw, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { DisabledAction, StateBadge } from "@/components/product/workspace-ui";
import type { ConfigurableRule } from "@/features/story/story-data";

export function RuleStudio({ rules }: { rules: ConfigurableRule[] }) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [previewed, setPreviewed] = useState(false);
  const configuredCount = useMemo(
    () => Object.values(draft).filter((value) => value.trim().length > 0).length,
    [draft],
  );

  function reset() {
    setDraft({});
    setPreviewed(false);
  }

  return (
    <div className="rule-studio">
      <div className="rule-studio-toolbar">
        <div>
          <p className="eyebrow">Browser-local draft · demo-draft.3</p>
          <h2>Configurable business fields</h2>
          <p>Values reset on refresh and never become an active ruleset.</p>
        </div>
        <div>
          <button type="button" className="secondary-action" onClick={reset}>
            <RotateCcw aria-hidden="true" /> Reset draft
          </button>
          <button
            type="button"
            className="primary-action"
            disabled={configuredCount === 0}
            onClick={() => setPreviewed(true)}
          >
            <Sparkles aria-hidden="true" /> Preview synthetic impact
          </button>
        </div>
      </div>

      <div className="rule-editor-list">
        {rules.map((rule) => (
          <section key={rule.id} aria-labelledby={`${rule.id}-name`}>
            <div className="rule-editor-copy">
              <div>
                <span>Draft field</span>
                <StateBadge state="TBD" />
              </div>
              <h3 id={`${rule.id}-name`}>{rule.name}</h3>
              <p>{rule.description}</p>
              <dl>
                <div>
                  <dt>How it is measured</dt>
                  <dd>{rule.input}</dd>
                </div>
                <div>
                  <dt>What it changes</dt>
                  <dd>{rule.effect}</dd>
                </div>
              </dl>
            </div>
            <div className="rule-input">
              <label htmlFor={`${rule.id}-value`}>Proposed value</label>
              <div>
                <input
                  id={`${rule.id}-value`}
                  inputMode="decimal"
                  value={draft[rule.id] ?? ""}
                  onChange={(event) => {
                    setDraft((current) => ({ ...current, [rule.id]: event.target.value }));
                    setPreviewed(false);
                  }}
                  placeholder={`Current: ${rule.activeValue}`}
                  aria-describedby={`${rule.id}-help`}
                />
                <span>{rule.unit}</span>
              </div>
              <small id={`${rule.id}-help`}>
                Active value: <strong>{rule.activeValue} {rule.unit}</strong>. Entering a new value creates a draft candidate — it does not modify the active ruleset.
              </small>
            </div>
          </section>
        ))}
      </div>

      <section className="impact-preview" aria-labelledby="impact-preview-title">
        <div>
          <p className="eyebrow">Illustrative preview</p>
          <h2 id="impact-preview-title">What would have changed in the synthetic story set?</h2>
          <p>This is a presentation fixture, not the production deterministic evaluator.</p>
        </div>
        {previewed ? (
          <div className="preview-results" role="status">
            <dl>
              <div>
                <dt>Fields included</dt>
                <dd>{configuredCount}</dd>
              </div>
              <div>
                <dt>Stories reclassified</dt>
                <dd>{Math.min(configuredCount, 2)}</dd>
              </div>
              <div>
                <dt>Additional no-trade outcomes</dt>
                <dd>{configuredCount > 2 ? 1 : 0}</dd>
              </div>
              <div>
                <dt>Executable authority created</dt>
                <dd>None</dd>
              </div>
            </dl>
            <p>
              Illustrative result: review the affected stories before any future approval request.
            </p>
          </div>
        ) : (
          <p className="inline-empty">
            Enter at least one draft value, then preview its explicitly synthetic impact.
          </p>
        )}
        <div className="rule-approval">
          <DisabledAction
            label="Approve and activate"
            reason="Ruleset persistence, deterministic validation, and approval APIs are not connected."
          />
          <p>Platform hard limits remain immutable regardless of any draft value.</p>
        </div>
      </section>
    </div>
  );
}
