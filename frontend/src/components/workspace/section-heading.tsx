import type { LucideIcon } from "lucide-react";

/** Shared glass card recipe (DESIGN.md Section 5.2), no hover glow. */
export const SECTION_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl";

/**
 * Left-aligned section heading rendered above a card: an accent-tinted icon
 * square, the title, and a muted subtitle. Shared across workspace pages so the
 * section styling stays consistent.
 */
export function SectionHeading({
  id,
  icon: Icon,
  title,
  subtitle,
  accent = "#547D83",
}: {
  id?: string;
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  /** Icon accent color (defaults to mineral teal). */
  accent?: string;
}) {
  return (
    <div className="mb-4">
      <h2
        id={id}
        className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
      >
        <span
          className="grid h-7 w-7 shrink-0 place-items-center rounded-md border"
          style={{ borderColor: `${accent}4d`, background: `${accent}26`, color: accent }}
        >
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        {title}
      </h2>
      {subtitle && <p className="mt-1 max-w-3xl text-[12px] text-[#64748B]">{subtitle}</p>}
    </div>
  );
}
