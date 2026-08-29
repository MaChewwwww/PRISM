# Repository Agent Instructions

This file is the canonical instruction entrypoint for every coding agent and contributor in this repository. `CLAUDE.md` and `GEMINI.md` only redirect here.

## Required reading order

Before changing code or documentation, read the applicable rules in order:

1. `.agents/rules/00-repository-onboarding.md`
2. `.agents/rules/10-architecture.md`
3. `.agents/rules/20-alpaca-documentation.md` for Alpaca-facing work
4. `.agents/rules/30-trading-safety.md` for market, portfolio, rules, or execution work
5. `.agents/rules/40-frontend-design.md` for frontend work
6. `.agents/rules/50-testing-quality.md`
7. `.agents/rules/60-documentation.md`
8. `.agents/rules/70-commits-pull-requests.md` for commits, branches, and pull requests

Read `docs/README.md` and the documents it identifies for the subsystem being changed. Follow the authority chain recorded there: repository invariants -> BA requirements and the machine-readable parameter register -> AI architecture -> API contracts -> implementation/tests -> explanatory concept documents. The application name is confirmed as **PRISM**. The BA-owned numerical governance thresholds and fixed hackathon window are authorized in `backend/app/rules/authorized_baseline.v1.json`, `docs/BUSINESS_RULES.md`, and `docs/AI_PROFILES.md`. Thresholds not covered there (for example SLOs and backup RPO/RTO) remain unresolved and must not be guessed.

## Non-negotiable repository invariants

- The system is paper-trading only. Never add or enable a live-trading path.
- AI produces research, proposals, critiques, and recommendations; deterministic code authorizes execution.
- The frontend never receives Alpaca or LLM credentials and never calls Alpaca directly.
- Execution is disabled by default and fails closed without a valid active ruleset and authorization.
- Financial values use decimal-safe representations, never binary floating point at trust boundaries.
- Do not invent thresholds, product names, API behavior, or Alpaca capabilities. Use the BA-authorized governance values from the source-of-truth docs; anything still unresolved stays unresolved until authorized.
- Preserve generated/source boundaries. Regenerate contract output instead of hand-editing it.
- Vendored Alpaca skills are upstream references. These root rules take precedence over them.
- Format communication and documentation in standard Markdown. Never use LaTeX syntax or math-mode markers; use plain ASCII arrows (`->`) and plain-text mathematical comparisons.

## Normal verification

Run the narrowest relevant checks while developing, then run `pnpm verify` before handing off a repository-wide change. Paper API integration tests are opt-in and must never place an order unless the user explicitly requests that test.
