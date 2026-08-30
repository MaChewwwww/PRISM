---
name: prism-design
description: Design system and branding guide for PRISM UI development. Use when creating, styling, or reviewing frontend components, landing pages, decision story views, charts, and design tokens to ensure alignment with PRISM brand identity, color palette (#547D83, obsidian surfaces, specular glass), typography (Plus Jakarta Sans and Display Serif), spectral agent perspectives, and WCAG 2.2 AA accessibility standards.
---

# PRISM Design System & Branding Skill

Use this skill to guide the construction, styling, and composition of frontend interfaces, design tokens, and UI components for **PRISM**. `docs/DESIGN.md` and `.agents/rules/40-frontend-design.md` remain the canonical authorities.

---

## 1. Brand Core & Visual Metaphor

- **Application Name**: **PRISM**
- **Tagline**: *"One signal. Multiple perspectives. Better decisions."*
- **Aesthetic**: **Dark Cyber-Crystalline** — institutional fintech precision, obsidian canvas, multi-perspective optical glass refractions, restrained mineral teal accent (`#547D83`), and 3D perspective wireframe gridlines with radial horizon fade.
- **Logo Asset**: `frontend/public/logo.png` (3D tetrahedron crystal prism).

---

## 2. Design Tokens & Color Palette

### 2.1 Surfaces & Canvas (Dark Obsidian)
```css
--canvas: #080b10;             /* Viewport canvas */
--surface-primary: #0b0f14;    /* Layout shell & main containers */
--surface-secondary: #0f151d;  /* Table rows, secondary panels */
--surface-elevated: #16202c;   /* Dropdowns, modals, floating cards */
```

### 2.2 Brand Mineral Teal (`#547D83`)
```css
--accent-primary: #547d83;               /* Active buttons, focus rings, primary highlights */
--accent-hover: #669299;                 /* Interactive hover */
--accent-ghost: rgba(84, 125, 131, 0.20);/* 20% opacity ghost button / soft badge fill */
--accent-glow: rgba(84, 125, 131, 0.35); /* Ambient glow bloom */
```

### 2.3 Prismatic Spectral Agent Accents
```css
--perspective-research: #38bdf8;   /* Ice Cyan: Catalyst Detection & Analogs */
--perspective-proposal: #10b981;   /* Mint Green: Options Strategy Candidate */
--perspective-risk: #f59e0b;       /* Amber Gold: Risk AI Critique & Tail-Risk */
--perspective-gate: #547d83;       /* Mineral Teal: Deterministic Rules Engine */
--perspective-shadowfund: #818cf8; /* Amethyst: Counterfactuals & Audit */
```

### 2.4 Multi-Layer Specular Glassmorphism
```css
--glass-fill: linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
--glass-border: rgba(255, 255, 255, 0.08);
--glass-border-specular: rgba(255, 255, 255, 0.16);
--glass-blur: blur(16px);
```

### 2.5 Semantic Status & P&L Colors
```css
--status-profit: #00d084;  /* Emerald: Positive P&L, PASS rules, high confidence */
--status-loss: #ff6b6b;    /* Coral Rose: Negative P&L, FAIL rules, hard stop */
--status-warning: #f59e0b; /* Amber Gold: MODIFIED rules, degraded evidence */
--status-neutral: #547d83; /* Teal/Slate: NO_TRADE, hold, informational */
```

---

## 3. Typography Rules

1. **Display & Brand Headings** (`font-serif`):
   - High-contrast Display Serif (Playfair Display / Cinzel style) for brand title "PRISM" and landing hero headers.
   - Use gradient text sheen: `bg-gradient-to-b from-white via-[#B2D8DC] to-[#547D83] bg-clip-text text-transparent`.
2. **Interface Headings, UI & Body** (`font-sans`):
   - **Plus Jakarta Sans** across all H1–H6, navigation, buttons, forms, tables, and narrative summaries.
   - Weights: Regular (400), Medium (500), SemiBold (600), Bold (700).
3. **Financial Figures, Timestamps, Greeks & Hashes** (`font-mono tabular-nums`):
   - JetBrains Mono / Geist Mono for currency decimals, strike prices, option Greeks (Delta, Gamma, Theta, IV), execution receipts, trace IDs, and digests.

---

## 4. Component Patterns & Recipes

### 4.1 Specular Glass Card Recipe (`rounded-xl` / `12px`)
```html
<div class="rounded-xl bg-gradient-to-b from-white/[0.06] to-white/[0.02] border border-white/[0.08] border-t-white/[0.16] backdrop-blur-xl p-6 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] transition-all hover:border-[#547D83]/40 hover:shadow-[0_12px_40px_-8px_rgba(84,125,131,0.25)] hover:-translate-y-0.5">
  <!-- Card Content -->
</div>
```

### 4.2 Interactive Buttons (Pill Shapes)
```html
<!-- Primary Active Button with Micro-glow & Arrow Shift -->
<button class="group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#547D83] via-[#5D8B91] to-[#547D83] px-6 py-2.5 text-sm font-medium text-white shadow-lg transition-all hover:shadow-[0_0_20px_rgba(84,125,131,0.45)] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-[#547D83] focus:ring-offset-2 focus:ring-offset-[#080B10]">
  <span>Explore PRISM</span>
  <svg class="h-4 w-4 transition-transform group-hover:translate-x-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M5 12h14M12 5l7 7-7 7"/>
  </svg>
</button>

<!-- Secondary Ghost Button (20% Opacity) -->
<button class="inline-flex items-center gap-2 rounded-full bg-[#547D83]/20 border border-[#547D83]/30 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-[#547D83]/35 hover:border-[#547D83]/50 focus:outline-none focus:ring-2 focus:ring-[#547D83]">
  <span>Decision Story Journal</span>
</button>
```

### 4.3 Floating Pill Header Navigation
```html
<header class="sticky top-4 z-50 mx-auto max-w-6xl px-4">
  <nav class="flex items-center justify-between rounded-full bg-white/[0.05] border border-white/[0.10] border-t-white/[0.18] backdrop-blur-md px-6 py-3 shadow-2xl">
    <div class="flex items-center gap-3">
      <img src="/logo.png" alt="PRISM" class="h-7 w-7 object-contain" />
      <span class="font-serif text-lg tracking-wider text-white">PRISM</span>
    </div>
    <div class="hidden md:flex items-center gap-8 text-sm text-slate-300">
      <a href="#overview" class="transition hover:text-white">Overview</a>
      <a href="#intelligence" class="transition hover:text-white">Intelligence</a>
      <a href="#how-it-works" class="transition hover:text-white">How It Works</a>
      <a href="#about" class="transition hover:text-white">About</a>
    </div>
    <button class="rounded-full bg-white/10 border border-white/20 px-5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#547D83]">
      Sign Up
    </button>
  </nav>
</header>
```

### 4.4 Prismatic Agent Perspective Badges
```html
<!-- Research Agent (Ice Cyan) -->
<span class="inline-flex items-center gap-1.5 rounded-full bg-[#38BDF8]/15 border border-[#38BDF8]/30 px-3 py-1 text-xs font-semibold text-[#38BDF8]">
  <span class="h-1.5 w-1.5 rounded-full bg-[#38BDF8]"></span>
  Research: Catalyst Mismatch
</span>

<!-- Proposal Agent (Mint Green) -->
<span class="inline-flex items-center gap-1.5 rounded-full bg-[#10B981]/15 border border-[#10B981]/30 px-3 py-1 text-xs font-semibold text-[#10B981]">
  <span class="h-1.5 w-1.5 rounded-full bg-[#10B981]"></span>
  Proposal: Bull Call Debit Spread
</span>

<!-- Risk Agent (Amber Gold) -->
<span class="inline-flex items-center gap-1.5 rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/30 px-3 py-1 text-xs font-semibold text-[#F59E0B]">
  <span class="h-1.5 w-1.5 rounded-full bg-[#F59E0B]"></span>
  Risk: Max Loss Bounded ($420)
</span>

<!-- Rules Engine Gate (Mineral Teal) -->
<span class="inline-flex items-center gap-1.5 rounded-full bg-[#547D83]/20 border border-[#547D83]/40 px-3 py-1 text-xs font-semibold text-[#B2D8DC]">
  <span class="h-1.5 w-1.5 rounded-full bg-[#547D83]"></span>
  Rules Gate: PASS (v1.0.4)
</span>

<!-- ShadowFund Audit (Amethyst) -->
<span class="inline-flex items-center gap-1.5 rounded-full bg-[#818CF8]/15 border border-[#818CF8]/30 px-3 py-1 text-xs font-semibold text-[#818CF8]">
  <span class="h-1.5 w-1.5 rounded-full bg-[#818CF8]"></span>
  ShadowFund: Counterfactual Audit
</span>
```

### 4.5 3D Perspective Grid Background with Radial Horizon Mask
```html
<div class="relative overflow-hidden bg-[#080B10]">
  <!-- 3D Receding Grid Floor with Horizon Mask -->
  <div class="pointer-events-none absolute inset-x-0 bottom-0 h-96 [mask-image:radial-gradient(ellipse_at_50%_0%,black_0%,transparent_75%)]">
    <div class="h-full w-full [transform:perspective(600px)_rotateX(60deg)] [transform-origin:center_top] [background-image:linear-gradient(to_right,rgba(84,125,131,0.15)_1px,transparent_1px),linear-gradient(to_bottom,rgba(84,125,131,0.15)_1px,transparent_1px)] [background-size:44px_44px]"></div>
  </div>
</div>
```

---

## 5. Quality & Accessibility Checklist

- [ ] Does the surface use `#080B10` canvas with specular glass layers?
- [ ] Are financial numbers and timestamps rendered in `font-mono tabular-nums`?
- [ ] Are agent perspectives color-coded with their respective spectral accents?
- [ ] Are interactive buttons configured with `#547D83` gradient or 20% opacity ghost styles?
- [ ] Do all interactive elements have visible focus rings (`ring-2 ring-[#547D83]`)?
- [ ] Are portfolio assets, equity, and cash presented with professional active terminology (e.g. "Active Portfolio", "Cash reserve") without "Illustrative cash" labels?
- [ ] Does the layout adapt gracefully at 360px, 768px, and 1280px?
