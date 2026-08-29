# Frontend Design Rules

`docs/DESIGN.md` is the canonical visual design authority for **PRISM**. shadcn components are editable primitives, not the product's visual identity. Keep generated primitives in `frontend/src/components/ui/`; compose domain-specific components in `components/product/` or feature directories.

## Visual identity & design system

- **Brand name & tagline**: **PRISM** — *"One signal. Multiple perspectives. Better decisions."*
- **Theme**: Dark Cyber-Crystalline aesthetic with 3D perspective wireframe grid floor and faceted glass refractions.
- **Logo asset**: [`frontend/public/logo.png`](file:///d:/repos/Alpaca_AI_Hackaton/frontend/public/logo.png) (3D crystal prism tetrahedron). Always display on dark obsidian backgrounds.
- **Color tokens**:
  - Canvas / Background: Deep Obsidian (`#080B10`, `#0B0F14`, `#0F151D`, `#16202C`).
  - Brand Accent: Active Mineral Teal (`#547D83`), Hover (`#669299`), Subtle/Ghost (`rgba(84, 125, 131, 0.20)`), Glow (`rgba(84, 125, 131, 0.35)`).
  - Prismatic Agent Accents: Research (`#38BDF8` Ice Cyan), Proposal (`#10B981` Mint Green), Risk (`#F59E0B` Amber Gold), Rules Gate (`#547D83` Mineral Teal), ShadowFund (`#818CF8` Amethyst).
  - Glass Containers: Multi-layer specular frosted glass (`from-white/[0.06] to-white/[0.02]`) with 1px border (`rgba(255, 255, 255, 0.08)`), top specular reflection (`border-t-white/[0.16]`), and `backdrop-blur-xl`.
  - Semantic Status: Profit (`#00D084`), Loss (`#FF6B6B`), Warning (`#F59E0B`), Neutral/NO_TRADE (`#547D83`).
- **Typography**:
  - Display / Hero Headings: High-Contrast Display Serif with metallic/crystal teal reflection gradient.
  - Interface Headings & Body: **Plus Jakarta Sans** (regular 400, medium 500, semibold 600, bold 700).
  - Numbers & Financial Data: Tabular Monospace (`font-mono tabular-nums`) for currency values, strike prices, Greeks, timestamps, and contract hashes.
- **Geometry**: Pill shapes (`rounded-full`) for navigation, CTAs, and status pills; `rounded-xl` (12px) for major glass cards; `rounded-md` (6px) for sub-panels; `rounded-[4px]` for dense financial chips.

## Before building a screen

Write down:

- Visual thesis: Dark crystalline operational surface, high information clarity, `#547D83` mineral teal accent, multi-layer specular glass.
- Content plan: selected period or story, evidence, agent interpretation, deterministic decision, outcome, counterfactual, and lesson.
- Interaction thesis: one meaningful entrance, one state transition, and clear hover/focus affordances with reduced-motion fallbacks.

## Story model

- Organize user-facing work around decision stories, not backend module names or infrastructure entities.
- Preserve the authority order: catalyst and market context; seven specialist perspectives; Trading Decision proposal or NO_TRADE; AI-assisted Risk Management; deterministic rule gate; paper-only execution when genuinely recorded; ShadowFund alternatives; and asynchronous Post-Analysis.
- Keep the same validated UTC date range across related dashboard, story, portfolio, news, and agent views. Store filter state in the URL so a view can be revisited and shared.
- Show the registry-backed hackathon window in governance surfaces: new-entry cutoff, total-equity scoring point, force-flatten deadline, and outer boundary must be explicit and read-only.
- Label all data provenance. Use `Illustrative fixture` for the backend demonstration snapshot. Reserve `Alpaca paper`, `ShadowFund`, `Benchmark`, and `Simulated` for data that genuinely came from those sources.
- Treat NO_TRADE, FAIL, and incomplete evidence as meaningful terminal stories rather than missing content.

## Charts and metrics

- Every chart answers a question stated in its heading or summary and has an accessible exact-value table or equivalent textual fallback.
- Use solid-versus-dashed lines, labels, and shapes in addition to color when comparing genuinely sourced paper data with simulations or illustrative paths.
- Keep decimal strings authoritative. Conversion to binary numbers is allowed only in presentation adapters used for plotting.
- Synchronize charts and supporting tables to the same filter range; empty ranges render an explicit empty state rather than fabricated continuity.

## Agent and integration visibility

- Show concise rationale, evidence references, model and prompt versions, latency, token usage, tool/MCP names, and terminal state where available.
- Never expose hidden chain-of-thought, credentials, raw sensitive tool arguments/results, or provider errors.
- Clearly separate recorded use from planned capability. A configured or documented MCP/tool must not be presented as invoked without an invocation record.
- Infrastructure readiness and system status are operational concerns, not primary user navigation. Do not add a user-facing System page unless requirements explicitly introduce an administrative audience.

## Composition

- Product surfaces begin with the working context, not marketing copy or a hero.
- Prefer layout, spacing, typography, dividers, tables, and timelines over card mosaics.
- A card is justified only when the container itself is an interaction or a bounded decision object.
- Use the `#547D83` accent color, spectral agent accents, specular glass surfaces, restrained status tags, and avoid generic pill soup or decorative iconography.
- Use utility language: status, scope, freshness, decision, and action.
- Story detail views may use a sticky evidence inspector when it improves chronology and provenance; collapse it into the reading flow on narrow viewports.

## Quality gate

Every screen must handle loading, empty, degraded, error, and success states; keyboard navigation; visible focus (`ring-2 ring-[#547D83]`); accessible contrast (WCAG 2.2 AA); semantic headings; touch targets; reduced motion; and mobile (360px), tablet (768px), and desktop (1280px+) layouts. Never expose keys, account identifiers, private positions, or raw provider errors in an unauthenticated surface.
