# Testing and Quality Rules

- Add tests for behavior changes, especially denials and failures.
- Mock Alpaca in normal unit and CI tests. Networked paper tests are opt-in, isolated, and read-only/dry-run unless the user explicitly requests an order test.
- Assert that rejected, expired, stale, mismatched, or unconfigured decisions never reach the CLI runner.
- Test idempotency and ambiguous-result reconciliation by client order ID.
- Validate generated schemas and example fixtures; regenerate TypeScript types and fail on drift.
- Frontend tests cover status variants, custom compositions, accessibility, and responsive behavior.
- Run Ruff, mypy, pytest, ESLint, formatting checks, Vitest, contract checks, and builds for repository-wide work.
- Do not weaken a test, type check, linter, or security control solely to make a change pass.

The full local quality gate is `pnpm verify`. Validate Compose with `pnpm docker:config` when infrastructure changes.
