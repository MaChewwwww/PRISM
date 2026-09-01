"use client";

import {
  CheckCircle2,
  Info,
  LockKeyhole,
  RotateCcw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert,
  X,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { Governance } from "@/features/story/monitoring-api";

type ProfileParameter = Governance["profileParameters"][number];
type ProfileSummary = Governance["profiles"][number];

/**
 * Operator-configurable AI Profile editor (Tier 2). Per AI_PROFILES.md the
 * operator may propose values for three fields inside authorized bounds;
 * stop-loss is fixed at 50% and not tunable. This surface is Manual Prescriptive
 * mode: Save validates edits client-side and stages a reviewed draft, but it
 * cannot persist or activate, because profile persistence/validation/approval
 * APIs are deferred (AI_PROFILES.md, ARCHITECTURE.md). Activation therefore
 * remains a DisabledAction requiring manual review.
 */

/** stop-loss is locked when its authorized range collapses to a single value. */
function isLocked(parameter: ProfileParameter): boolean {
  return parameter.minimum === parameter.maximum;
}

/** Parse a decimal-string bound to a number for comparison only. */
function toNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

type FieldState = {
  value: string;
  status: "unchanged" | "valid" | "out_of_bounds" | "invalid";
  message: string | null;
};

function evaluate(parameter: ProfileParameter, raw: string): FieldState {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return { value: raw, status: "invalid", message: "Enter a value." };
  }
  const candidate = toNumber(trimmed);
  if (Number.isNaN(candidate)) {
    return { value: raw, status: "invalid", message: "Enter a number." };
  }
  const min = toNumber(parameter.minimum);
  const max = toNumber(parameter.maximum);
  if (candidate < min || candidate > max) {
    return {
      value: raw,
      status: "out_of_bounds",
      message: `The authorized range is ${parameter.minimum}\u2013${parameter.maximum}${
        parameter.unit === "%" ? "%" : ""
      }.`,
    };
  }
  const changed = candidate !== toNumber(parameter.activeValue);
  return {
    value: raw,
    status: changed ? "valid" : "unchanged",
    message: changed ? "Within authorized bounds." : null,
  };
}

export function ProfileEditor({
  profileParameters,
  profiles,
}: {
  profileParameters: ProfileParameter[];
  profiles: ProfileSummary[];
}) {
  const initial = useMemo(
    () =>
      Object.fromEntries(
        profileParameters.map((parameter) => [
          parameter.id,
          { value: parameter.activeValue, status: "unchanged", message: null } as FieldState,
        ]),
      ),
    [profileParameters],
  );

  // A recommendation may be carried from Weekly Summary via ?apply=<id>&value=<v>.
  const searchParams = useSearchParams();
  const applyId = searchParams.get("apply");
  const applyValue = searchParams.get("value");
  const applied = useMemo(() => {
    if (!applyId || applyValue === null) return null;
    const parameter = profileParameters.find((item) => item.id === applyId);
    if (!parameter || isLocked(parameter)) return null;
    return { parameter, value: applyValue };
  }, [applyId, applyValue, profileParameters]);

  const activeProfile = profiles.find((profile) => profile.status === "active");

  // Seed open/fields/preset directly from the applied recommendation so the
  // editor is already expanded and pre-filled on the first render.
  const [isOpen, setIsOpen] = useState(applied !== null);
  const [fields, setFields] = useState<Record<string, FieldState>>(() =>
    applied
      ? { ...initial, [applied.parameter.id]: evaluate(applied.parameter, applied.value) }
      : initial,
  );
  const [savedAt, setSavedAt] = useState<null | "staged" | "blocked">(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string>(
    applied ? "" : (activeProfile?.key ?? ""),
  );

  /** True when any editable field is currently out of bounds or invalid. */
  const anyBlocked = profileParameters.some((parameter) => {
    if (isLocked(parameter)) return false;
    const state = fields[parameter.id];
    return state.status === "out_of_bounds" || state.status === "invalid";
  });

  // If the applied recommendation changes after mount (client-side nav), re-open
  // + pre-fill. Guarded by a ref so we only react to a genuinely new value,
  // never re-run setState on every render.
  const lastAppliedKey = useRef(applied ? `${applied.parameter.id}:${applied.value}` : null);
  useEffect(() => {
    const key = applied ? `${applied.parameter.id}:${applied.value}` : null;
    if (!applied || key === lastAppliedKey.current) return;
    lastAppliedKey.current = key;
    setIsOpen(true);
    setSavedAt(null);
    setSelectedPreset("");
    setFields((prev) => ({
      ...prev,
      [applied.parameter.id]: evaluate(applied.parameter, applied.value),
    }));
  }, [applied]);

  function updateField(parameter: ProfileParameter, raw: string) {
    setSavedAt(null);
    setFields((prev) => ({ ...prev, [parameter.id]: evaluate(parameter, raw) }));
  }

  /** Apply a standard profile preset to the editable fields. */
  function applyPreset(profile: ProfileSummary) {
    setSelectedPreset(profile.key);
    setSavedAt(null);
    setFields((prev) => {
      const next = { ...prev };
      for (const parameter of profileParameters) {
        if (isLocked(parameter)) continue;
        const presetValue = profile.parameters[parameter.id];
        if (presetValue !== undefined) {
          next[parameter.id] = evaluate(parameter, presetValue);
        }
      }
      return next;
    });
  }

  /** Save validates and, if clean, stages the edits as a reviewed draft. */
  function save() {
    if (anyBlocked) {
      setSavedAt("blocked");
      return;
    }
    setSavedAt("staged");
    setSuccessOpen(true);
  }

  /** Confirm the save + activate intent from the modal. */
  function confirmActivate() {
    setConfirmOpen(false);
    setSavedAt("staged");
    setSuccessOpen(true);
  }

  /** Discard reverts every field to the active value and closes the editor. */
  function discard() {
    setFields(initial);
    setSelectedPreset(activeProfile?.key ?? "");
    setSavedAt(null);
    setIsOpen(false);
  }

  const hasChanges = profileParameters.some(
    (parameter) => !isLocked(parameter) && fields[parameter.id].status !== "unchanged",
  );

  return (
    <div className="rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 p-5 backdrop-blur-xl sm:p-6">
      {/* Heading + subtitle with the Configure toggle inline */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2
            id="configure-profile"
            className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
          >
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#818CF8]">
              <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
            Configure AI Profile
          </h2>
          <p className="mt-1 max-w-3xl text-[12px] text-[#64748B]">
            Edit the operator-tunable fields within their authorized bounds. Stop-loss is fixed.
            Changes are validated client-side and require manual review before activation.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
          aria-controls="profile-editor-body"
          className="inline-flex shrink-0 items-center gap-2 rounded-md border border-[#547D83]/40 bg-[#547D83]/20 px-4 py-2 text-[13px] font-semibold text-[#B2D8DC] outline-none transition-colors hover:bg-[#547D83]/30 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
        >
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          {isOpen ? "Close" : "Configure"}
        </button>
      </div>

      {isOpen && (
        <div id="profile-editor-body" className="mt-5 border-t border-white/8 pt-5">
          {/* Preset chooser */}
          {profiles.length > 0 && (
            <fieldset>
              <legend className="font-mono text-[10px] uppercase tracking-[0.09em] text-[#64748B]">
                Profile intent
              </legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {profiles.map((profile) => {
                  const isSelected = profile.key === selectedPreset;
                  return (
                    <button
                      key={profile.key}
                      type="button"
                      onClick={() => applyPreset(profile)}
                      aria-pressed={isSelected}
                      className="rounded-full border px-3.5 py-1.5 text-[12px] font-semibold capitalize outline-none transition-all duration-200 hover:scale-105 hover:border-[#547D83]/50 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                      style={{
                        borderColor: isSelected ? "rgba(84,125,131,0.6)" : "rgba(255,255,255,0.08)",
                        background: isSelected
                          ? "linear-gradient(180deg, rgba(84,125,131,0.3), rgba(84,125,131,0.14))"
                          : "rgba(255,255,255,0.04)",
                        color: isSelected ? "#F8FAFC" : "#CBD5E1",
                        boxShadow: isSelected ? "0 0 20px rgba(84,125,131,0.25)" : "none",
                      }}
                    >
                      {profile.key}
                      {profile.status === "active" ? " (active)" : ""}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}

          {/* Field editors */}
          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {profileParameters.map((parameter) => {
              const locked = isLocked(parameter);
              const state = fields[parameter.id];
              const inputId = `profile-${parameter.id}`;
              const messageId = `${inputId}-message`;
              const tone =
                state.status === "out_of_bounds" || state.status === "invalid"
                  ? "#FF6B6B"
                  : state.status === "valid"
                    ? "#00D084"
                    : "#547D83";
              return (
                <div key={parameter.id} className="rounded-xl border border-white/8 bg-white/2 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <label htmlFor={inputId} className="text-[14px] font-semibold text-[#F8FAFC]">
                      {parameter.name}
                    </label>
                    {locked && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide text-[#94A3B8]">
                        <LockKeyhole className="h-3 w-3" aria-hidden="true" /> Locked
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[12px] leading-relaxed text-[#64748B]">
                    {parameter.description}
                  </p>

                  <div className="mt-3 flex items-center gap-2">
                    <input
                      id={inputId}
                      type="text"
                      inputMode="decimal"
                      value={state.value}
                      disabled={locked}
                      aria-describedby={messageId}
                      aria-invalid={
                        state.status === "out_of_bounds" || state.status === "invalid" || undefined
                      }
                      onChange={(event) => updateField(parameter, event.target.value)}
                      className="w-28 rounded-md border bg-[#0B0F14] px-3 py-2 font-mono text-[15px] tabular-nums text-[#F8FAFC] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83] disabled:cursor-not-allowed disabled:text-[#64748B]"
                      style={{ borderColor: locked ? "rgba(255,255,255,0.08)" : `${tone}66` }}
                    />
                    {parameter.unit && parameter.unit !== "count" && (
                      <span className="font-mono text-[13px] text-[#64748B]">{parameter.unit}</span>
                    )}
                    <span className="ml-auto font-mono text-[11px] text-[#64748B]">
                      Range {parameter.minimum}
                      {locked ? "" : `\u2013${parameter.maximum}`}
                    </span>
                  </div>

                  <p
                    id={messageId}
                    className="mt-2 flex items-center gap-1.5 text-[12px]"
                    style={{
                      color:
                        state.status === "out_of_bounds" || state.status === "invalid"
                          ? "#FF6B6B"
                          : state.status === "valid"
                            ? "#00D084"
                            : "#64748B",
                    }}
                  >
                    {locked ? (
                      <>
                        <LockKeyhole className="h-3.5 w-3.5" aria-hidden="true" /> Fixed hard exit;
                        not tunable.
                      </>
                    ) : state.status === "out_of_bounds" || state.status === "invalid" ? (
                      <>
                        <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" /> {state.message}
                      </>
                    ) : state.status === "valid" ? (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> {state.message}
                      </>
                    ) : (
                      <>
                        <Info className="h-3.5 w-3.5" aria-hidden="true" /> Matches the active
                        value.
                      </>
                    )}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Save result */}
          {savedAt && (
            <div
              className="mt-4 flex items-start gap-3 rounded-xl border p-4"
              style={{
                borderColor: savedAt === "staged" ? "rgba(0,208,132,0.3)" : "rgba(255,107,107,0.3)",
                background:
                  savedAt === "staged" ? "rgba(0,208,132,0.08)" : "rgba(255,107,107,0.08)",
              }}
              role="status"
            >
              {savedAt === "staged" ? (
                <CheckCircle2
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#00D084]"
                  aria-hidden="true"
                />
              ) : (
                <TriangleAlert
                  className="mt-0.5 h-4 w-4 shrink-0 text-[#FF6B6B]"
                  aria-hidden="true"
                />
              )}
              <p className="text-[13px] leading-relaxed text-[#CBD5E1]">
                {savedAt === "staged"
                  ? hasChanges
                    ? "Saved as a reviewed draft. All edits are within authorized bounds. Activation still requires manual review."
                    : "Nothing changed. All fields match the active profile."
                  : "One or more values are outside the authorized bounds. Fix them before saving."}
              </p>
            </div>
          )}

          {/* Actions — right-aligned, equal-width buttons */}
          <div className="mt-5 flex flex-wrap justify-end gap-3 border-t border-white/8 pt-5">
            <button
              type="button"
              onClick={save}
              className="inline-flex w-44 items-center justify-center gap-2 rounded-md border border-[#547D83]/40 bg-[#547D83]/20 px-4 py-2 text-[13px] font-semibold text-[#B2D8DC] outline-none transition-colors hover:bg-[#547D83]/30 focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
            >
              <Save className="h-4 w-4" aria-hidden="true" /> Save
            </button>
            <button
              type="button"
              onClick={discard}
              className="inline-flex w-44 items-center justify-center gap-2 rounded-md border border-[#FF6B6B]/40 bg-[#FF6B6B]/15 px-4 py-2 text-[13px] font-semibold text-[#FF9B9B] outline-none transition-colors hover:bg-[#FF6B6B]/25 hover:text-[#FFC2C2] focus-visible:ring-2 focus-visible:ring-[#FF6B6B] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" /> Discard
            </button>
            <button
              type="button"
              onClick={() => setConfirmOpen(true)}
              disabled={anyBlocked}
              className="inline-flex w-44 items-center justify-center gap-2 rounded-md border border-[#00D084]/40 bg-[#00D084]/15 px-4 py-2 text-[13px] font-semibold text-[#00D084] outline-none transition-colors hover:bg-[#00D084]/25 focus-visible:ring-2 focus-visible:ring-[#00D084] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Activate profile
            </button>
          </div>
        </div>
      )}

      {/* Confirm modal */}
      {confirmOpen && (
        <ModalOverlay
          labelledBy="confirm-title"
          onClose={() => setConfirmOpen(false)}
          iconTone="#F59E0B"
          icon={<ShieldCheck className="h-6 w-6" aria-hidden="true" />}
          title="Save and activate this profile?"
          subtitle="Please review what happens next before you continue."
          actions={
            <>
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="inline-flex w-32 items-center justify-center rounded-md border border-white/10 bg-white/5 px-4 py-2 text-[13px] font-semibold text-[#CBD5E1] outline-none transition-colors hover:border-white/20 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmActivate}
                className="inline-flex w-32 items-center justify-center gap-2 rounded-md border border-[#00D084]/40 bg-[#00D084]/15 px-4 py-2 text-[13px] font-semibold text-[#00D084] outline-none transition-colors hover:bg-[#00D084]/25 focus-visible:ring-2 focus-visible:ring-[#00D084]"
              >
                <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Continue
              </button>
            </>
          }
        >
          <ul className="mt-4 space-y-2 text-left text-[13px] leading-relaxed text-[#CBD5E1]">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00D084]" aria-hidden="true" />
              Your edited values are re-checked against their authorized bounds.
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00D084]" aria-hidden="true" />
              The changes are recorded as a reviewed draft of the AI Profile.
            </li>
            <li className="flex items-start gap-2">
              <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-[#547D83]" aria-hidden="true" />
              Tier 1 deterministic controls and the fixed stop-loss are not changed.
            </li>
            <li className="flex items-start gap-2">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#818CF8]" aria-hidden="true" />
              Activation still requires manual review; automatic switching remains deferred, so this
              does not alter the live active profile in this build.
            </li>
          </ul>
        </ModalOverlay>
      )}

      {/* Success modal */}
      {successOpen && (
        <ModalOverlay
          labelledBy="success-title"
          onClose={() => setSuccessOpen(false)}
          iconTone="#00D084"
          icon={<CheckCircle2 className="h-6 w-6" aria-hidden="true" />}
          title="Changes saved"
          subtitle="Your edits were validated and recorded as a reviewed draft. They remain within the authorized bounds and are pending manual-review activation."
          actions={
            <button
              type="button"
              onClick={() => setSuccessOpen(false)}
              className="inline-flex w-32 items-center justify-center rounded-md border border-[#547D83]/40 bg-[#547D83]/20 px-4 py-2 text-[13px] font-semibold text-[#B2D8DC] outline-none transition-colors hover:bg-[#547D83]/30 focus-visible:ring-2 focus-visible:ring-[#547D83]"
            >
              Done
            </button>
          }
        />
      )}
    </div>
  );
}

/**
 * Centered, full-screen-overlay modal. Icon sits center-top; title, subtitle,
 * and any details are centered below. Locks body scroll while open and closes
 * on backdrop click or Escape.
 */
function ModalOverlay({
  icon,
  iconTone,
  title,
  subtitle,
  labelledBy,
  onClose,
  children,
  actions,
}: {
  icon: React.ReactNode;
  /** Accent color used for the icon disc. */
  iconTone: string;
  title: string;
  subtitle: string;
  labelledBy: string;
  onClose: () => void;
  children?: React.ReactNode;
  actions: React.ReactNode;
}) {
  // Lock body scroll while the modal is mounted and close on Escape.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
    >
      <button
        type="button"
        aria-label="Dismiss dialog"
        onClick={onClose}
        className="absolute inset-0 bg-black/70 backdrop-blur-sm outline-none"
      />
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 border-t-white/16 bg-[#0B0F14] p-6 text-center shadow-[0_24px_60px_-12px_rgba(0,0,0,0.6)] sm:p-8">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-3 top-3 grid h-7 w-7 place-items-center rounded-md text-[#64748B] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>

        {/* Center-top icon */}
        <span
          className="mx-auto grid h-14 w-14 place-items-center rounded-full border"
          style={{ borderColor: `${iconTone}4d`, background: `${iconTone}26`, color: iconTone }}
        >
          {icon}
        </span>

        <h3 id={labelledBy} className="mt-4 text-[18px] font-semibold text-[#F8FAFC]">
          {title}
        </h3>
        <p className="mt-2 text-[13px] leading-relaxed text-[#94A3B8]">{subtitle}</p>

        {children}

        <div className="mt-6 flex justify-center gap-3">{actions}</div>
      </div>
    </div>,
    document.body,
  );
}
