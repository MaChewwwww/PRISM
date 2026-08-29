# Security

## Trust boundaries

External market/news providers, AI output, browsers, and CLI output are untrusted. Deterministic validation and authorization sit between all proposals and the execution adapter. PostgreSQL is authoritative for rules, decisions, receipts, and audit events; Redis is never authoritative.

## Credentials

- Secrets belong in deployment secret stores or local untracked environment files.
- `.env.example` contains names and safe defaults only.
- Keys are passed to the CLI through its process environment and never command arguments.
- Logs and public responses expose presence booleans, not values or account-sensitive details.
- MCP configuration with credentials must never be committed.

## Execution controls

Live trading is rejected during settings validation. Paper execution additionally requires an enabled flag, active ruleset, unexpired accepted authorization, matching proposal digest, fresh verified account state, suitable options level, and tradable contracts. A kill switch prevents new submissions and is checked immediately before invocation.

Every submission is idempotent, traceable, and reconciled after ambiguity. Agents and the frontend cannot bypass the backend execution service.

## Application and network controls

Production exposes Nginx only. Database and Redis remain on private networks without host ports. Containers use non-root users where practical, health checks, minimal runtime stages, and pinned bases. HTTP security headers, request-size limits, bounded timeouts, and TLS termination are required at the edge.

To safeguard staging and production deployments during hackathon evaluation and judge review, a seeded credential gate (`AUTH_EMAIL`, `AUTH_PASSWORD`, and HMAC-SHA256 session tokens signed with `AUTH_SECRET_KEY`) protects all operator UI views and operational endpoints (`/api/v1/system/status`), while preserving unauthenticated health checks (`/api/v1/health/live`, `/api/v1/health/ready`) for container orchestrators.

## Supply chain and CI

CI performs linting, type checks, tests, contract-diff checks, vendored-skill checksum verification, dependency audit, secret scan, and container scan. Production deployment is manual and protected by a GitHub environment. Build provenance and image digests are retained.

`staging` and `main` require reviewed PRs and branch-policy checks. Staging and production deployments use distinct protected GitHub environments, VPS checkout paths, Compose project names, ports (3005 for staging, 80 for production), secrets, credentials, and databases. Specifically, **staging uses a personal/dummy Alpaca paper account** for pre-release simulations and test trades, while **production uses the official Hackathon-provided Alpaca paper account** ($100,000 baseline). A staging credential must never be promoted by copying its environment file into production.

## Incident posture

On suspected compromise: enable the kill switch, disable execution, rotate Alpaca and deployment credentials, preserve audit data, reconcile paper orders, and record the incident timeline. Never erase evidence as part of recovery.
