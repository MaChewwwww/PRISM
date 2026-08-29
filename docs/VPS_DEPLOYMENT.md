# VPS Deployment

## Prerequisites

- A maintained Linux VPS with Docker Engine and Compose v2.
- DNS and TLS certificates for the deployment hostname.
- A non-root deploy account with narrowly scoped Docker access.
- Alpaca paper credentials only: personal/dummy paper account for staging (`.env.staging`), and official Hackathon paper account ($100,000 baseline) for production (`.env.production`). Execution remains disabled for initial deployment.

## Deployment flow

1. Feature branches reach `staging` only through reviewed pull requests and required CI checks.
2. A successful push CI run on `staging` may deploy automatically to the protected staging environment when `STAGING_DEPLOY_ENABLED=true`.
3. A reviewed promotion pull request moves `staging` into `main`.
4. An authorized operator starts the protected manual production workflow with the exact `main` commit SHA.
5. The workflow builds immutable images, records digests, and deploys the exact revision.
6. Compose applies database migrations as a one-shot operation before application readiness.
7. Smoke checks verify Nginx routing, liveness, readiness, and the redacted system-status payload.
8. The operator confirms the kill switch and execution-disabled state.

See [CI/CD and Branch Promotion](CI_CD.md) for branch protections, environment configuration, and the bootstrap procedure.

## Network and storage

Expose only ports 80/443 through Nginx. PostgreSQL and Redis use private Compose networks and persistent named volumes; no database host port is allowed. Backups are encrypted, access-controlled, tested for restoration, and retained according to a BA/security-owned policy (**TBD**).

## Rollback

Application rollback redeploys the prior image digests. Database migrations must be forward-compatible; destructive migrations require a separately tested recovery plan. Rollback never deletes audit or execution records.

## Operations

Monitor host capacity, container health, database storage, certificate expiry, provider failures, and execution kill-switch state. Define alert thresholds and RTO/RPO before production authentication is enabled; these values are **TBD** and tracked in [FRS_NFRS.md](FRS_NFRS.md).
