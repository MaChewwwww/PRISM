"use client";

import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  Settings2,
  Sparkles,
  TrendingUp,
  X,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DisabledAction } from "@/components/product/workspace-ui";
import type { WeeklySummary } from "@/features/story/story-data";

type Mode = "auto" | "manual";

export function WeeklySummaryClient({ summary }: { summary: WeeklySummary }) {
  const [mode, setMode] = useState<Mode>("manual");
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  function accept(id: string) {
    setAccepted((prev) => new Set([...prev, id]));
    setDismissed((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function dismiss(id: string) {
    setDismissed((prev) => new Set([...prev, id]));
    setAccepted((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function stageAll() {
    setAccepted(new Set(summary.suggestions.map((s) => s.id)));
    setDismissed(new Set());
  }

  const pendingSuggestions = summary.suggestions.filter((s) => !dismissed.has(s.id));
  const stagedSuggestions = summary.suggestions.filter(
    (s) => mode === "auto" || accepted.has(s.id),
  );

  const confidenceOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...summary.suggestions].sort(
    (a, b) => (confidenceOrder[a.confidence] ?? 3) - (confidenceOrder[b.confidence] ?? 3),
  );

  return (
    <div className="weekly-summary-body">
      {/* Calibration mode toggle */}
      <div className="calibration-mode-header">
        <div>
          <p className="eyebrow">Post-analysis calibration</p>
          <h2>AI Rule Suggestions</h2>
          <p className="weekly-mode-description">
            Choose how AI suggestions are applied to your next draft ruleset.
          </p>
        </div>
        <div
          className="calibration-mode-toggle"
          role="group"
          aria-label="Calibration mode"
        >
          <button
            type="button"
            className="calibration-mode-btn"
            data-active={mode === "auto" ? "true" : "false"}
            onClick={() => setMode("auto")}
            aria-pressed={mode === "auto"}
          >
            <Cpu aria-hidden="true" />
            Auto-calibration
          </button>
          <button
            type="button"
            className="calibration-mode-btn"
            data-active={mode === "manual" ? "true" : "false"}
            onClick={() => setMode("manual")}
            aria-pressed={mode === "manual"}
          >
            <Settings2 aria-hidden="true" />
            Manual selection
          </button>
        </div>
      </div>

      {mode === "auto" && (
        <div className="calibration-mode-notice" role="status">
          <Sparkles aria-hidden="true" />
          <p>
            <strong>Auto-calibration active.</strong> All {summary.suggestions.length} suggestions
            below will be staged in the next draft on approval. Review them before submitting.
          </p>
        </div>
      )}

      {/* Suggestions list */}
      <div className="suggestion-list" aria-label="AI rule suggestions">
        {sorted.map((suggestion) => {
          const isDismissed = dismissed.has(suggestion.id);
          const isAccepted = mode === "auto" || accepted.has(suggestion.id);

          if (isDismissed && mode === "manual") return null;

          return (
            <article
              key={suggestion.id}
              className="suggestion-card"
              data-accepted={isAccepted ? "true" : "false"}
              aria-label={`Suggestion: ${suggestion.ruleName}`}
            >
              <div className="suggestion-card-header">
                <div className="suggestion-meta">
                  <span className="suggestion-rule-name">{suggestion.ruleName}</span>
                  <span
                    className="suggestion-confidence"
                    data-level={suggestion.confidence}
                    aria-label={`${suggestion.confidence} confidence`}
                  >
                    {suggestion.confidence}
                  </span>
                </div>
                {mode === "manual" && (
                  <div className="suggestion-actions">
                    {isAccepted ? (
                      <span className="suggestion-accepted-label">
                        <CheckCircle2 aria-hidden="true" /> Staged
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="suggestion-accept-btn"
                        onClick={() => accept(suggestion.id)}
                        aria-label={`Accept suggestion for ${suggestion.ruleName}`}
                      >
                        <CheckCircle2 aria-hidden="true" /> Accept
                      </button>
                    )}
                    <button
                      type="button"
                      className="suggestion-dismiss-btn"
                      onClick={() => dismiss(suggestion.id)}
                      aria-label={`Dismiss suggestion for ${suggestion.ruleName}`}
                    >
                      <X aria-hidden="true" />
                    </button>
                  </div>
                )}
                {mode === "auto" && (
                  <span className="suggestion-auto-label">
                    <TrendingUp aria-hidden="true" /> Will stage on approval
                  </span>
                )}
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
                  <span className="suggestion-value-label">Suggested</span>
                  <span className="suggestion-value suggestion-value--proposed">
                    {suggestion.suggestedValue}
                  </span>
                </div>
              </div>

              <p className="suggestion-rationale">{suggestion.rationale}</p>
            </article>
          );
        })}

        {mode === "manual" && dismissed.size === summary.suggestions.length && (
          <p className="inline-empty">All suggestions dismissed. Reset to reconsider.</p>
        )}
      </div>

      {/* Staged changes panel */}
      <section className="staged-changes" aria-labelledby="staged-title">
        <div className="staged-header">
          <h2 id="staged-title">
            Staged for next draft
            {stagedSuggestions.length > 0 && (
              <span className="staged-count">{stagedSuggestions.length}</span>
            )}
          </h2>
          {mode === "auto" && stagedSuggestions.length > 0 && (
            <span className="staged-mode-label">Auto — all suggestions included</span>
          )}
          {mode === "manual" && summary.suggestions.length > accepted.size && (
            <button type="button" className="staged-stage-all" onClick={stageAll}>
              Stage all
            </button>
          )}
        </div>

        {stagedSuggestions.length > 0 ? (
          <>
            <ul className="staged-list">
              {stagedSuggestions.map((s) => (
                <li key={s.id}>
                  <CheckCircle2 aria-hidden="true" className="staged-check" />
                  <span>
                    <strong>{s.ruleName}</strong>: {s.currentValue} → {s.suggestedValue}
                  </span>
                  {mode === "manual" && (
                    <button
                      type="button"
                      className="staged-remove"
                      onClick={() => dismiss(s.id)}
                      aria-label={`Remove ${s.ruleName} from staged`}
                    >
                      <XCircle aria-hidden="true" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <div className="staged-footer">
              <DisabledAction
                label="Submit staged changes for approval"
                reason="Ruleset persistence, deterministic validation, and approval APIs are not connected in this prototype."
              />
              <p>
                Staged changes go to{" "}
                <Link href="/rules" className="detail-link">
                  Rules
                </Link>{" "}
                for final review before any approval request.
              </p>
            </div>
          </>
        ) : (
          <p className="inline-empty">
            {mode === "manual"
              ? "Accept at least one suggestion above to stage it for the next draft."
              : "No suggestions available to stage."}
          </p>
        )}
      </section>
    </div>
  );
}
