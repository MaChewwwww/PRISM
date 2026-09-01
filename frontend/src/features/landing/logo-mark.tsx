export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 28"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M2 22 L16 2 L30 22 L16 15 Z"
        fill="url(#prism-logo-gradient)"
        stroke="var(--color-ice-soft)"
        strokeWidth="0.75"
        strokeLinejoin="round"
      />
      <path d="M16 2 L16 15 L2 22 Z" fill="white" fillOpacity="0.08" />
      <defs>
        <linearGradient id="prism-logo-gradient" x1="2" y1="2" x2="30" y2="22" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--color-ice-soft)" />
          <stop offset="1" stopColor="var(--color-ice-dim)" />
        </linearGradient>
      </defs>
    </svg>
  );
}
