# Documentation Rules

Engineering documentation is part of the implementation.

- Update `FRS_NFRS.md` when externally observable requirements change.
- Update `DATA_API_CONTRACTS.md` and generated contracts together.
- Update `ARCHITECTURE.md` for dependency, trust-boundary, module, or topology changes.
- Update `BUSINESS_RULES.md`, `AI_PROFILES.md`, and `AI_AGENTS.md` for authority or configuration changes.
- Update `SECURITY.md`, `DOCKER.md`, and `VPS_DEPLOYMENT.md` for operational changes.
- Update `CI_CD.md` for commit policy, branch flow, required checks, environments, or deployment workflow changes.
- Keep `IMPLEMENTATION_PLAN.md` status honest.
- When the BA changes a dated operating window, mirror its start, entry cutoff, scoring basis/point, force-flatten deadline, and outer boundary in the registry, API, frontend governance surface, and both concept formats.
- Preserve explicit TBDs; do not turn examples into requirements.
- Include source links and dates for time-sensitive Alpaca behavior.
- Maintain `DESIGN.md` as the authoritative design system and visual branding specification.

Use concise Markdown, stable heading anchors, and repository-relative links. Every new document must be linked from `docs/README.md`. Avoid LaTeX math syntax; use plain ASCII arrows (`->`) and plain-text comparisons instead.
