/**
 * Shared animated backdrop for landing sections: a visible teal grid plus a
 * couple of drifting aurora blobs. Purely decorative (aria-hidden).
 */
export function SectionBackground({ variant = "a" }: { variant?: "a" | "b" }) {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Static visible grid */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(84,125,131,0.16) 1px, transparent 1px), linear-gradient(to bottom, rgba(84,125,131,0.16) 1px, transparent 1px)",
          backgroundSize: "58px 58px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 85%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 85%)",
        }}
      />
      {/* Drifting aurora glows */}
      {variant === "a" ? (
        <>
          <div className="absolute -right-[6%] top-[8%] h-[420px] w-[420px] animate-aurora-a rounded-full bg-[var(--color-ice)]/[0.12] blur-[130px]" />
          <div className="absolute -left-[8%] bottom-[6%] h-[380px] w-[380px] animate-aurora-b rounded-full bg-[#818CF8]/[0.08] blur-[140px]" />
        </>
      ) : (
        <>
          <div className="absolute left-[10%] top-[10%] h-[400px] w-[400px] animate-aurora-b rounded-full bg-[#38BDF8]/[0.08] blur-[140px]" />
          <div className="absolute right-[4%] bottom-[10%] h-[420px] w-[420px] animate-aurora-a rounded-full bg-[var(--color-ice)]/[0.10] blur-[130px]" />
        </>
      )}
    </div>
  );
}
