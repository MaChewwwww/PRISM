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
      {/* Drifting aurora glows (optimized with radial gradient to avoid GPU blur overhead) */}
      {variant === "a" ? (
        <>
          <div
            className="absolute -right-[6%] top-[8%] h-[460px] w-[460px] animate-aurora-a rounded-full opacity-60 will-change-transform"
            style={{
              background:
                "radial-gradient(circle, rgba(84,125,131,0.22) 0%, rgba(84,125,131,0.08) 45%, transparent 70%)",
            }}
          />
          <div
            className="absolute -left-[8%] bottom-[6%] h-[420px] w-[420px] animate-aurora-b rounded-full opacity-50 will-change-transform"
            style={{
              background:
                "radial-gradient(circle, rgba(129,140,248,0.18) 0%, rgba(129,140,248,0.06) 45%, transparent 70%)",
            }}
          />
        </>
      ) : (
        <>
          <div
            className="absolute left-[10%] top-[10%] h-[440px] w-[440px] animate-aurora-b rounded-full opacity-50 will-change-transform"
            style={{
              background:
                "radial-gradient(circle, rgba(56,189,248,0.16) 0%, rgba(56,189,248,0.05) 45%, transparent 70%)",
            }}
          />
          <div
            className="absolute right-[4%] bottom-[10%] h-[460px] w-[460px] animate-aurora-a rounded-full opacity-55 will-change-transform"
            style={{
              background:
                "radial-gradient(circle, rgba(84,125,131,0.20) 0%, rgba(84,125,131,0.06) 45%, transparent 70%)",
            }}
          />
        </>
      )}
    </div>
  );
}
