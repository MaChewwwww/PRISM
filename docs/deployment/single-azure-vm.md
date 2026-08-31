# PRISM single Azure VM runbook

PRISM staging and production currently share one protected Azure VM while
using isolated application roots, Compose projects, databases, credentials,
and edge ports.

## Runtime topology

| Environment | Application root | Compose overlays | Edge port | Readiness |
| --- | --- | --- | ---: | --- |
| Staging | `/opt/bgh/prism-staging` | `compose.yml`, `compose.production.yml`, `compose.staging.yml` | 3005 | `http://localhost:3005/api/v1/health/ready` |
| Production | `/opt/bgh/prism-production` | `compose.yml`, `compose.production.yml` | 80 | `http://localhost/api/v1/health/ready` |

PostgreSQL and Redis remain private to the Compose networks. Nginx is the only
production host-exposed service. Both environments use Alpaca paper mode only.

## Change flow

1. Implement application and infrastructure changes locally.
2. Run `pnpm verify` and `pnpm docker:config`.
3. Open a pull request targeting `staging`; do not edit source files on the VM.
4. After approval and merge, the staging workflow deploys the exact revision.
5. The production workflow deploys only from the protected `main` branch.
6. Confirm the migration service completes and readiness is healthy.

Runtime secrets and environment-specific schedules are maintained in the
server-side `.env` files and are never committed. Staging may configure a
historical-simulation command and rejects autonomous trading. Production autonomous
execution remains disabled unless separately reviewed and, when enabled, its
window must match the BA-authorized hackathon trading period.

## Recovery boundaries

Use the staging maintenance cheatsheet for lock-aware Compose operations and
rollback. Never force-push repository branches, remove database volumes, or
fall back to passwords for SSH or `sudo`. Backup and recovery retention, RPO,
and RTO remain unresolved until Operations authorizes them.
