# Docker

## Local stack

Copy `.env.example` to an untracked `.env`, then run:

```bash
pnpm docker:up
```

The base Compose file starts frontend, backend, PostgreSQL 17, and the optional Redis profile. Seeded credentials (`AUTH_EMAIL`, `AUTH_PASSWORD`, `AUTH_SECRET_KEY`) configured in `.env` protect the console interface. Execution remains disabled and no Alpaca credentials are required for baseline health/status operation.

Inspect the resolved configuration with `pnpm docker:config` and stop it with `pnpm docker:down`.

## Production override

```bash
docker compose -f compose.yml -f compose.production.yml up -d --build
```

The override adds Nginx as the only published service, removes database/cache host exposure, enables persistent volumes and restart policies, and routes `/api/` and `/openapi.json` to the backend. TLS should terminate at Nginx or an upstream trusted reverse proxy.

For the isolated staging deployment, append `-f compose.staging.yml`; it overrides Nginx to `${STAGING_HTTP_PORT:-3005}` and runs under a separate Compose project name and VPS path.

## Images

Both application images use multi-stage builds. The backend image builds Alpaca CLI v0.0.13 in a dedicated Go stage and copies only the executable into the Python runtime. Build images and OS packages are pinned; lockfiles are copied before source to maximize deterministic cache reuse.

## Health and operations

Liveness proves a process can answer. Readiness additionally reflects safe configuration and required dependencies. Compose health checks use the corresponding endpoints. Operators should treat `degraded` and `misconfigured` as non-ready and must not infer broker availability from container health alone.

Never bake `.env`, credentials, local databases, build caches, or MCP configuration into images.
