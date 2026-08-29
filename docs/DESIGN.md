# PRISM — Design System & Branding Authority

**One signal. Multiple perspectives. Better decisions.**

This document establishes the canonical visual identity, design tokens, typography, component patterns, and styling guidelines for **PRISM**. It serves as the single source of design truth for developers, UI designers, and AI agents building operator interfaces, dashboards, and landing surfaces.

---

## 1. Brand Concept & Visual Thesis

### 1.1 The Optical Dispersion Metaphor
In physics, an optical prism refracts a single beam of white light into its constituent spectral wavelengths, revealing depth and structure that are invisible in the aggregate. 

In the same way, **PRISM takes a single market signal (catalyst, news, price anomaly) and autonomously breaks it down into multiple perspectives**:
- **Catalyst & Reaction Analysis** (Market Reaction / Mispricing Agent)
- **Candidate Options Strategies** (Trading Decision Agent)
- **Risk Critiques & Downside Stress-Tests** (Risk Management Layer)
- **Deterministic Boundary Enforcement** (Business Rules Gate)
- **Counterfactual Audits & Alternate Realities** (ShadowFund Intelligence)

### 1.2 Visual Thesis: Dark Cyber-Crystalline
The visual environment expresses institutional precision, intelligence, and depth through a **Dark Cyber-Crystalline** aesthetic:
- **Infinite Deep Obsidian Canvas**: Deep space blacks and midnight navy tones provide high contrast and reduce visual fatigue during prolonged market monitoring.
- **Multi-Layer Specular Glassmorphism**: Translucent frosted surfaces with delicate top-edge specular reflections (`border-t-white/15`), subtle inner ambient glows, and deep backdrop blurs mimic physical optical glass.
- **Mineral Sage Teal Accent (`#547D83`)**: A restrained, sophisticated mineral teal serves as the primary interactive accent, avoiding aggressive neon or generic SaaS blues.
- **Prismatic Spectral Highlights**: Controlled spectral accents (Cyan, Emerald, Amber, Teal, Indigo) map directly to each agent's analytical perspective.
- **Perspective Wireframe Grid Floor**: Subtle 3D vector gridlines with a smooth radial horizon fade evoke an analytical simulation space.

### 1.3 Design Evolution & Modernization Principles
While respecting the core prototype geometry and typography, PRISM elevates the UI to meet institutional, modern fintech aesthetics:
1. **Material Depth over Flat Gray**: Replace flat `#0B0F14` containers with layered gradient glass (`from-white/[0.06] to-white/[0.02]`) with specular top borders and ambient depth.
2. **Tactile Micro-interactions**: Smooth hover transitions with subtle glow blooms (`shadow-[0_0_24px_rgba(84,125,131,0.35)]`), button scale down on press (`active:scale-[0.98]`), and icon translation.
3. **Tabular Precision**: Enforce monospace tabular numbers (`font-mono tabular-nums`) for currency values, strike prices, options Greeks, and timestamps to eliminate layout jitter.
4. **Hierarchical Radii**: Combine sleek `rounded-full` pills for primary navigation/CTAs with `rounded-xl` (12px) for major glass modules and `rounded-[4px]` for compact financial tags.

---

## 2. Official Logo & Brand Assets

### 2.1 Primary Logo Emblem
- **Asset Path**: [`frontend/public/logo.png`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/logo.png)
- **Form**: 3D faceted tetrahedron crystal prism with glassy obsidian-teal refractions and sharp optical vertices.
- **Usage Context**:
  - Pinned Navigation Bar: 28px–32px height paired with the serif wordmark "PRISM".
  - Hero Section: Large floating 3D visual asset with subtle ambient glow and reflection.
  - Favicon & App Icon: Centered square crop on dark obsidian background.

### 2.2 Clear Space & Contrast
- Minimum clear space around the logo equals 50% of the emblem's width.
- Always display the logo on dark surfaces (`#080B10`, `#0B0F14`, `#0F151D`). Never place the crystalline emblem on light or saturated colored backgrounds.

### 2.3 Favicon & App Icon Assets
- **Root / App Favicon**: [`frontend/src/app/favicon.ico`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/src/app/favicon.ico) & [`frontend/public/favicon.ico`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/favicon.ico) (Multi-resolution: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256).
- **Standard PNG Favicon**: [`frontend/public/favicon-32x32.png`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/favicon-32x32.png) (32x32).
- **PWA & Web Manifest Icons**: [`frontend/public/icon-192.png`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/icon-192.png), [`frontend/public/icon-512.png`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/icon-512.png).

---

## 3. Color Palette & Design Tokens

### 3.1 Surface & Background Tokens (Deep Obsidian)
The dark palette is layered to establish clear spatial depth without harsh drop-shadows.

| Token Name | Hex Code | HSL / RGBA Equivalent | Purpose |
| :--- | :--- | :--- | :--- |
| `--color-canvas` | `#080B10` | `hsl(216, 33%, 5%)` | Primary viewport background / infinite canvas |
| `--color-surface-primary` | `#0B0F14` | `hsl(214, 29%, 6%)` | Base application shell / main layout background |
| `--color-surface-secondary`| `#0F151D` | `hsl(216, 31%, 9%)` | Section containers, table rows, secondary panels |
| `--color-surface-elevated` | `#16202C` | `hsl(215, 33%, 13%)` | Floating modals, dropdowns, elevated cards |

### 3.2 Brand & Accent Tokens
The brand uses mineral sage teal (`#547D83`) as its primary interactive accent.

| Token Name | Value | Purpose |
| :--- | :--- | :--- |
| `--color-brand-accent` | `#547D83` | Primary active buttons, focus rings, key indicators, interactive links |
| `--color-brand-accent-hover` | `#669299` | Hover state for primary buttons and interactive accents |
| `--color-brand-accent-ghost` | `rgba(84, 125, 131, 0.20)` | Secondary buttons, ghost containers, badge backgrounds |
| `--color-brand-accent-glow` | `rgba(84, 125, 131, 0.35)` | Ambient highlights, active tab glows, drop glows |

### 3.3 Prismatic Spectral Perspective Tokens
Each agent in the PRISM authority chain possesses a dedicated spectral accent:

| Agent Perspective | Accent Color | Tinted Background | Border Stroke | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Research (Catalyst)** | `#38BDF8` (Ice Cyan) | `rgba(56, 189, 248, 0.12)` | `rgba(56, 189, 248, 0.30)` | Catalyst detection, analog match, news analysis |
| **Proposal (Strategy)** | `#10B981` (Mint Green)| `rgba(16, 185, 129, 0.12)` | `rgba(16, 185, 129, 0.30)` | Proposed options strategy, strike selection |
| **Risk (Critique)** | `#F59E0B` (Amber Gold)| `rgba(245, 158, 11, 0.12)` | `rgba(245, 158, 11, 0.30)` | Risk challenge, tail-risk critique, modifications |
| **Rules Engine (Gate)** | `#547D83` (Mineral Teal)| `rgba(84, 125, 131, 0.15)` | `rgba(84, 125, 131, 0.35)` | Deterministic PASS/FAIL, hard boundary enforcement |
| **ShadowFund (Audit)** | `#818CF8` (Amethyst) | `rgba(129, 140, 248, 0.12)` | `rgba(129, 140, 248, 0.30)` | Counterfactual simulations, post-trade lessons |

### 3.4 Glassmorphism Tokens

| Token Name | Value | Description |
| :--- | :--- | :--- |
| `--glass-fill` | `linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%)` | Multi-layer frosted glass fill |
| `--glass-border` | `rgba(255, 255, 255, 0.08)` | Standard translucent perimeter border |
| `--glass-border-specular` | `rgba(255, 255, 255, 0.16)` | Top-edge specular glass reflection |
| `--glass-border-accent` | `rgba(84, 125, 131, 0.30)` | Glass border with brand teal reflection |
| `--glass-backdrop-blur` | `blur(16px)` | Standard backdrop filter for frosted panels |

### 3.5 Text & Foreground Tokens

| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--color-text-primary` | `#FFFFFF` / `#F8FAFC` | Main headings, active labels, primary values |
| `--color-text-secondary` | `#CBD5E1` | Body copy, secondary titles, narrative analysis |
| `--color-text-muted` | `#64748B` | Timestamp labels, metadata captions, inactive nav |
| `--color-border-subtle` | `#1E293B` / `rgba(255, 255, 255, 0.08)` | Dividers, table borders, inactive container strokes |

### 3.6 Semantic Status & P&L Colors

| Status | Hex Code | Background Tint | Usage |
| :--- | :--- | :--- | :--- |
| **Profit / Positive** | `#00D084` | `rgba(0, 208, 132, 0.15)` | Positive P&L, approved trades, PASS rules, high confidence |
| **Loss / Negative** | `#FF6B6B` | `rgba(255, 107, 107, 0.15)` | Negative P&L, rejected trades, FAIL rules, hard risk stop |
| **Warning / Caution** | `#F59E0B` | `rgba(245, 158, 11, 0.15)` | MODIFIED proposals, degraded evidence, approaching limit |
| **Neutral / NO_TRADE**| `#547D83` | `rgba(84, 125, 131, 0.15)` | NO_TRADE candidate, hold status, informational notice |

---

## 4. Typography System

The PRISM typographic hierarchy pairs a **high-contrast Display Serif** for brand statements and hero headers with **Plus Jakarta Sans** for crisp, modern operational clarity across all interfaces.

```text
Display / Hero Headings: High-Contrast Serif (with crystal metallic teal reflection)
UI Headings & Body Copy: Plus Jakarta Sans (400, 500, 600, 700)
Financial Data / Greeks / Hashes: Tabular Monospace (tabular-nums font-mono)
```

### 4.1 Font Families
- **Display Serif Font**: Playfair Display, Cinzel, or Cormorant Garamond (`font-serif`).
  - Used exclusively for the master brand wordmark "PRISM" and primary landing page hero titles.
  - Rendered with metallic/crystalline teal-to-white sheen:
    `linear-gradient(180deg, #FFFFFF 0%, #B2D8DC 60%, #547D83 100%)`.
- **Primary Interface Font**: **Plus Jakarta Sans** (`font-sans`).
  - Used for all interface headings (H1–H6), navigation, cards, form controls, and body text.
- **Monospace Font**: JetBrains Mono or Geist Mono (`font-mono`).
  - Used for contract digests, strike prices, option Greeks ($\Delta$, $\Gamma$, $\Theta$, $\text{IV}$), client order IDs, execution trace IDs, and timestamps.

### 4.2 Type Scale & Hierarchy

| Style | Font Family | Weight | Size / Line Height | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Brand Hero** | Display Serif | 700 / Bold | `5rem` / `5.5rem` (80px) | `0.05em` | Landing page "PRISM" hero |
| **Display H1** | Plus Jakarta Sans | 700 / Bold | `2.5rem` / `3rem` (40px) | `-0.02em` | Major page headlines |
| **Section H2** | Plus Jakarta Sans | 600 / SemiBold | `1.75rem` / `2.25rem` (28px) | `-0.01em` | Story module & view headers |
| **Card H3** | Plus Jakarta Sans | 600 / SemiBold | `1.25rem` / `1.75rem` (20px) | `0em` | Panel titles, decision headers |
| **Section Overline**| Plus Jakarta Sans| 600 / SemiBold | `0.75rem` / `1rem` (12px) | `0.20em` | Uppercase category overlines |
| **Subtitle / Lead**| Plus Jakarta Sans| 400 / Regular | `1.125rem` / `1.625rem` (18px)| `0em` | Hero descriptor, story summary |
| **Body Regular** | Plus Jakarta Sans | 400 / Regular | `0.875rem` / `1.375rem` (14px)| `0em` | Standard text, rationale, logs |
| **Body Medium** | Plus Jakarta Sans | 500 / Medium | `0.875rem` / `1.375rem` (14px)| `0em` | Table data, form values |
| **Caption / Meta** | Plus Jakarta Sans | 500 / Medium | `0.75rem` / `1rem` (12px) | `0.02em` | Timestamps, model versions, tags |
| **Financial / Code**| Monospace | 500 / Medium | `0.8125rem` / `1.125rem` (13px)| `0em` | Strikes, P&L, IDs, digests |

---

## 5. Geometry & Elevation

### 5.1 Corner Radii Hierarchy
PRISM balances sharp technical precision with comfortable pill-shaped affordances:

- **Pill Radius** (`rounded-full` / `9999px`): Top navigation bars, primary CTA buttons, floating status pills, and agent perspective chips.
- **Major Card Radius** (`rounded-xl` / `12px`): Outer decision story modules, chart containers, and modal dialogs.
- **Nested Container Radius** (`rounded-md` / `6px`): Sub-panels, agent critique boxes, and evidence preview drawers.
- **Compact Badge Radius** (`rounded-[4px]` / `4px`): Dense table cells, Greeks tags, and contract symbol chips.

### 5.2 Multi-Layer Specular Glass Recipe

```css
.prism-glass-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-color: rgba(255, 255, 255, 0.16);
  border-radius: 12px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}

.prism-glass-card-interactive {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-color: rgba(255, 255, 255, 0.16);
  border-radius: 12px;
  backdrop-filter: blur(16px);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.prism-glass-card-interactive:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
  border-color: rgba(84, 125, 131, 0.40);
  border-top-color: rgba(178, 216, 220, 0.50);
  box-shadow: 0 12px 40px -8px rgba(84, 125, 131, 0.25);
  transform: translateY(-2px);
}
```

---

## 6. Component Specifications & Patterns

### 6.1 Buttons

#### Active Primary Button ("Explore PRISM →")
- **Shape**: Pill (`rounded-full`)
- **Background**: `bg-gradient-to-r from-[#547D83] via-[#5D8B91] to-[#547D83]`
- **Text Color**: Crisp White (`#FFFFFF`), `font-sans`, Medium (500)
- **Icon**: Right arrow (`Lucide.ArrowRight`) with smooth translate on hover (`group-hover:translate-x-1`)
- **Hover State**: Border glow (`shadow-[0_0_20px_rgba(84,125,131,0.45)]`)
- **Press State**: `active:scale-[0.98]`

#### Subtle Ghost Button (20% Opacity)
- **Shape**: Pill (`rounded-full`)
- **Background**: `bg-[#547D83]/20` with `border border-[#547D83]/30`
- **Text Color**: `#FFFFFF`, `font-sans`, Medium (500)
- **Hover State**: `bg-[#547D83]/35 border-[#547D83]/50`

### 6.2 Floating Pill Navigation Bar
- **Position**: Pinned top with margin (`sticky top-4 z-50 mx-auto max-w-6xl px-4`)
- **Container**: `backdrop-blur-md bg-white/[0.05] border border-white/[0.10] border-t-white/[0.18] rounded-full px-6 py-3 shadow-2xl`
- **Left**: Crystal Logo (`28px`) + "PRISM" serif wordmark
- **Center**: Navigation Links (`Overview`, `Intelligence`, `How It Works`, `About`) in `text-slate-300 hover:text-white transition`
- **Right**: Pill CTA button (`Sign Up` / `Launch App`)

### 6.3 Agent Perspective Chips & Status Tags
- **Shape**: Pill (`rounded-full px-3 py-1 text-xs font-semibold inline-flex items-center gap-1.5`)
- **Variants**:
  - **Market Reaction / Mispricing Agent**: `bg-[#38BDF8]/15 text-[#38BDF8] border border-[#38BDF8]/30`
  - **Trading Decision Agent**: `bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30`
  - **Risk Management Layer**: `bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30`
  - **Rules Gate**: `bg-[#547D83]/20 text-[#B2D8DC] border border-[#547D83]/40`
  - **ShadowFund**: `bg-[#818CF8]/15 text-[#818CF8] border border-[#818CF8]/30`

### 6.4 3D Perspective Grid Background with Radial Horizon Fade
```css
.perspective-grid-floor {
  background-image: 
    linear-gradient(to right, rgba(84, 125, 131, 0.15) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(84, 125, 131, 0.15) 1px, transparent 1px);
  background-size: 44px 44px;
  transform: perspective(600px) rotateX(60deg);
  transform-origin: center top;
  mask-image: radial-gradient(ellipse at 50% 0%, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0) 75%);
  -webkit-mask-image: radial-gradient(ellipse at 50% 0%, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0) 75%);
}
```

---

## 7. Decision Story Architecture & UX

### 7.1 Chronological Decision Flow
PRISM's operator interface presents each trading decision as an auditable, narrative decision story:

```text
1. Catalyst & Reaction  → News headline, price move, analog comparison [Research: Cyan]
2. Research Evidence    → Overreaction/underreaction hypothesis, thesis score
3. Proposed Strategy    → Selected contract, debit spread, or NO_TRADE [Proposal: Mint]
4. Risk AI Critique     → Downside stress-test, tail-risk challenge [Risk: Amber]
5. Deterministic Gate   → Rules engine verdict (PASS / MODIFY / FAIL) [Gate: Teal]
6. Paper Outcome        → Live paper fill, P&L progression, exit [Paper: Emerald/Rose]
7. ShadowFund Audit     → Counterfactual alternative paths & learned lessons [Audit: Indigo]
```

### 7.2 Authority & Provenance Labelling
- **Paper Trading**: Solid border, primary teal indicators, explicit `[PAPER]` tag.
- **ShadowFund Simulation**: Dashed border, secondary muted badge, explicit `[SIMULATED]` tag.
- **Historical Analogs**: Dotted reference line, `[ANALOG]` indicator.
- **NO_TRADE / Reject**: Treated as first-class, intentional terminal decision cards with full reasoning traces.

---

## 8. Accessibility & Quality Standards (WCAG 2.2 AA)

- **Contrast Ratios**: All primary text (`#FFFFFF`, `#F8FAFC`) on dark backgrounds exceeds **12:1** (far exceeding the 4.5:1 requirement). Secondary text (`#CBD5E1`) maintains at least **7:1**.
- **Interactive Focus Rings**: All interactive components receive an explicit focus ring: `ring-2 ring-[#547D83] ring-offset-2 ring-offset-[#080B10]`.
- **Reduced Motion**: All animations (grid perspective movements, glowing refractions, transforms) must respect `prefers-reduced-motion: reduce` and fall back to static renderings.
- **Responsive Viewport Support**: Layouts must be verified and fully functional across:
  - **Mobile**: 360px width
  - **Tablet**: 768px width
  - **Desktop**: 1280px+ width
